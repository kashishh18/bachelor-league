import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass, asdict
from collections import defaultdict
import uuid
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessageType(str, Enum):
    """WebSocket message types"""
    # Incoming from clients
    AUTHENTICATE = "authenticate"
    SUBSCRIBE_SHOW = "subscribe_show"
    UNSUBSCRIBE_SHOW = "unsubscribe_show"
    USER_PREDICTION = "user_prediction"
    TEAM_UPDATE = "team_update"
    PING = "ping"
    
    # Outgoing to clients
    SCORE_UPDATE = "score_update"
    EPISODE_EVENT = "episode_event"
    PREDICTION_UPDATE = "prediction_update"
    LEADERBOARD_UPDATE = "leaderboard_update"
    FRIEND_ACTIVITY = "friend_activity"
    LIVE_STATS = "live_stats"
    PONG = "pong"
    ERROR = "error"
    CONNECTED = "connected"

@dataclass
class Connection:
    """Represents a WebSocket connection"""
    websocket: WebSocket
    connection_id: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    subscribed_shows: Set[str] = None
    connected_at: datetime = None
    last_ping: datetime = None
    is_authenticated: bool = False
    
    def __post_init__(self):
        if self.subscribed_shows is None:
            self.subscribed_shows = set()
        if self.connected_at is None:
            self.connected_at = datetime.utcnow()
        if self.last_ping is None:
            self.last_ping = datetime.utcnow()

@dataclass
class LiveStats:
    """Live statistics for a show"""
    show_id: str
    viewers_count: int = 0
    active_predictions: int = 0
    total_points_awarded: int = 0
    recent_events: int = 0
    top_performer: Dict[str, Any] = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
        if self.top_performer is None:
            self.top_performer = {"username": "TBD", "points": 0}

