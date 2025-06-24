from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import uvicorn
from contextlib import asynccontextmanager

# Database and ML imports
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db, init_db
from models import User, Show, Contestant, UserTeam, Prediction, LeagueStats
from schemas import (
    UserCreate, UserLogin, UserResponse, 
    ShowResponse, ContestantResponse, 
    TeamCreate, TeamResponse,
    PredictionCreate, PredictionResponse
)
from auth import create_access_token, verify_token, get_current_user, hash_password, verify_password
from ml_models import PredictionEngine, SentimentAnalyzer
from websocket_manager import ConnectionManager
from background_tasks import BackgroundTaskManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize ML components
prediction_engine = PredictionEngine()
sentiment_analyzer = SentimentAnalyzer()
websocket_manager = ConnectionManager()
task_manager = BackgroundTaskManager()

# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting Bachelor Fantasy League API...")
    
    # Initialize database
    await init_db()
    logger.info("✅ Database initialized")
    
    # Load ML models
    await prediction_engine.load_models()
    logger.info("🤖 ML models loaded")
    
    # Start background tasks
    await task_manager.start()
    logger.info("⚡ Background tasks started")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    await task_manager.stop()
    logger.info("✅ Background tasks stopped")

# Create FastAPI app
app = FastAPI(
    title="Bachelor Fantasy League API",
    description="Fantasy sports platform for The Bachelor franchise with ML predictions and real-time scoring",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://bachelor-fantasy.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {
            "database": "connected",
            "ml_engine": "loaded",
            "websockets": f"{len(websocket_manager.active_connections)} active"
        }
    }

# ==================== AUTH ENDPOINTS ====================

@app.post("/api/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user"""
    try:
        # Check if user already exists
        existing_user = await db.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Create user
        hashed_password = hash_password(user_data.password)
        user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hashed_password,
            favorite_show=user_data.favorite_show
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Create access token
        access_token = create_access_token({"sub": user.id})
        
        return {
            "user": user,
            "token": access_token,
            "refresh_token": create_access_token({"sub": user.id}, expires_delta=timedelta(days=30))
        }
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@app.post("/api/auth/login")
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """User login"""
    try:
        user = await db.get_user_by_email(credentials.email)
        if not user or not verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        access_token = create_access_token({"sub": user.id})
        
        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "total_points": user.total_points,
                "current_rank": user.current_rank,
                "favorite_show": user.favorite_show
            },
            "token": access_token,
            "refresh_token": create_access_token({"sub": user.id}, expires_delta=timedelta(days=30))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user

# ==================== SHOW ENDPOINTS ====================

@app.get("/api/shows", response_model=List[ShowResponse])
async def get_shows(db: AsyncSession = Depends(get_db)):
    """Get all Bachelor franchise shows"""
    try:
        shows = await db.get_all_shows()
        return shows
    except Exception as e:
        logger.error(f"Error getting shows: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch shows"
        )

@app.get("/api/shows/{show_id}", response_model=ShowResponse)
async def get_show(show_id: str, db: AsyncSession = Depends(get_db)):
    """Get specific show details"""
    try:
        show = await db.get_show_by_id(show_id)
        if not show:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Show not found"
            )
        return show
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting show {show_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch show"
        )

@app.get("/api/shows/{show_id}/contestants", response_model=List[ContestantResponse])
async def get_contestants(
    show_id: str, 
    include_eliminated: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Get contestants for a specific show"""
    try:
        contestants = await db.get_contestants_by_show(show_id, include_eliminated)
        
        # Enhance with ML predictions
        enhanced_contestants = []
        for contestant in contestants:
            # Get ML predictions
            predictions = await prediction_engine.predict_contestant_outcomes(contestant)
            
            # Get sentiment analysis
            sentiment = await sentiment_analyzer.analyze_contestant_sentiment(contestant)
            
            # Enhance contestant data
            enhanced_contestant = {
                **contestant.__dict__,
                "predictions": predictions,
                "sentiment_score": sentiment
            }
            enhanced_contestants.append(enhanced_contestant)
        
        return enhanced_contestants
        
    except Exception as e:
        logger.error(f"Error getting contestants for show {show_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch contestants"
        )

# ==================== FANTASY TEAM ENDPOINTS ====================

@app.get("/api/users/{user_id}/teams/{show_id}", response_model=TeamResponse)
async def get_user_team(
    user_id: str, 
    show_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's fantasy team for a specific show"""
    try:
        # Check authorization
        if current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this team"
            )
        
        team = await db.get_user_team(user_id, show_id)
        if not team:
            # Create default empty team
            team = UserTeam(
                user_id=user_id,
                show_id=show_id,
                contestants=[],
                total_points=0,
                weekly_points=0
            )
        
        return team
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting team for user {user_id}, show {show_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch team"
        )

