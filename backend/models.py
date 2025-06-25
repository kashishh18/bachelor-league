
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey, Table, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from datetime import datetime
import uuid
from enum import Enum
from typing import List, Dict, Any, Optional

Base = declarative_base()

# Enums for type safety
class ShowType(str, Enum):
    BACHELOR = "bachelor"
    BACHELORETTE = "bachelorette"
    BACHELOR_IN_PARADISE = "bachelor-in-paradise"
    GOLDEN_BACHELOR = "golden-bachelor"
    GOLDEN_BACHELORETTE = "golden-bachelorette"

class ShowStatus(str, Enum):
    UPCOMING = "upcoming"
    AIRING = "airing"
    COMPLETED = "completed"

class EpisodeEventType(str, Enum):
    ROSE_CEREMONY = "rose_ceremony"
    ONE_ON_ONE = "one_on_one"
    GROUP_DATE = "group_date"
    DRAMA = "drama"
    ELIMINATION = "elimination"
    FANTASY_SUITE = "fantasy_suite"
    HOMETOWN = "hometown"
    FINALE = "finale"

class PredictionType(str, Enum):
    ELIMINATION = "elimination"
    WINNER = "winner"
    ROSES = "roses"
    DRAMA_SCORE = "drama_score"

# Association tables for many-to-many relationships
user_team_contestants = Table(
    'user_team_contestants',
    Base.metadata,
    Column('team_id', String, ForeignKey('user_teams.id')),
    Column('contestant_id', String, ForeignKey('contestants.id'))
)

user_friends = Table(
    'user_friends',
    Base.metadata,
    Column('user_id', String, ForeignKey('users.id')),
    Column('friend_id', String, ForeignKey('users.id'))
)

# ==================== USER MODELS ====================

class User(Base):
    """User model for authentication and profile management"""
    __tablename__ = "users"
    
    # Primary fields
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile information
    first_name = Column(String(100))
    last_name = Column(String(100))
    avatar_url = Column(String(500))
    bio = Column(Text)
    location = Column(String(100))
    
    # Fantasy stats
    total_points = Column(Integer, default=0)
    current_rank = Column(Integer)
    seasons_participated = Column(Integer, default=0)
    total_leagues = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    top_three_finishes = Column(Integer, default=0)
    average_rank = Column(Float)
    best_rank = Column(Integer)
    points_this_season = Column(Integer, default=0)
    points_all_time = Column(Integer, default=0)
    
    # Prediction accuracy
    total_predictions = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    prediction_accuracy = Column(Float, default=0.0)
    longest_streak = Column(Integer, default=0)
    current_streak = Column(Integer, default=0)
    
    # Preferences
    favorite_show = Column(String(50))
    email_notifications = Column(Boolean, default=True)
    push_notifications = Column(Boolean, default=True)
    spoiler_protection = Column(Boolean, default=False)
    auto_pick_team = Column(Boolean, default=False)
    favorite_show_types = Column(Text, default="")
    
    # System fields
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    teams = relationship("UserTeam", back_populates="user", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="user", cascade="all, delete-orphan")
    league_memberships = relationship("LeagueMembership", back_populates="user")
    
    # Self-referential many-to-many for friends
    friends = relationship(
        "User",
        secondary=user_friends,
        primaryjoin=id == user_friends.c.user_id,
        secondaryjoin=id == user_friends.c.friend_id,
        back_populates="friends"
    )

# ==================== SHOW MODELS ====================

class Show(Base):
    """Bachelor franchise show model"""
    __tablename__ = "shows"
    
    # Primary fields
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    type = Column(String(30), nullable=False)  # ShowType enum
    season = Column(Integer, nullable=False)
    
    # Show details
    lead = Column(String(100), nullable=False)
    network = Column(String(20), default="ABC")
    description = Column(Text)
    location = Column(String(100))
    logo_url = Column(String(500))
    
    # Episode information
    current_episode = Column(Integer, default=1)
    total_episodes = Column(Integer, default=12)
    episode_duration = Column(Integer, default=90)  # minutes
    
    # Dates and status
    premiere_date = Column(DateTime, nullable=False)
    finale_date = Column(DateTime)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    status = Column(String(20), default=ShowStatus.UPCOMING)  # ShowStatus enum
    is_active = Column(Boolean, default=False)
    
    # Social media and metadata
    hashtag = Column(String(50))
    social_handles = Column(JSON)  # {"instagram": "@bachelor", "twitter": "@BachelorABC"}
    viewing_info = Column(JSON)  # Streaming platforms, time slots, etc.
    
    # System fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    contestants = relationship("Contestant", back_populates="show", cascade="all, delete-orphan")
    episodes = relationship("Episode", back_populates="show", cascade="all, delete-orphan")
    user_teams = relationship("UserTeam", back_populates="show")
    leagues = relationship("League", back_populates="show")
    
    # Indexes
    __table_args__ = (
        Index('ix_shows_type_season', 'type', 'season'),
        Index('ix_shows_status_active', 'status', 'is_active'),
    )

