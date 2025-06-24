import os
import asyncio
import logging
from typing import AsyncGenerator, List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update, delete, func, and_, or_, desc, asc
from sqlalchemy.exc import SQLAlchemyError
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import json

# Import models
from models import (
    Base, User, Show, Contestant, UserTeam, Prediction, 
    League, LeagueMembership, Episode, EpisodeEvent, LeagueStats,
    ShowType, ShowStatus, EpisodeEventType, PredictionType
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://user:password@localhost:5432/bachelor_fantasy"
)

# For local development, use SQLite
if os.getenv("ENVIRONMENT") == "development":
    DATABASE_URL = "sqlite+aiosqlite:///./bachelor_fantasy.db"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "check_same_thread": False  # For SQLite
    } if "sqlite" in DATABASE_URL else {}
)

# Create session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Initialize database tables"""
    try:
        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("✅ Database tables created successfully")
        
        # Seed initial data if needed
        await seed_initial_data()
        
    except Exception as e:
        logger.error(f"❌ Error initializing database: {str(e)}")
        raise

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close()

@asynccontextmanager
async def get_db_session():
    """Context manager to get database session"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database transaction error: {str(e)}")
            raise
        finally:
            await session.close()

class DatabaseOperations:
    """Database operations for Bachelor Fantasy League"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # ==================== USER OPERATIONS ====================
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            result = await self.session.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {str(e)}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            result = await self.session.execute(
                select(User).where(User.email == email)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {str(e)}")
            return None
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            result = await self.session.execute(
                select(User).where(User.username == username)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {str(e)}")
            return None
    
    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """Create a new user"""
        try:
            user = User(**user_data)
            self.session.add(user)
            await self.session.flush()
            return user
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise
    
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Optional[User]:
        """Update user information"""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return None
            
            for key, value in updates.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            user.updated_at = datetime.utcnow()
            await self.session.flush()
            return user
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {str(e)}")
            raise
    
    # ==================== SHOW OPERATIONS ====================
    
    async def get_all_shows(self) -> List[Show]:
        """Get all shows"""
        try:
            result = await self.session.execute(
                select(Show).order_by(desc(Show.premiere_date))
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting all shows: {str(e)}")
            return []
    
    async def get_show_by_id(self, show_id: str) -> Optional[Show]:
        """Get show by ID"""
        try:
            result = await self.session.execute(
                select(Show).where(Show.id == show_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting show by ID {show_id}: {str(e)}")
            return None
    
    async def get_active_shows(self) -> List[Show]:
        """Get currently active shows"""
        try:
            result = await self.session.execute(
                select(Show).where(
                    and_(
                        Show.is_active == True,
                        Show.status == ShowStatus.AIRING
                    )
                ).order_by(desc(Show.premiere_date))
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting active shows: {str(e)}")
            return []
    
    async def get_shows_by_type(self, show_type: ShowType) -> List[Show]:
        """Get shows by type"""
        try:
            result = await self.session.execute(
                select(Show).where(Show.type == show_type)
                .order_by(desc(Show.season))
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting shows by type {show_type}: {str(e)}")
            return []
    
    # ==================== CONTESTANT OPERATIONS ====================
    
    async def get_contestants_by_show(self, show_id: str, include_eliminated: bool = True) -> List[Contestant]:
        """Get contestants for a show"""
        try:
            query = select(Contestant).where(Contestant.show_id == show_id)
            
            if not include_eliminated:
                query = query.where(Contestant.is_eliminated == False)
            
            # Order by elimination status and winner probability
            query = query.order_by(
                asc(Contestant.is_eliminated),
                desc(Contestant.winner_probability)
            )
            
            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting contestants for show {show_id}: {str(e)}")
            return []
    
    async def get_contestant_by_id(self, contestant_id: str) -> Optional[Contestant]:
        """Get contestant by ID"""
        try:
            result = await self.session.execute(
                select(Contestant).where(Contestant.id == contestant_id)
                .options(selectinload(Contestant.show))
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting contestant by ID {contestant_id}: {str(e)}")
            return None
    
    async def update_contestant_predictions(self, contestant_id: str, 
                                          predictions: Dict[str, float]) -> Optional[Contestant]:
        """Update ML predictions for contestant"""
        try:
            contestant = await self.get_contestant_by_id(contestant_id)
            if not contestant:
                return None
            
            # Update prediction fields
            contestant.elimination_probability = predictions.get('elimination_probability', 0.0)
            contestant.winner_probability = predictions.get('winner_probability', 0.0)
            contestant.next_episode_safe = predictions.get('next_episode_safe', True)
            contestant.confidence_interval_low = predictions.get('confidence_low', 0.0)
            contestant.confidence_interval_high = predictions.get('confidence_high', 1.0)
            contestant.prediction_trend = predictions.get('trend', 'stable')
            contestant.updated_at = datetime.utcnow()
            
            await self.session.flush()
            return contestant
        except Exception as e:
            logger.error(f"Error updating predictions for contestant {contestant_id}: {str(e)}")
            raise
    
    async def eliminate_contestant(self, contestant_id: str, episode: int, 
                                 reason: str = None) -> Optional[Contestant]:
        """Eliminate a contestant"""
        try:
            contestant = await self.get_contestant_by_id(contestant_id)
            if not contestant:
                return None
            
            contestant.is_eliminated = True
            contestant.elimination_episode = episode
            contestant.elimination_reason = reason
            contestant.winner_probability = 0.0
            contestant.elimination_probability = 1.0
            contestant.updated_at = datetime.utcnow()
            
            await self.session.flush()
            return contestant
        except Exception as e:
            logger.error(f"Error eliminating contestant {contestant_id}: {str(e)}")
            raise
    
    # ==================== FANTASY TEAM OPERATIONS ====================
    
    async def get_user_team(self, user_id: str, show_id: str) -> Optional[UserTeam]:
        """Get user's fantasy team for a show"""
        try:
            result = await self.session.execute(
                select(UserTeam).where(
                    and_(
                        UserTeam.user_id == user_id,
                        UserTeam.show_id == show_id
                    )
                ).options(selectinload(UserTeam.contestants))
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting team for user {user_id}, show {show_id}: {str(e)}")
            return None
    
    async def update_user_team(self, user_id: str, show_id: str, 
                             contestant_ids: List[str]) -> UserTeam:
        """Update user's fantasy team"""
        try:
            # Get or create team
            team = await self.get_user_team(user_id, show_id)
            
            if not team:
                team = UserTeam(
                    user_id=user_id,
                    show_id=show_id,
                    total_points=0,
                    weekly_points=0
                )
                self.session.add(team)
                await self.session.flush()
            
            # Get contestants
            contestants = await self.session.execute(
                select(Contestant).where(Contestant.id.in_(contestant_ids))
            )
            team.contestants = contestants.scalars().all()
            
            team.updated_at = datetime.utcnow()
            await self.session.flush()
            
            return team
        except Exception as e:
            logger.error(f"Error updating team for user {user_id}, show {show_id}: {str(e)}")
            raise
    
    async def get_leaderboard(self, show_id: str, limit: int = 50) -> List[UserTeam]:
        """Get leaderboard for a show"""
        try:
            result = await self.session.execute(
                select(UserTeam).where(UserTeam.show_id == show_id)
                .options(selectinload(UserTeam.user))
                .order_by(desc(UserTeam.total_points))
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting leaderboard for show {show_id}: {str(e)}")
            return []
    
    async def update_team_points(self, team_id: str, points_to_add: int, 
                               weekly_points: int = None) -> Optional[UserTeam]:
        """Update team points"""
        try:
            team = await self.session.execute(
                select(UserTeam).where(UserTeam.id == team_id)
            )
            team = team.scalar_one_or_none()
            
            if not team:
                return None
            
            team.total_points += points_to_add
            if weekly_points is not None:
                team.weekly_points = weekly_points
            
            team.updated_at = datetime.utcnow()
            await self.session.flush()
            
            return team
        except Exception as e:
            logger.error(f"Error updating points for team {team_id}: {str(e)}")
            raise
    
    # ==================== PREDICTION OPERATIONS ====================
    
    async def create_prediction(self, prediction_data: Dict[str, Any]) -> Prediction:
        """Create a new prediction"""
        try:
            prediction = Prediction(**prediction_data)
            self.session.add(prediction)
            await self.session.flush()
            return prediction
        except Exception as e:
            logger.error(f"Error creating prediction: {str(e)}")
            raise
    
    async def get_user_predictions(self, user_id: str, show_id: str = None) -> List[Prediction]:
        """Get user's predictions"""
        try:
            query = select(Prediction).where(Prediction.user_id == user_id)
            
            if show_id:
                query = query.where(Prediction.show_id == show_id)
            
            query = query.order_by(desc(Prediction.created_at))
            
            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting predictions for user {user_id}: {str(e)}")
            return []
    
    async def resolve_prediction(self, prediction_id: str, actual_result: float, 
                               points_earned: int) -> Optional[Prediction]:
        """Resolve a prediction with actual result"""
        try:
            prediction = await self.session.execute(
                select(Prediction).where(Prediction.id == prediction_id)
            )
            prediction = prediction.scalar_one_or_none()
            
            if not prediction:
                return None
            
            prediction.actual_result = actual_result
            prediction.points_earned = points_earned
            prediction.is_correct = abs(prediction.prediction_value - actual_result) < 0.1
            prediction.resolved_at = datetime.utcnow()
            
            await self.session.flush()
            return prediction
        except Exception as e:
            logger.error(f"Error resolving prediction {prediction_id}: {str(e)}")
            raise
    
    # ==================== EPISODE OPERATIONS ====================
    
    async def create_episode_event(self, event_data: Dict[str, Any]) -> EpisodeEvent:
        """Create a new episode event"""
        try:
            event = EpisodeEvent(**event_data)
            self.session.add(event)
            await self.session.flush()
            return event
        except Exception as e:
            logger.error(f"Error creating episode event: {str(e)}")
            raise
    
    async def get_episode_events(self, episode_id: str) -> List[EpisodeEvent]:
        """Get events for an episode"""
        try:
            result = await self.session.execute(
                select(EpisodeEvent).where(EpisodeEvent.episode_id == episode_id)
                .options(selectinload(EpisodeEvent.contestants))
                .order_by(desc(EpisodeEvent.timestamp))
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting events for episode {episode_id}: {str(e)}")
            return []
    
    # ==================== STATISTICS OPERATIONS ====================
    
    async def get_league_stats(self, show_id: str) -> Dict[str, Any]:
        """Get league statistics for a show"""
        try:
            # Total users with teams
            total_users_result = await self.session.execute(
                select(func.count(UserTeam.id)).where(UserTeam.show_id == show_id)
            )
            total_users = total_users_result.scalar() or 0
            
            # Average score
            avg_score_result = await self.session.execute(
                select(func.avg(UserTeam.total_points)).where(UserTeam.show_id == show_id)
            )
            average_score = avg_score_result.scalar() or 0.0
            
            # Top score
            top_score_result = await self.session.execute(
                select(func.max(UserTeam.total_points)).where(UserTeam.show_id == show_id)
            )
            top_score = top_score_result.scalar() or 0
            
            # Weekly leader
            weekly_leader_result = await self.session.execute(
                select(UserTeam, User.username).join(User)
                .where(UserTeam.show_id == show_id)
                .order_by(desc(UserTeam.weekly_points))
                .limit(1)
            )
            weekly_leader_row = weekly_leader_result.first()
            weekly_leader = weekly_leader_row[1] if weekly_leader_row else "TBD"
            
            return {
                "total_users": total_users,
                "average_score": float(average_score),
                "top_score": top_score,
                "weekly_leader": weekly_leader
            }
            
        except Exception as e:
            logger.error(f"Error getting league stats for show {show_id}: {str(e)}")
            return {
                "total_users": 0,
                "average_score": 0.0,
                "top_score": 0,
                "weekly_leader": "TBD"
            }
    
    async def update_user_rank(self, user_id: str, show_id: str) -> Optional[int]:
        """Update and return user's rank in a show"""
        try:
            # Get user's team
            user_team = await self.get_user_team(user_id, show_id)
            if not user_team:
                return None
            
            # Count teams with higher scores
            higher_scores_result = await self.session.execute(
                select(func.count(UserTeam.id)).where(
                    and_(
                        UserTeam.show_id == show_id,
                        UserTeam.total_points > user_team.total_points
                    )
                )
            )
            rank = higher_scores_result.scalar() + 1
            
            # Update user's rank
            user_team.rank = rank
            await self.session.flush()
            
            return rank
            
        except Exception as e:
            logger.error(f"Error updating rank for user {user_id}: {str(e)}")
            return None
    
    # ==================== UTILITY OPERATIONS ====================
    
    async def validate_contestants(self, show_id: str, contestant_ids: List[str]) -> List[str]:
        """Validate that contestants exist and aren't eliminated"""
        try:
            result = await self.session.execute(
                select(Contestant.id).where(
                    and_(
                        Contestant.show_id == show_id,
                        Contestant.id.in_(contestant_ids),
                        Contestant.is_eliminated == False
                    )
                )
            )
            return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error validating contestants: {str(e)}")
            return []
    
    async def bulk_update_contestants(self, updates: List[Dict[str, Any]]) -> bool:
        """Bulk update multiple contestants"""
        try:
            for update_data in updates:
                contestant_id = update_data.pop('id')
                await self.session.execute(
                    update(Contestant)
                    .where(Contestant.id == contestant_id)
                    .values(**update_data)
                )
            
            await self.session.flush()
            return True
        except Exception as e:
            logger.error(f"Error bulk updating contestants: {str(e)}")
            return False

# Extend AsyncSession with our custom operations
AsyncSession.get_user_by_id = DatabaseOperations.get_user_by_id
AsyncSession.get_user_by_email = DatabaseOperations.get_user_by_email
AsyncSession.get_all_shows = DatabaseOperations.get_all_shows
AsyncSession.get_contestants_by_show = DatabaseOperations.get_contestants_by_show
AsyncSession.get_user_team = DatabaseOperations.get_user_team
AsyncSession.update_user_team = DatabaseOperations.update_user_team
AsyncSession.get_league_stats = DatabaseOperations.get_league_stats
AsyncSession.validate_contestants = DatabaseOperations.validate_contestants
AsyncSession.get_contestant_by_id = DatabaseOperations.get_contestant_by_id

async def seed_initial_data():
    """Seed database with initial Bachelor show data"""
    try:
        async with get_db_session() as session:
            # Check if data already exists
            existing_shows = await session.execute(select(func.count(Show.id)))
            if existing_shows.scalar() > 0:
                logger.info("📊 Database already contains data, skipping seed")
                return
            
            logger.info("🌱 Seeding initial Bachelor show data...")
            
            # Create sample shows (this would be real data in production)
            shows_data = [
                {
                    "id": "bachelor-28",
                    "name": "The Bachelor",
                    "type": ShowType.BACHELOR,
                    "season": 28,
                    "lead": "Joey Graziadei",
                    "premiere_date": datetime(2024, 1, 22),
                    "current_episode": 8,
                    "total_episodes": 12,
                    "status": ShowStatus.AIRING,
                    "is_active": True,
                    "location": "Malta",
                    "description": "Joey Graziadei searches for love among 32 incredible women"
                },
                {
                    "id": "bachelorette-21",
                    "name": "The Bachelorette",
                    "type": ShowType.BACHELORETTE,
                    "season": 21,
                    "lead": "Jenn Tran",
                    "premiere_date": datetime(2024, 7, 8),
                    "finale_date": datetime(2024, 9, 3),
                    "current_episode": 12,
                    "total_episodes": 12,
                    "status": ShowStatus.COMPLETED,
                    "is_active": False,
                    "location": "Various Locations",
                    "description": "Jenn Tran's journey to find her perfect match"
                }
            ]
            
            for show_data in shows_data:
                show = Show(**show_data)
                session.add(show)
            
            await session.commit()
            logger.info("✅ Initial data seeded successfully")
            
    except Exception as e:
        logger.error(f"❌ Error seeding initial data: {str(e)}")

# Export main functions and classes
__all__ = [
    'engine', 'async_session_factory', 'init_db', 'get_db', 
    'get_db_session', 'DatabaseOperations', 'seed_initial_data'
]