@app.post("/api/users/{user_id}/teams/{show_id}", response_model=TeamResponse)
async def update_user_team(
    user_id: str,
    show_id: str,
    team_data: TeamCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user's fantasy team"""
    try:
        # Check authorization
        if current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this team"
            )
        
        # Validate contestants exist and aren't eliminated
        valid_contestants = await db.validate_contestants(show_id, team_data.contestants)
        if len(valid_contestants) != len(team_data.contestants):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Some contestants are invalid or eliminated"
            )
        
        # Update or create team
        team = await db.update_user_team(user_id, show_id, team_data.contestants)
        
        # Broadcast team update via WebSocket
        await websocket_manager.broadcast_to_show(show_id, {
            "type": "team_update",
            "user_id": user_id,
            "username": current_user.username,
            "contestants": team_data.contestants,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return team
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating team for user {user_id}, show {show_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update team"
        )

# ==================== PREDICTION ENDPOINTS ====================

@app.post("/api/predictions", response_model=PredictionResponse)
async def create_prediction(
    prediction_data: PredictionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new prediction"""
    try:
        # Validate contestant exists
        contestant = await db.get_contestant_by_id(prediction_data.contestant_id)
        if not contestant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contestant not found"
            )
        
        # Create prediction
        prediction = Prediction(
            user_id=current_user.id,
            contestant_id=prediction_data.contestant_id,
            show_id=contestant.show_id,
            prediction_type=prediction_data.prediction_type,
            prediction_value=prediction_data.prediction_value,
            confidence=prediction_data.confidence
        )
        
        db.add(prediction)
        await db.commit()
        
        # Broadcast prediction via WebSocket
        await websocket_manager.broadcast_to_show(contestant.show_id, {
            "type": "user_prediction",
            "user_id": current_user.id,
            "username": current_user.username,
            "contestant_id": prediction_data.contestant_id,
            "prediction": prediction_data.prediction_value,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return prediction
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating prediction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create prediction"
        )

@app.get("/api/shows/{show_id}/league-stats")
async def get_league_stats(show_id: str, db: AsyncSession = Depends(get_db)):
    """Get league statistics for a show"""
    try:
        stats = await db.get_league_stats(show_id)
        return stats
    except Exception as e:
        logger.error(f"Error getting league stats for show {show_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch league stats"
        )

# ==================== WEBSOCKET ENDPOINTS ====================

@app.websocket("/ws/{show_id}")
async def websocket_endpoint(websocket: WebSocket, show_id: str):
    """WebSocket endpoint for real-time updates"""
    await websocket_manager.connect(websocket, show_id)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "authenticate":
                await websocket_manager.authenticate_connection(websocket, message.get("user_id"))
            elif message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, show_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        websocket_manager.disconnect(websocket, show_id)

# ==================== BACKGROUND TASK ENDPOINTS ====================

@app.post("/api/admin/trigger-ml-update")
async def trigger_ml_update(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger ML model updates (admin only)"""
    try:
        # Check if user is admin (you'd implement admin check)
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        # Trigger ML updates
        await task_manager.trigger_ml_updates()
        
        return {"message": "ML update triggered successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering ML update: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger ML update"
        )

@app.post("/api/admin/simulate-episode-event")
async def simulate_episode_event(
    event_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Simulate an episode event for testing (admin only)"""
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        # Broadcast simulated event
        await websocket_manager.broadcast_to_show(event_data.get("show_id"), {
            "type": "episode_event",
            "event_type": event_data.get("event_type"),
            "description": event_data.get("description"),
            "contestants": event_data.get("contestants", []),
            "points": event_data.get("points", 0),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {"message": "Event simulated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error simulating event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to simulate event"
        )

# ==================== ERROR HANDLERS ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# ==================== STARTUP ====================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