class Episode(Base):
    """Individual episode model"""
    __tablename__ = "episodes"
    
    # Primary fields
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    show_id = Column(String, ForeignKey('shows.id'), nullable=False)
    episode_number = Column(Integer, nullable=False)
    
    # Episode details
    title = Column(String(200))
    description = Column(Text)
    air_date = Column(DateTime, nullable=False)
    duration = Column(Integer, default=90)  # minutes
    location = Column(String(100))
    
    # Episode type and status
    episode_type = Column(String(30), default="regular")  # regular, special, finale, reunion
    is_live = Column(Boolean, default=False)
    has_aired = Column(Boolean, default=False)
    
    # Content metadata
    preview_url = Column(String(500))
    highlights = Column(JSON)  # Key moments, timestamps
    contestants_featured = Column(Text)
    
    # System fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    show = relationship("Show", back_populates="episodes")
    events = relationship("EpisodeEvent", back_populates="episode", cascade="all, delete-orphan")

# ==================== CONTESTANT MODELS ====================

class Contestant(Base):
    """Contestant model with comprehensive stats and ML predictions"""
    __tablename__ = "contestants"
    
    # Primary fields
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    show_id = Column(String, ForeignKey('shows.id'), nullable=False)
    
    # Basic information
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    hometown = Column(String(100))
    occupation = Column(String(100))
    bio = Column(Text)
    profile_image = Column(String(500))
    
    # Physical attributes (for some shows)
    height = Column(String(20))
    education = Column(String(200))
    family_info = Column(JSON)
    
    # Show participation
    is_eliminated = Column(Boolean, default=False)
    elimination_episode = Column(Integer)
    elimination_reason = Column(String(200))
    final_placement = Column(Integer)
    
    # Fantasy stats
    roses_received = Column(Integer, default=0)
    one_on_one_dates = Column(Integer, default=0)
    group_dates = Column(Integer, default=0)
    screen_time = Column(Float, default=0.0)  # minutes
    confessional_count = Column(Integer, default=0)
    
    # Social and drama metrics
    drama_score = Column(Float, default=0.0)  # 0-10 scale
    sentiment_score = Column(Float, default=0.0)  # -1 to 1
    social_media_following = Column(JSON)  # Before/during/after show
    fan_favorite_score = Column(Float, default=0.0)
    
    # Social media handles
    instagram = Column(String(100))
    twitter = Column(String(100))
    tiktok = Column(String(100))
    
    # ML predictions (updated regularly)
    elimination_probability = Column(Float, default=0.0)
    winner_probability = Column(Float, default=0.0)
    next_episode_safe = Column(Boolean, default=True)
    confidence_interval_low = Column(Float, default=0.0)
    confidence_interval_high = Column(Float, default=1.0)
    prediction_trend = Column(String(20), default="stable")  # up, down, stable
    
    # Personality and compatibility scores
    personality_type = Column(String(20))  # MBTI, etc.
    compatibility_score = Column(Float)  # With lead
    edit_portrayal = Column(String(50))  # hero, villain, comic relief, etc.
    
    # System fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    show = relationship("Show", back_populates="contestants")
    predictions = relationship("Prediction", back_populates="contestant")
    episode_events = relationship("EpisodeEvent", back_populates="contestants", secondary="episode_event_contestants")
    
    # Indexes
    __table_args__ = (
        Index('ix_contestants_show_elimination', 'show_id', 'is_eliminated'),
        Index('ix_contestants_winner_probability', 'winner_probability'),
    )

# ==================== FANTASY TEAM MODELS ====================

class UserTeam(Base):
    """User's fantasy team for a specific show"""
    __tablename__ = "user_teams"
    
    # Primary fields
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    show_id = Column(String, ForeignKey('shows.id'), nullable=False)
    
    # Team details
    team_name = Column(String(100))
    total_points = Column(Integer, default=0)
    weekly_points = Column(Integer, default=0)
    rank = Column(Integer)
    league_name = Column(String(100), default="Global League")
    
    # Team configuration
    max_contestants = Column(Integer, default=8)
    auto_substitute = Column(Boolean, default=False)
    locked_until = Column(DateTime)  # When team changes are locked
    
    # Performance tracking
    weekly_rank_history = Column(JSON, default=[])  # Historical ranks
    points_history = Column(JSON, default=[])  # Weekly points
    best_week_points = Column(Integer, default=0)
    worst_week_points = Column(Integer, default=0)
    
    # System fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="teams")
    show = relationship("Show", back_populates="user_teams")
    contestants = relationship("Contestant", secondary=user_team_contestants)
    
    # Unique constraint
    __table_args__ = (
        Index('ix_user_teams_user_show', 'user_id', 'show_id', unique=True),
    )

class League(Base):
    """Custom leagues between friends"""
    __tablename__ = "leagues"
    
    # Primary fields
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    show_id = Column(String, ForeignKey('shows.id'), nullable=False)
    creator_id = Column(String, ForeignKey('users.id'), nullable=False)
    
    # League details
    name = Column(String(100), nullable=False)
    description = Column(Text)
    league_code = Column(String(10), unique=True)  # For joining
    max_members = Column(Integer, default=20)
    
    # League settings
    is_public = Column(Boolean, default=False)
    requires_approval = Column(Boolean, default=False)
    entry_fee = Column(Float, default=0.0)
    prize_pool = Column(Float, default=0.0)
    
    # Scoring rules
    custom_scoring = Column(JSON)  # Custom point values
    playoff_format = Column(String(50), default="standard")
    
    # System fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    show = relationship("Show", back_populates="leagues")
    creator = relationship("User")
    members = relationship("LeagueMembership", back_populates="league")

