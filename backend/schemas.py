from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirmPassword: str
    favorite_show: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    total_points: int
    current_rank: Optional[int]
    favorite_show: Optional[str]
    
    class Config:
        from_attributes = True

class ShowResponse(BaseModel):
    id: str
    name: str
    type: str
    season: int
    lead: str
    is_active: bool
    current_episode: int
    total_episodes: int
    
    class Config:
        from_attributes = True

class ContestantResponse(BaseModel):
    id: str
    name: str
    age: int
    hometown: str
    occupation: str
    is_eliminated: bool
    roses_received: int
    winner_probability: float
    elimination_probability: float
    
    class Config:
        from_attributes = True

class TeamCreate(BaseModel):
    contestants: List[str]

class TeamResponse(BaseModel):
    id: str
    contestants: List[str]
    total_points: int
    weekly_points: int
    rank: Optional[int]
    
    class Config:
        from_attributes = True

class PredictionCreate(BaseModel):
    contestant_id: str
    prediction_type: str
    prediction_value: float
    confidence: float

class PredictionResponse(BaseModel):
    id: str
    contestant_id: str
    prediction_type: str
    prediction_value: float
    confidence: float
    created_at: datetime
    
    class Config:
        from_attributes = True
