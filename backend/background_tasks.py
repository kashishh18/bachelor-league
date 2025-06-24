import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import aiofiles
from contextlib import asynccontextmanager
import traceback
from collections import defaultdict
import hashlib

# Import our modules
from database import get_db_session, DatabaseOperations
from ml_models import PredictionEngine, SentimentAnalyzer
from websocket_manager import ConnectionManager, format_score_update, format_episode_event, format_prediction_update
from models import User, Show, Contestant, UserTeam, EpisodeEvent, ShowStatus
from auth import session_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class TaskResult:
    """Result of a background task"""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ScheduledTask:
    """Represents a scheduled background task"""
    id: str
    name: str
    function: Callable
    schedule_type: str  # 'interval', 'cron', 'once'
    schedule_config: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    failure_count: int = 0
    max_failures: int = 3

class BackgroundTaskManager:
    """Manages all background tasks for the Bachelor Fantasy League platform"""
    
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_results: Dict[str, TaskResult] = {}
        self.is_running = False
        self.scheduler_task: Optional[asyncio.Task] = None
        
        # Dependencies
        self.prediction_engine: Optional[PredictionEngine] = None
        self.sentiment_analyzer: Optional[SentimentAnalyzer] = None
        self.websocket_manager: Optional[ConnectionManager] = None
        
        # Performance tracking
        self.stats = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'total_runtime_seconds': 0.0,
            'last_ml_update': None,
            'last_data_sync': None
        }
        
        # Register default tasks
        self._register_default_tasks()

    async def start(self):
        """Start the background task manager"""
        try:
            logger.info("🚀 Starting Background Task Manager...")
            
            # Initialize dependencies
            await self._initialize_dependencies()
            
            # Start task scheduler
            self.is_running = True
            self.scheduler_task = asyncio.create_task(self._task_scheduler())
            
            logger.info("✅ Background Task Manager started successfully")
            
        except Exception as e:
            logger.error(f"❌ Error starting Background Task Manager: {str(e)}")
            raise

    async def stop(self):
        """Stop the background task manager"""
        try:
            logger.info("🛑 Stopping Background Task Manager...")
            
            self.is_running = False
            
            # Cancel scheduler
            if self.scheduler_task:
                self.scheduler_task.cancel()
                try:
                    await self.scheduler_task
                except asyncio.CancelledError:
                    pass
            
            # Cancel running tasks
            for task_id, task in self.running_tasks.items():
                logger.info(f"🔄 Cancelling task: {task_id}")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            self.running_tasks.clear()
            
            logger.info("✅ Background Task Manager stopped")
            
        except Exception as e:
            logger.error(f"❌ Error stopping Background Task Manager: {str(e)}")

    async def _initialize_dependencies(self):
        """Initialize required dependencies"""
        try:
            # Initialize ML components
            self.prediction_engine = PredictionEngine()
            await self.prediction_engine.load_models()
            
            self.sentiment_analyzer = SentimentAnalyzer()
            
            logger.info("🤖 ML components initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing dependencies: {str(e)}")
            raise

    def _register_default_tasks(self):
        """Register default scheduled tasks"""
        
        # ML model updates - every 30 minutes during active episodes
        self.register_task(
            "ml_predictions_update",
            "Update ML Predictions",
            self.update_ml_predictions,
            schedule_type="interval",
            schedule_config={"minutes": 30},
            priority=TaskPriority.HIGH
        )
        
        # Sentiment analysis - every 15 minutes
        self.register_task(
            "sentiment_analysis",
            "Analyze Social Media Sentiment",
            self.analyze_sentiment,
            schedule_type="interval", 
            schedule_config={"minutes": 15},
            priority=TaskPriority.NORMAL
        )
        
        # Data synchronization - every 5 minutes
        self.register_task(
            "data_sync",
            "Synchronize External Data",
            self.sync_external_data,
            schedule_type="interval",
            schedule_config={"minutes": 5},
            priority=TaskPriority.NORMAL
        )
        
        # Leaderboard updates - every 10 minutes
        self.register_task(
            "leaderboard_update",
            "Update Leaderboards",
            self.update_leaderboards,
            schedule_type="interval",
            schedule_config={"minutes": 10},
            priority=TaskPriority.NORMAL
        )
        
        # Episode event detection - every 2 minutes during live episodes
        self.register_task(
            "episode_event_detection",
            "Detect Live Episode Events",
            self.detect_episode_events,
            schedule_type="interval",
            schedule_config={"minutes": 2},
            priority=TaskPriority.CRITICAL
        )
        
        # User statistics update - every hour
        self.register_task(
            "user_stats_update",
            "Update User Statistics",
            self.update_user_statistics,
            schedule_type="interval",
            schedule_config={"hours": 1},
            priority=TaskPriority.LOW
        )
        
        # Database cleanup - daily at 3 AM
        self.register_task(
            "database_cleanup",
            "Clean Up Database",
            self.cleanup_database,
            schedule_type="cron",
            schedule_config={"hour": 3, "minute": 0},
            priority=TaskPriority.LOW
        )
        
        # Session cleanup - every 30 minutes
        self.register_task(
            "session_cleanup",
            "Clean Expired Sessions",
            self.cleanup_sessions,
            schedule_type="interval",
            schedule_config={"minutes": 30},
            priority=TaskPriority.LOW
        )

    def register_task(self, task_id: str, name: str, function: Callable,
                     schedule_type: str, schedule_config: Dict[str, Any],
                     priority: TaskPriority = TaskPriority.NORMAL,
                     enabled: bool = True):
        """Register a new scheduled task"""
        
        task = ScheduledTask(
            id=task_id,
            name=name,
            function=function,
            schedule_type=schedule_type,
            schedule_config=schedule_config,
            priority=priority,
            enabled=enabled,
            next_run=self._calculate_next_run(schedule_type, schedule_config)
        )
        
        self.tasks[task_id] = task
        logger.info(f"📋 Registered task: {name} ({task_id})")

    def _calculate_next_run(self, schedule_type: str, config: Dict[str, Any]) -> datetime:
        """Calculate next run time for a task"""
        now = datetime.utcnow()
        
        if schedule_type == "interval":
            # Add interval to current time
            delta_kwargs = {k: v for k, v in config.items() 
                          if k in ['days', 'hours', 'minutes', 'seconds']}
            return now + timedelta(**delta_kwargs)
        
        elif schedule_type == "cron":
            # Simple cron-like scheduling (hour and minute only for now)
            next_run = now.replace(
                hour=config.get('hour', now.hour),
                minute=config.get('minute', 0),
                second=0,
                microsecond=0
            )
            
            # If time has passed today, schedule for tomorrow
            if next_run <= now:
                next_run += timedelta(days=1)
            
            return next_run
        
        elif schedule_type == "once":
            # Run once at specified time or immediately
            return config.get('run_at', now)
        
        else:
            # Default to immediate execution
            return now

    async def _task_scheduler(self):
        """Main task scheduler loop"""
        logger.info("📅 Task scheduler started")
        
        while self.is_running:
            try:
                await self._check_and_run_tasks()
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Error in task scheduler: {str(e)}")
                await asyncio.sleep(60)  # Wait longer on error

    async def _check_and_run_tasks(self):
        """Check for tasks that need to run and execute them"""
        now = datetime.utcnow()
        
        for task_id, task in self.tasks.items():
            if not task.enabled:
                continue
            
            if task.next_run and now >= task.next_run:
                # Check if task is already running
                if task_id not in self.running_tasks:
                    await self._execute_task(task)

    async def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task"""
        try:
            logger.info(f"▶️ Starting task: {task.name}")
            
            # Create task result
            result = TaskResult(
                task_id=task.id,
                status=TaskStatus.RUNNING,
                started_at=datetime.utcnow()
            )
            self.task_results[task.id] = result
            
            # Create and start async task
            async_task = asyncio.create_task(self._run_task_with_error_handling(task, result))
            self.running_tasks[task.id] = async_task
            
        except Exception as e:
            logger.error(f"❌ Error executing task {task.name}: {str(e)}")

    async def _run_task_with_error_handling(self, task: ScheduledTask, result: TaskResult):
        """Run task with comprehensive error handling"""
        try:
            # Execute the task function
            task_result = await task.function()
            
            # Update result
            result.status = TaskStatus.COMPLETED
            result.result = task_result
            result.completed_at = datetime.utcnow()
            result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
            
            # Update task metadata
            task.last_run = datetime.utcnow()
            task.run_count += 1
            task.failure_count = 0  # Reset failure count on success
            task.next_run = self._calculate_next_run(task.schedule_type, task.schedule_config)
            
            # Update stats
            self.stats['tasks_completed'] += 1
            self.stats['total_runtime_seconds'] += result.duration_seconds
            
            logger.info(f"✅ Task completed: {task.name} ({result.duration_seconds:.2f}s)")
            
        except Exception as e:
            # Handle task failure
            result.status = TaskStatus.FAILED
            result.error = str(e)
            result.completed_at = datetime.utcnow()
            if result.started_at:
                result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
            
            # Update task failure tracking
            task.failure_count += 1
            self.stats['tasks_failed'] += 1
            
            logger.error(f"❌ Task failed: {task.name} - {str(e)}")
            logger.debug(f"Task error traceback: {traceback.format_exc()}")
            
            # Disable task if too many failures
            if task.failure_count >= task.max_failures:
                task.enabled = False
                logger.warning(f"⚠️ Disabled task {task.name} due to repeated failures")
            else:
                # Reschedule with exponential backoff
                backoff_minutes = 2 ** task.failure_count
                task.next_run = datetime.utcnow() + timedelta(minutes=backoff_minutes)
        
        finally:
            # Remove from running tasks
            self.running_tasks.pop(task.id, None)

    # ==================== TASK IMPLEMENTATIONS ====================

    async def update_ml_predictions(self) -> Dict[str, Any]:
        """Update ML predictions for all active contestants"""
        logger.info("🤖 Starting ML predictions update...")
        
        async with get_db_session() as db:
            try:
                # Get active shows
                active_shows = await db.execute(
                    "SELECT * FROM shows WHERE is_active = true AND status = 'airing'"
                )
                
                updated_count = 0
                predictions_changed = []
                
                for show in active_shows:
                    # Get contestants for show
                    contestants = await db.get_contestants_by_show(show.id, include_eliminated=False)
                    
                    for contestant in contestants:
                        # Get new predictions from ML model
                        old_prediction = contestant.winner_probability
                        predictions = await self.prediction_engine.predict_contestant_outcomes(contestant)
                        
                        # Update contestant predictions
                        await db.update_contestant_predictions(contestant.id, {
                            'elimination_probability': predictions.elimination_probability,
                            'winner_probability': predictions.winner_probability,
                            'next_episode_safe': predictions.next_episode_safe,
                            'confidence_low': predictions.confidence_interval[0],
                            'confidence_high': predictions.confidence_interval[1],
                            'trend': predictions.trend
                        })
                        
                        updated_count += 1
                        
                        # Track significant changes
                        change = abs(predictions.winner_probability - old_prediction)
                        if change > 0.05:  # 5% change threshold
                            predictions_changed.append({
                                'contestant_id': contestant.id,
                                'contestant_name': contestant.name,
                                'old_prediction': old_prediction,
                                'new_prediction': predictions.winner_probability,
                                'change': change,
                                'factors': predictions.factors
                            })
                            
                            # Broadcast prediction update via WebSocket
                            if self.websocket_manager:
                                await self.websocket_manager.broadcast_to_show(show.id, 
                                    format_prediction_update(
                                        contestant.id,
                                        contestant.name,
                                        old_prediction,
                                        predictions.winner_probability,
                                        predictions.confidence_interval[1] - predictions.confidence_interval[0],
                                        predictions.factors
                                    )
                                )
                
                await db.commit()
                
                self.stats['last_ml_update'] = datetime.utcnow()
                
                logger.info(f"✅ Updated {updated_count} contestant predictions")
                logger.info(f"📈 {len(predictions_changed)} significant prediction changes")
                
                return {
                    'updated_count': updated_count,
                    'significant_changes': len(predictions_changed),
                    'changes': predictions_changed
                }
                
            except Exception as e:
                logger.error(f"❌ Error updating ML predictions: {str(e)}")
                raise

    async def analyze_sentiment(self) -> Dict[str, Any]:
        """Analyze social media sentiment for contestants"""
        logger.info("📊 Starting sentiment analysis...")
        
        async with get_db_session() as db:
            try:
                # Get active contestants
                active_contestants = await db.execute(
                    """
                    SELECT c.* FROM contestants c 
                    JOIN shows s ON c.show_id = s.id 
                    WHERE s.is_active = true AND c.is_eliminated = false
                    """
                )
                
                analyzed_count = 0
                sentiment_updates = []
                
                for contestant in active_contestants:
                    # Analyze sentiment
                    sentiment_score = await self.sentiment_analyzer.analyze_contestant_sentiment(contestant)
                    
                    # Update contestant sentiment
                    old_sentiment = contestant.sentiment_score
                    contestant.sentiment_score = sentiment_score
                    
                    analyzed_count += 1
                    
                    # Track significant sentiment changes
                    change = abs(sentiment_score - old_sentiment)
                    if change > 0.2:  # 20% change threshold
                        sentiment_updates.append({
                            'contestant_name': contestant.name,
                            'old_sentiment': old_sentiment,
                            'new_sentiment': sentiment_score,
                            'change': change
                        })
                
                await db.commit()
                
                logger.info(f"✅ Analyzed sentiment for {analyzed_count} contestants")
                
                return {
                    'analyzed_count': analyzed_count,
                    'significant_changes': len(sentiment_updates),
                    'updates': sentiment_updates
                }
                
            except Exception as e:
                logger.error(f"❌ Error analyzing sentiment: {str(e)}")
                raise

    async def sync_external_data(self) -> Dict[str, Any]:
        """Synchronize data from external sources"""
        logger.info("🔄 Starting external data sync...")
        
        try:
            synced_sources = []
            
            # Sync social media follower counts
            await self._sync_social_media_data()
            synced_sources.append("social_media")
            
            # Sync episode schedules
            await self._sync_episode_schedules()
            synced_sources.append("episode_schedules")
            
            # Sync show ratings/viewership
            await self._sync_show_ratings()
            synced_sources.append("show_ratings")
            
            self.stats['last_data_sync'] = datetime.utcnow()
            
            logger.info(f"✅ Synced data from {len(synced_sources)} sources")
            
            return {
                'synced_sources': synced_sources,
                'sync_time': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error syncing external data: {str(e)}")
            raise

    async def _sync_social_media_data(self):
        """Sync social media follower data"""
        # Mock implementation - in production, use real social media APIs
        async with get_db_session() as db:
            contestants = await db.execute(
                "SELECT * FROM contestants WHERE is_eliminated = false"
            )
            
            for contestant in contestants:
                if contestant.instagram:
                    # Mock follower update
                    import random
                    growth = random.randint(-100, 500)
                    # Update follower count in social_media_following JSON field
                    pass

    async def _sync_episode_schedules(self):
        """Sync episode schedules from external sources"""
        # Mock implementation - in production, sync with TV network APIs
        pass

    async def _sync_show_ratings(self):
        """Sync show ratings and viewership data"""
        # Mock implementation - in production, sync with Nielsen or similar
        pass

    async def update_leaderboards(self) -> Dict[str, Any]:
        """Update user rankings and leaderboards"""
        logger.info("🏆 Updating leaderboards...")
        
        async with get_db_session() as db:
            try:
                active_shows = await db.get_active_shows()
                updated_shows = 0
                rank_changes = []
                
                for show in active_shows:
                    # Get all teams for this show ordered by points
                    teams = await db.get_leaderboard(show.id, limit=1000)
                    
                    # Update ranks
                    for i, team in enumerate(teams, 1):
                        old_rank = team.rank
                        new_rank = i
                        
                        if old_rank != new_rank:
                            team.rank = new_rank
                            
                            # Track significant rank changes
                            if old_rank and abs(old_rank - new_rank) >= 5:
                                rank_changes.append({
                                    'user_id': team.user_id,
                                    'show_id': show.id,
                                    'old_rank': old_rank,
                                    'new_rank': new_rank,
                                    'points': team.total_points
                                })
                                
                                # Broadcast rank change via WebSocket
                                if self.websocket_manager:
                                    await self.websocket_manager.broadcast_to_show(show.id, {
                                        'type': 'leaderboard_update',
                                        'user_id': team.user_id,
                                        'old_rank': old_rank,
                                        'new_rank': new_rank,
                                        'total_points': team.total_points,
                                        'timestamp': datetime.utcnow().isoformat()
                                    })
                    
                    updated_shows += 1
                
                await db.commit()
                
                logger.info(f"✅ Updated leaderboards for {updated_shows} shows")
                logger.info(f"📊 {len(rank_changes)} significant rank changes")
                
                return {
                    'updated_shows': updated_shows,
                    'rank_changes': len(rank_changes)
                }
                
            except Exception as e:
                logger.error(f"❌ Error updating leaderboards: {str(e)}")
                raise

    async def detect_episode_events(self) -> Dict[str, Any]:
        """Detect live episode events and award points"""
        logger.info("🔴 Detecting live episode events...")
        
        # Mock implementation - in production, this would:
        # 1. Monitor TV feeds or official show APIs
        # 2. Use computer vision to detect roses, eliminations
        # 3. Award points to users with affected contestants
        
        detected_events = []
        
        # Simulate random episode events during active episodes
        import random
        if random.random() < 0.1:  # 10% chance of event
            # Mock event detection
            event_types = ['rose_ceremony', 'one_on_one', 'group_date', 'drama', 'elimination']
            event_type = random.choice(event_types)
            
            detected_events.append({
                'type': event_type,
                'description': f"Mock {event_type} event detected",
                'timestamp': datetime.utcnow().isoformat()
            })
            
            logger.info(f"🎬 Detected mock episode event: {event_type}")
        
        return {
            'events_detected': len(detected_events),
            'events': detected_events
        }

    async def update_user_statistics(self) -> Dict[str, Any]:
        """Update user statistics and achievements"""
        logger.info("📈 Updating user statistics...")
        
        async with get_db_session() as db:
            try:
                # Update prediction accuracy for all users
                users_updated = 0
                
                users = await db.execute("SELECT * FROM users WHERE is_active = true")
                
                for user in users:
                    # Calculate prediction accuracy
                    predictions = await db.get_user_predictions(user.id)
                    
                    if predictions:
                        correct_predictions = sum(1 for p in predictions if p.is_correct)
                        total_predictions = len(predictions)
                        accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0
                        
                        # Update user stats
                        await db.update_user(user.id, {
                            'prediction_accuracy': accuracy,
                            'total_predictions': total_predictions,
                            'correct_predictions': correct_predictions
                        })
                        
                        users_updated += 1
                
                await db.commit()
                
                logger.info(f"✅ Updated statistics for {users_updated} users")
                
                return {
                    'users_updated': users_updated
                }
                
            except Exception as e:
                logger.error(f"❌ Error updating user statistics: {str(e)}")
                raise

    async def cleanup_database(self) -> Dict[str, Any]:
        """Clean up old data and optimize database"""
        logger.info("🧹 Starting database cleanup...")
        
        async with get_db_session() as db:
            try:
                cleanup_actions = []
                
                # Clean old task results (keep last 1000)
                if len(self.task_results) > 1000:
                    oldest_results = sorted(self.task_results.items(), 
                                          key=lambda x: x[1].started_at or datetime.min)
                    for task_id, _ in oldest_results[:-1000]:
                        del self.task_results[task_id]
                    cleanup_actions.append("task_results")
                
                # Clean old episode events (older than 30 days)
                cutoff_date = datetime.utcnow() - timedelta(days=30)
                old_events = await db.execute(
                    f"DELETE FROM episode_events WHERE created_at < '{cutoff_date}'"
                )
                if old_events.rowcount > 0:
                    cleanup_actions.append(f"episode_events ({old_events.rowcount})")
                
                # Clean expired predictions
                expired_predictions = await db.execute(
                    f"DELETE FROM predictions WHERE created_at < '{cutoff_date}' AND resolved_at IS NULL"
                )
                if expired_predictions.rowcount > 0:
                    cleanup_actions.append(f"expired_predictions ({expired_predictions.rowcount})")
                
                await db.commit()
                
                logger.info(f"✅ Database cleanup completed: {', '.join(cleanup_actions)}")
                
                return {
                    'cleanup_actions': cleanup_actions,
                    'cleaned_at': datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"❌ Error during database cleanup: {str(e)}")
                raise

    async def cleanup_sessions(self) -> Dict[str, Any]:
        """Clean up expired sessions and tokens"""
        logger.info("🔑 Cleaning up expired sessions...")
        
        try:
            # Clean expired tokens from session manager
            session_manager.cleanup_expired_tokens()
            
            # Clean up rate limiting data
            # (Already handled in auth.py rate limiter)
            
            logger.info("✅ Session cleanup completed")
            
            return {
                'cleanup_completed': True,
                'cleaned_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error during session cleanup: {str(e)}")
            raise

    # ==================== MANUAL TASK TRIGGERS ====================

    async def trigger_ml_updates(self) -> Dict[str, Any]:
        """Manually trigger ML model updates"""
        logger.info("🔄 Manually triggering ML updates...")
        return await self.update_ml_predictions()

    async def trigger_data_sync(self) -> Dict[str, Any]:
        """Manually trigger data synchronization"""
        logger.info("🔄 Manually triggering data sync...")
        return await self.sync_external_data()

    # ==================== TASK MANAGEMENT ====================

    def get_task_status(self, task_id: str) -> Optional[TaskResult]:
        """Get status of a specific task"""
        return self.task_results.get(task_id)

    def get_all_task_statuses(self) -> Dict[str, Any]:
        """Get status of all tasks"""
        return {
            'tasks': {task_id: task.to_dict() for task_id, task in self.tasks.items()},
            'running_tasks': list(self.running_tasks.keys()),
            'recent_results': {task_id: result.to_dict() 
                             for task_id, result in list(self.task_results.items())[-10:]},
            'stats': self.stats
        }

    def enable_task(self, task_id: str) -> bool:
        """Enable a disabled task"""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            self.tasks[task_id].failure_count = 0
            self.tasks[task_id].next_run = self._calculate_next_run(
                self.tasks[task_id].schedule_type, 
                self.tasks[task_id].schedule_config
            )
            logger.info(f"✅ Enabled task: {task_id}")
            return True
        return False

    def disable_task(self, task_id: str) -> bool:
        """Disable a task"""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            logger.info(f"❌ Disabled task: {task_id}")
            return True
        return False

    def set_websocket_manager(self, websocket_manager: ConnectionManager):
        """Set the WebSocket manager for real-time updates"""
        self.websocket_manager = websocket_manager

# Export main class
__all__ = ['BackgroundTaskManager', 'TaskStatus', 'TaskPriority', 'TaskResult']