class LeagueMembership(Base):
    """User membership in leagues"""
    __tablename__ = "league_memberships"
    
    # Primary fields
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    league_id = Column(String, ForeignKey('leagues.id'), nullable=False)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    
    # Membership details
    joined_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # League performance
    league_points = Column(Integer, default=0)
    league_rank = Column(Integer)
    
    # Relationships
    league = relationship("League", back_populates="members")
    user = relationship("User", back_populates="league_memberships")

# ==================== PREDICTION MODELS ====================

class Prediction(Base):
    """User predictions for contestants and episodes"""
    __tablename__ = "predictions"
    
    # Primary fields
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    contestant_id = Column(String, ForeignKey('contestants.id'), nullable=False)
    show_id = Column(String, ForeignKey('shows.id'), nullable=False)
    
    # Prediction details
    prediction_type = Column(String(30), nullable=False)  # PredictionType enum
    prediction_value = Column(Float, nullable=False)
    confidence = Column(Float, default=0.5)  # 0-1 scale
    
    # Episode context
    episode_number = Column(Integer)
    made_before_episode = Column(Boolean, default=True)
    
    # Result tracking
    actual_result = Column(Float)
    is_correct = Column(Boolean)
    points_earned = Column(Integer, default=0)
    
    # System fields
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="predictions")
    contestant = relationship("Contestant", back_populates="predictions")
    
    # Indexes
    __table_args__ = (
        Index('ix_predictions_user_show', 'user_id', 'show_id'),
        Index('ix_predictions_type_episode', 'prediction_type', 'episode_number'),
    )

# ==================== EPISODE EVENT MODELS ====================

# Association table for episode events and contestants
episode_event_contestants = Table(
    'episode_event_contestants',
    Base.metadata,
    Column('event_id', String, ForeignKey('episode_events.id')),
    Column('contestant_id', String, ForeignKey('contestants.id'))
)

class EpisodeEvent(Base):
    """Real-time episode events for live scoring"""
    __tablename__ = "episode_events"
    
    # Primary fields
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    episode_id = Column(String, ForeignKey('episodes.id'), nullable=False)
    show_id = Column(String, ForeignKey('shows.id'), nullable=False)
    
    # Event details
    event_type = Column(String(30), nullable=False)  # EpisodeEventType enum
    description = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Scoring
    base_points = Column(Integer, default=0)
    multiplier = Column(Float, default=1.0)
    
    # Event metadata
    location = Column(String(100))
    duration = Column(Integer)  # minutes
    drama_level = Column(Integer, default=1)  # 1-10 scale
    
    # System fields
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    episode = relationship("Episode", back_populates="events")
    contestants = relationship("Contestant", secondary=episode_event_contestants)

# ==================== ANALYTICS MODELS ====================

class LeagueStats(Base):
    """Aggregated league statistics"""
    __tablename__ = "league_stats"
    
    # Primary fields
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    show_id = Column(String, ForeignKey('shows.id'), nullable=False)
    
    # Participation stats
    total_users = Column(Integer, default=0)
    active_users = Column(Integer, default=0)
    total_teams = Column(Integer, default=0)
    total_predictions = Column(Integer, default=0)
    
    # Scoring stats
    average_score = Column(Float, default=0.0)
    median_score = Column(Float, default=0.0)
    top_score = Column(Integer, default=0)
    weekly_leader = Column(String(100))
    weekly_top_score = Column(Integer, default=0)
    
    # Contestant popularity
    most_picked_contestant = Column(String(100))
    least_picked_contestant = Column(String(100))
    biggest_surprise = Column(String(100))  # Unexpected performer
    
    # Prediction accuracy
    average_prediction_accuracy = Column(Float, default=0.0)
    best_predictor = Column(String(100))
    most_accurate_prediction_type = Column(String(30))
    
    # System fields
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    # Additional metrics as JSON
    detailed_stats = Column(JSON, default={})

# ==================== HELPER FUNCTIONS ====================

def create_indexes():
    """Create additional indexes for performance"""
    # Performance-critical indexes are defined in __table_args__
    # Additional indexes can be added here
    pass

def get_contestant_fantasy_stats(contestant_id: str, db_session):
    """Helper function to calculate fantasy stats for a contestant"""
    # This would calculate pick percentage, average points, etc.
    pass

def calculate_user_rank(user_id: str, show_id: str, db_session):
    """Helper function to calculate user's rank in a show"""
    # This would calculate rank based on total points
    pass

def update_ml_predictions(contestant_id: str, predictions: Dict[str, float], db_session):
    """Helper function to update ML predictions for a contestant"""
    # This would update the prediction fields in the Contestant model
    pass