class ConnectionManager:
    """Manages WebSocket connections and real-time messaging"""
    
    def __init__(self):
        # Connection storage
        self.active_connections: Dict[str, Connection] = {}
        self.show_subscribers: Dict[str, Set[str]] = defaultdict(set)
        self.user_connections: Dict[str, str] = {}  # user_id -> connection_id
        
        # Live statistics
        self.live_stats: Dict[str, LiveStats] = {}
        
        # Message queues and rate limiting
        self.message_queues: Dict[str, List[Dict]] = defaultdict(list)
        self.rate_limits: Dict[str, datetime] = {}
        
        # Background tasks
        self.cleanup_task: Optional[asyncio.Task] = None
        self.stats_task: Optional[asyncio.Task] = None
        
        # Start background tasks
        self._start_background_tasks()

    def _start_background_tasks(self):
        """Start background maintenance tasks"""
        self.cleanup_task = asyncio.create_task(self._cleanup_connections())
        self.stats_task = asyncio.create_task(self._update_live_stats())

    async def connect(self, websocket: WebSocket, show_id: Optional[str] = None):
        """Accept a new WebSocket connection"""
        try:
            await websocket.accept()
            
            connection_id = str(uuid.uuid4())
            connection = Connection(
                websocket=websocket,
                connection_id=connection_id
            )
            
            self.active_connections[connection_id] = connection
            
            # Subscribe to show if provided
            if show_id:
                await self._subscribe_to_show(connection_id, show_id)
            
            # Send welcome message
            await self._send_to_connection(connection_id, {
                "type": MessageType.CONNECTED,
                "connection_id": connection_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Connected to Bachelor Fantasy League real-time updates"
            })
            
            logger.info(f"🔗 New WebSocket connection: {connection_id}")
            
        except Exception as e:
            logger.error(f"❌ Error connecting WebSocket: {str(e)}")
            await websocket.close()

    def disconnect(self, websocket: WebSocket, show_id: Optional[str] = None):
        """Disconnect a WebSocket connection"""
        try:
            # Find connection by websocket
            connection_id = None
            for conn_id, conn in self.active_connections.items():
                if conn.websocket == websocket:
                    connection_id = conn_id
                    break
            
            if connection_id:
                connection = self.active_connections[connection_id]
                
                # Remove from show subscriptions
                for subscribed_show in connection.subscribed_shows:
                    self.show_subscribers[subscribed_show].discard(connection_id)
                
                # Remove from user connections
                if connection.user_id:
                    self.user_connections.pop(connection.user_id, None)
                
                # Remove connection
                del self.active_connections[connection_id]
                
                logger.info(f"🔌 Disconnected WebSocket: {connection_id}")
            
        except Exception as e:
            logger.error(f"❌ Error disconnecting WebSocket: {str(e)}")

    async def authenticate_connection(self, websocket: WebSocket, user_id: str, username: str = None):
        """Authenticate a WebSocket connection with user credentials"""
        try:
            # Find connection
            connection_id = None
            for conn_id, conn in self.active_connections.items():
                if conn.websocket == websocket:
                    connection_id = conn_id
                    break
            
            if not connection_id:
                logger.warning("🚫 Authentication attempt on unknown connection")
                return
            
            connection = self.active_connections[connection_id]
            connection.user_id = user_id
            connection.username = username
            connection.is_authenticated = True
            
            # Update user connection mapping
            self.user_connections[user_id] = connection_id
            
            logger.info(f"✅ Authenticated connection {connection_id} for user {username} ({user_id})")
            
            # Send authentication confirmation
            await self._send_to_connection(connection_id, {
                "type": "authentication_success",
                "user_id": user_id,
                "username": username,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Error authenticating connection: {str(e)}")

    async def subscribe_to_show(self, websocket: WebSocket, show_id: str):
        """Subscribe a connection to show updates"""
        try:
            # Find connection
            connection_id = None
            for conn_id, conn in self.active_connections.items():
                if conn.websocket == websocket:
                    connection_id = conn_id
                    break
            
            if connection_id:
                await self._subscribe_to_show(connection_id, show_id)
            
        except Exception as e:
            logger.error(f"❌ Error subscribing to show {show_id}: {str(e)}")

    async def _subscribe_to_show(self, connection_id: str, show_id: str):
        """Internal method to subscribe connection to show"""
        if connection_id not in self.active_connections:
            return
        
        connection = self.active_connections[connection_id]
        connection.subscribed_shows.add(show_id)
        self.show_subscribers[show_id].add(connection_id)
        
        # Initialize live stats for show if needed
        if show_id not in self.live_stats:
            self.live_stats[show_id] = LiveStats(show_id=show_id)
        
        # Update viewer count
        self.live_stats[show_id].viewers_count = len(self.show_subscribers[show_id])
        
        logger.info(f"📺 Connection {connection_id} subscribed to show {show_id}")
        
        # Send current live stats
        await self._send_to_connection(connection_id, {
            "type": MessageType.LIVE_STATS,
            "show_id": show_id,
            "stats": asdict(self.live_stats[show_id]),
            "timestamp": datetime.utcnow().isoformat()
        })

    async def unsubscribe_from_show(self, websocket: WebSocket, show_id: str):
        """Unsubscribe a connection from show updates"""
        try:
            # Find connection
            connection_id = None
            for conn_id, conn in self.active_connections.items():
                if conn.websocket == websocket:
                    connection_id = conn_id
                    break
            
            if connection_id:
                connection = self.active_connections[connection_id]
                connection.subscribed_shows.discard(show_id)
                self.show_subscribers[show_id].discard(connection_id)
                
                # Update viewer count
                if show_id in self.live_stats:
                    self.live_stats[show_id].viewers_count = len(self.show_subscribers[show_id])
                
                logger.info(f"📺 Connection {connection_id} unsubscribed from show {show_id}")
            
        except Exception as e:
            logger.error(f"❌ Error unsubscribing from show {show_id}: {str(e)}")

    async def broadcast_to_show(self, show_id: str, message: Dict[str, Any]):
        """Broadcast a message to all subscribers of a show"""
        try:
            if show_id not in self.show_subscribers:
                logger.warning(f"⚠️ No subscribers for show {show_id}")
                return
            
            subscribers = self.show_subscribers[show_id].copy()
            message["show_id"] = show_id
            message["timestamp"] = datetime.utcnow().isoformat()
            
            # Send to all subscribers
            failed_connections = []
            for connection_id in subscribers:
                success = await self._send_to_connection(connection_id, message)
                if not success:
                    failed_connections.append(connection_id)
            
            # Clean up failed connections
            for failed_id in failed_connections:
                await self._cleanup_connection(failed_id)
            
            # Update stats
            await self._update_show_stats(show_id, message)
            
            logger.info(f"📡 Broadcasted {message.get('type')} to {len(subscribers)} subscribers of show {show_id}")
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting to show {show_id}: {str(e)}")

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send a message to a specific user"""
        try:
            if user_id not in self.user_connections:
                logger.warning(f"⚠️ User {user_id} not connected")
                return
            
            connection_id = self.user_connections[user_id]
            await self._send_to_connection(connection_id, message)
            
        except Exception as e:
            logger.error(f"❌ Error sending to user {user_id}: {str(e)}")

    async def _send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Send a message to a specific connection"""
        try:
            if connection_id not in self.active_connections:
                return False
            
            connection = self.active_connections[connection_id]
            
            # Rate limiting check
            if not await self._check_rate_limit(connection_id):
                return False
            
            # Send message
            await connection.websocket.send_text(json.dumps(message))
            return True
            
        except WebSocketDisconnect:
            await self._cleanup_connection(connection_id)
            return False
        except Exception as e:
            logger.error(f"❌ Error sending to connection {connection_id}: {str(e)}")
            await self._cleanup_connection(connection_id)
            return False

    async def _check_rate_limit(self, connection_id: str) -> bool:
        """Check if connection is within rate limits"""
        now = datetime.utcnow()
        
        # Allow 10 messages per second per connection
        rate_limit_key = f"{connection_id}:{now.second}"
        
        if rate_limit_key in self.rate_limits:
            # Already at limit for this second
            return False
        
        self.rate_limits[rate_limit_key] = now
        
        # Clean old rate limit entries
        cutoff = now - timedelta(seconds=2)
        keys_to_remove = [key for key, timestamp in self.rate_limits.items() 
                         if timestamp < cutoff]
        for key in keys_to_remove:
            del self.rate_limits[key]
        
        return True

    async def _update_show_stats(self, show_id: str, message: Dict[str, Any]):
        """Update live statistics for a show based on message"""
        try:
            if show_id not in self.live_stats:
                self.live_stats[show_id] = LiveStats(show_id=show_id)
            
            stats = self.live_stats[show_id]
            message_type = message.get("type")
            
            # Update based on message type
            if message_type == MessageType.SCORE_UPDATE:
                stats.total_points_awarded += message.get("points", 0)
                stats.recent_events += 1
                
                # Update top performer if needed
                user_points = message.get("user_total_points", 0)
                if user_points > stats.top_performer["points"]:
                    stats.top_performer = {
                        "username": message.get("username", "Unknown"),
                        "points": user_points
                    }
            
            elif message_type == MessageType.EPISODE_EVENT:
                stats.recent_events += 1
            
            elif message_type == MessageType.USER_PREDICTION:
                stats.active_predictions += 1
            
            stats.updated_at = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"❌ Error updating show stats: {str(e)}")

    async def _cleanup_connection(self, connection_id: str):
        """Clean up a failed or disconnected connection"""
        try:
            if connection_id in self.active_connections:
                connection = self.active_connections[connection_id]
                
                # Remove from show subscriptions
                for show_id in connection.subscribed_shows:
                    self.show_subscribers[show_id].discard(connection_id)
                    
                    # Update viewer count
                    if show_id in self.live_stats:
                        self.live_stats[show_id].viewers_count = len(self.show_subscribers[show_id])
                
                # Remove from user connections
                if connection.user_id:
                    self.user_connections.pop(connection.user_id, None)
                
                # Remove connection
                del self.active_connections[connection_id]
                
                logger.info(f"🧹 Cleaned up connection {connection_id}")
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up connection {connection_id}: {str(e)}")

    async def _cleanup_connections(self):
        """Background task to clean up stale connections"""
        while True:
            try:
                await asyncio.sleep(30)  # Run every 30 seconds
                
                now = datetime.utcnow()
                stale_connections = []
                
                for connection_id, connection in self.active_connections.items():
                    # Remove connections inactive for more than 5 minutes
                    if now - connection.last_ping > timedelta(minutes=5):
                        stale_connections.append(connection_id)
                
                for connection_id in stale_connections:
                    await self._cleanup_connection(connection_id)
                    logger.info(f"🧹 Removed stale connection {connection_id}")
                
            except Exception as e:
                logger.error(f"❌ Error in cleanup task: {str(e)}")

    async def _update_live_stats(self):
        """Background task to update live statistics"""
        while True:
            try:
                await asyncio.sleep(10)  # Update every 10 seconds
                
                # Broadcast updated stats to all shows
                for show_id, stats in self.live_stats.items():
                    if self.show_subscribers[show_id]:
                        await self.broadcast_to_show(show_id, {
                            "type": MessageType.LIVE_STATS,
                            "stats": asdict(stats)
                        })
                
            except Exception as e:
                logger.error(f"❌ Error updating live stats: {str(e)}")

    async def handle_ping(self, websocket: WebSocket):
        """Handle ping message from client"""
        try:
            # Find connection and update last ping
            for connection in self.active_connections.values():
                if connection.websocket == websocket:
                    connection.last_ping = datetime.utcnow()
                    
                    # Send pong response
                    await connection.websocket.send_text(json.dumps({
                        "type": MessageType.PONG,
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                    break
            
        except Exception as e:
            logger.error(f"❌ Error handling ping: {str(e)}")

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get current connection statistics"""
        total_connections = len(self.active_connections)
        authenticated_connections = sum(1 for conn in self.active_connections.values() 
                                      if conn.is_authenticated)
        
        show_stats = {}
        for show_id, subscribers in self.show_subscribers.items():
            show_stats[show_id] = len(subscribers)
        
        return {
            "total_connections": total_connections,
            "authenticated_connections": authenticated_connections,
            "show_subscribers": show_stats,
            "live_stats": {show_id: asdict(stats) for show_id, stats in self.live_stats.items()}
        }

    async def shutdown(self):
        """Gracefully shutdown the connection manager"""
        try:
            logger.info("🛑 Shutting down WebSocket manager...")
            
            # Cancel background tasks
            if self.cleanup_task:
                self.cleanup_task.cancel()
            if self.stats_task:
                self.stats_task.cancel()
            
            # Close all connections
            for connection in self.active_connections.values():
                try:
                    await connection.websocket.close()
                except:
                    pass
            
            self.active_connections.clear()
            self.show_subscribers.clear()
            self.user_connections.clear()
            
            logger.info("✅ WebSocket manager shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {str(e)}")

# Utility functions for message formatting
def format_score_update(contestant_id: str, contestant_name: str, points: int, 
                       reason: str, episode: int, user_id: str = None) -> Dict[str, Any]:
    """Format a score update message"""
    return {
        "type": MessageType.SCORE_UPDATE,
        "contestant_id": contestant_id,
        "contestant_name": contestant_name,
        "points": points,
        "reason": reason,
        "episode": episode,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }

def format_episode_event(event_type: str, description: str, contestants: List[str], 
                        episode: int, points: int = 0) -> Dict[str, Any]:
    """Format an episode event message"""
    return {
        "type": MessageType.EPISODE_EVENT,
        "event_type": event_type,
        "description": description,
        "contestants": contestants,
        "episode": episode,
        "points": points,
        "timestamp": datetime.utcnow().isoformat()
    }

def format_prediction_update(contestant_id: str, contestant_name: str, 
                           old_prediction: float, new_prediction: float,
                           confidence: float, factors: List[str]) -> Dict[str, Any]:
    """Format a prediction update message"""
    return {
        "type": MessageType.PREDICTION_UPDATE,
        "contestant_id": contestant_id,
        "contestant_name": contestant_name,
        "old_prediction": old_prediction,
        "new_prediction": new_prediction,
        "confidence": confidence,
        "factors": factors,
        "timestamp": datetime.utcnow().isoformat()
    }

# Export main class
__all__ = ['ConnectionManager', 'MessageType', 'format_score_update', 
           'format_episode_event', 'format_prediction_update']
