import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, mean_squared_error, classification_report
import joblib
import asyncio
import aiohttp
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import logging
from dataclasses import dataclass
from textblob import TextBlob
import tweepy
import requests
import json
from collections import defaultdict
import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ContestantPredictions:
    """Data class for contestant prediction results"""
    elimination_probability: float
    winner_probability: float
    next_episode_safe: bool
    confidence_interval: Tuple[float, float]
    trend: str  # 'up', 'down', 'stable'
    factors: List[str]
    sentiment_score: float
    social_media_momentum: float

@dataclass
class HistoricalData:
    """Historical contestant data for training"""
    show_type: str
    season: int
    episode: int
    contestant_data: Dict[str, Any]
    final_placement: int
    eliminated_this_episode: bool

class PredictionEngine:
    """Main ML engine for Bachelor Fantasy League predictions"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.encoders = {}
        self.is_loaded = False
        self.feature_importance = {}
        
        # Model configurations
        self.model_configs = {
            'elimination': {
                'model_type': RandomForestClassifier,
                'params': {
                    'n_estimators': 100,
                    'max_depth': 10,
                    'random_state': 42,
                    'class_weight': 'balanced'
                }
            },
            'winner': {
                'model_type': GradientBoostingRegressor,
                'params': {
                    'n_estimators': 150,
                    'learning_rate': 0.1,
                    'max_depth': 8,
                    'random_state': 42
                }
            },
            'placement': {
                'model_type': RandomForestClassifier,
                'params': {
                    'n_estimators': 120,
                    'max_depth': 12,
                    'random_state': 42
                }
            }
        }

    async def load_models(self):
        """Load or train ML models"""
        try:
            # Try to load existing models
            await self._load_existing_models()
            
            if not self.is_loaded:
                logger.info("🤖 Training new ML models...")
                await self._train_models()
                await self._save_models()
            
            logger.info("✅ ML models loaded successfully")
            self.is_loaded = True
            
        except Exception as e:
            logger.error(f"❌ Error loading ML models: {str(e)}")
            # Fallback to basic heuristics if ML fails
            await self._load_fallback_models()

    async def _load_existing_models(self):
        """Load pre-trained models from disk"""
        try:
            for model_name in ['elimination', 'winner', 'placement']:
                model_path = f"models/{model_name}_model.joblib"
                scaler_path = f"models/{model_name}_scaler.joblib"
                
                self.models[model_name] = joblib.load(model_path)
                self.scalers[model_name] = joblib.load(scaler_path)
                
            self.is_loaded = True
            logger.info("📚 Loaded existing ML models")
            
        except FileNotFoundError:
            logger.info("🔄 No existing models found, will train new ones")
            self.is_loaded = False

    async def _train_models(self):
        """Train ML models on historical Bachelor data"""
        try:
            # Generate training data
            training_data = await self._generate_training_data()
            
            if len(training_data) < 100:
                logger.warning("⚠️ Limited training data, using enhanced synthetic data")
                training_data.extend(await self._generate_synthetic_data())
            
            # Prepare features and targets
            features_df = pd.DataFrame([self._extract_features(data) for data in training_data])
            
            # Train elimination model (binary classification)
            elimination_target = [data.eliminated_this_episode for data in training_data]
            await self._train_model('elimination', features_df, elimination_target)
            
            # Train winner probability model (regression)
            winner_target = [1.0 / data.final_placement if data.final_placement <= 3 else 0.0 
                           for data in training_data]
            await self._train_model('winner', features_df, winner_target)
            
            # Train placement model (multi-class classification)
            placement_target = [min(data.final_placement, 10) for data in training_data]
            await self._train_model('placement', features_df, placement_target)
            
            logger.info("🎯 ML models trained successfully")
            
        except Exception as e:
            logger.error(f"❌ Error training models: {str(e)}")
            raise

    async def _generate_training_data(self) -> List[HistoricalData]:
        """Generate training data from historical Bachelor seasons"""
        training_data = []
        
        # Simulate historical data (in production, this would come from database)
        show_types = ['bachelor', 'bachelorette', 'bachelor-in-paradise']
        
        for show_type in show_types:
            for season in range(20, 29):  # Recent seasons
                season_data = await self._simulate_season_data(show_type, season)
                training_data.extend(season_data)
        
        return training_data

    async def _simulate_season_data(self, show_type: str, season: int) -> List[HistoricalData]:
        """Simulate realistic season data based on Bachelor patterns"""
        season_data = []
        num_contestants = 30 if show_type != 'bachelor-in-paradise' else 20
        
        for contestant_idx in range(num_contestants):
            # Simulate contestant journey
            final_placement = contestant_idx + 1
            
            # Generate episode-by-episode data
            max_episodes = 12 if show_type != 'bachelor-in-paradise' else 8
            elimination_episode = min(
                np.random.exponential(scale=3) + 1,
                max_episodes
            ) if final_placement > 1 else max_episodes
            
            for episode in range(1, int(elimination_episode) + 1):
                contestant_data = self._generate_contestant_features(
                    show_type, season, episode, contestant_idx, final_placement
                )
                
                eliminated_this_episode = (episode == int(elimination_episode) and final_placement > 1)
                
                season_data.append(HistoricalData(
                    show_type=show_type,
                    season=season,
                    episode=episode,
                    contestant_data=contestant_data,
                    final_placement=final_placement,
                    eliminated_this_episode=eliminated_this_episode
                ))
        
        return season_data

    def _generate_contestant_features(self, show_type: str, season: int, episode: int, 
                                    contestant_idx: int, final_placement: int) -> Dict[str, Any]:
        """Generate realistic contestant features"""
        # Base features with some realism
        age = np.random.normal(28, 4)
        
        # Performance tends to correlate with final placement
        performance_factor = 1.0 / (final_placement ** 0.3)
        
        # Generate features that correlate with success
        roses_received = max(0, int(np.random.poisson(episode * performance_factor * 0.8)))
        one_on_one_dates = max(0, int(np.random.poisson(performance_factor * 2)))
        group_dates = max(0, int(np.random.poisson(episode * 0.6)))
        screen_time = max(0, np.random.exponential(scale=performance_factor * 10))
        
        # Drama and sentiment
        drama_score = np.random.beta(2, 5) * 10  # Most contestants low drama
        if final_placement > 15:  # Early eliminations often have more drama
            drama_score = np.random.beta(5, 2) * 10
            
        sentiment_score = np.random.normal(performance_factor * 0.5, 0.3)
        sentiment_score = np.clip(sentiment_score, -1, 1)
        
        # Social media (followers tend to correlate with performance)
        social_media_following = int(np.random.lognormal(
            mean=np.log(10000) + performance_factor,
            sigma=1
        ))
        
        return {
            'age': age,
            'episode': episode,
            'roses_received': roses_received,
            'one_on_one_dates': one_on_one_dates,
            'group_dates': group_dates,
            'screen_time': screen_time,
            'drama_score': drama_score,
            'sentiment_score': sentiment_score,
            'social_media_following': social_media_following,
            'show_type': show_type,
            'episode_ratio': episode / 12,  # Progress through season
            'performance_trend': performance_factor
        }

    async def _generate_synthetic_data(self) -> List[HistoricalData]:
        """Generate additional synthetic training data"""
        synthetic_data = []
        
        # Add edge cases and pattern variations
        for _ in range(500):
            show_type = np.random.choice(['bachelor', 'bachelorette', 'bachelor-in-paradise'])
            season = np.random.randint(15, 30)
            episode = np.random.randint(1, 13)
            final_placement = np.random.randint(1, 31)
            
            contestant_data = self._generate_contestant_features(
                show_type, season, episode, 0, final_placement
            )
            
            # Add noise and variations
            contestant_data['drama_score'] += np.random.normal(0, 1)
            contestant_data['sentiment_score'] += np.random.normal(0, 0.2)
            
            eliminated_this_episode = np.random.random() < 0.15  # ~15% elimination rate per episode
            
            synthetic_data.append(HistoricalData(
                show_type=show_type,
                season=season,
                episode=episode,
                contestant_data=contestant_data,
                final_placement=final_placement,
                eliminated_this_episode=eliminated_this_episode
            ))
        
        return synthetic_data

    def _extract_features(self, data: HistoricalData) -> Dict[str, float]:
        """Extract numerical features for ML models"""
        features = data.contestant_data.copy()
        
        # Add derived features
        features['total_dates'] = features['one_on_one_dates'] + features['group_dates']
        features['roses_per_episode'] = features['roses_received'] / max(features['episode'], 1)
        features['screen_time_per_episode'] = features['screen_time'] / max(features['episode'], 1)
        
        # Show type encoding
        show_type_encoding = {
            'bachelor': 0,
            'bachelorette': 1,
            'bachelor-in-paradise': 2
        }
        features['show_type_encoded'] = show_type_encoding.get(features['show_type'], 0)
        
        # Remove non-numeric features
        numeric_features = {k: v for k, v in features.items() 
                          if isinstance(v, (int, float)) and not math.isnan(v)}
        
        return numeric_features

    async def _train_model(self, model_name: str, features_df: pd.DataFrame, target: List):
        """Train a specific model"""
        try:
            # Prepare data
            X = features_df.fillna(0)
            y = np.array(target)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=None
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            model_class = self.model_configs[model_name]['model_type']
            params = self.model_configs[model_name]['params']
            model = model_class(**params)
            
            model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test_scaled)
            
            if model_name == 'elimination':
                accuracy = accuracy_score(y_test, y_pred)
                logger.info(f"📊 {model_name} model accuracy: {accuracy:.3f}")
            else:
                mse = mean_squared_error(y_test, y_pred)
                logger.info(f"📊 {model_name} model MSE: {mse:.3f}")
            
            # Store model and scaler
            self.models[model_name] = model
            self.scalers[model_name] = scaler
            
            # Store feature importance
            if hasattr(model, 'feature_importances_'):
                self.feature_importance[model_name] = dict(
                    zip(X.columns, model.feature_importances_)
                )
            
        except Exception as e:
            logger.error(f"❌ Error training {model_name} model: {str(e)}")
            raise

    async def _save_models(self):
        """Save trained models to disk"""
        try:
            import os
            os.makedirs('models', exist_ok=True)
            
            for model_name in self.models:
                joblib.dump(self.models[model_name], f'models/{model_name}_model.joblib')
                joblib.dump(self.scalers[model_name], f'models/{model_name}_scaler.joblib')
            
            logger.info("💾 Models saved successfully")
            
        except Exception as e:
            logger.error(f"❌ Error saving models: {str(e)}")

    async def _load_fallback_models(self):
        """Load simple heuristic-based fallback models"""
        logger.info("🔄 Loading fallback heuristic models")
        
        # Simple rule-based models as fallback
        self.models['fallback'] = True
        self.is_loaded = True

    async def predict_contestant_outcomes(self, contestant) -> ContestantPredictions:
        """Generate comprehensive predictions for a contestant"""
        try:
            if not self.is_loaded:
                await self.load_models()
            
            # Extract features from contestant
            features = self._extract_contestant_features(contestant)
            
            if 'fallback' in self.models:
                return await self._fallback_predictions(contestant, features)
            
            # ML-based predictions
            elimination_prob = await self._predict_elimination_probability(features)
            winner_prob = await self._predict_winner_probability(features)
            
            # Calculate confidence intervals
            confidence_interval = self._calculate_confidence_interval(
                winner_prob, features
            )
            
            # Determine trend
            trend = await self._calculate_trend(contestant, features)
            
            # Identify key factors
            factors = self._identify_key_factors(features)
            
            # Calculate next episode safety
            next_episode_safe = elimination_prob < 0.3
            
            return ContestantPredictions(
                elimination_probability=elimination_prob,
                winner_probability=winner_prob,
                next_episode_safe=next_episode_safe,
                confidence_interval=confidence_interval,
                trend=trend,
                factors=factors,
                sentiment_score=features.get('sentiment_score', 0.0),
                social_media_momentum=features.get('social_momentum', 0.0)
            )
            
        except Exception as e:
            logger.error(f"❌ Error predicting outcomes for contestant: {str(e)}")
            return await self._fallback_predictions(contestant, {})

    def _extract_contestant_features(self, contestant) -> Dict[str, float]:
        """Extract features from contestant object for prediction"""
        return {
            'age': getattr(contestant, 'age', 25),
            'episode': getattr(contestant, 'current_episode', 1),
            'roses_received': getattr(contestant, 'roses_received', 0),
            'one_on_one_dates': getattr(contestant, 'one_on_one_dates', 0),
            'group_dates': getattr(contestant, 'group_dates', 0),
            'screen_time': getattr(contestant, 'screen_time', 0),
            'drama_score': getattr(contestant, 'drama_score', 0),
            'sentiment_score': getattr(contestant, 'sentiment_score', 0),
            'social_media_following': getattr(contestant, 'social_media_following', {}).get('instagram', 1000),
            'show_type_encoded': self._encode_show_type(getattr(contestant, 'show_type', 'bachelor')),
            'episode_ratio': getattr(contestant, 'current_episode', 1) / 12,
            'total_dates': getattr(contestant, 'one_on_one_dates', 0) + getattr(contestant, 'group_dates', 0),
            'roses_per_episode': getattr(contestant, 'roses_received', 0) / max(getattr(contestant, 'current_episode', 1), 1),
            'is_eliminated': getattr(contestant, 'is_eliminated', False)
        }

    def _encode_show_type(self, show_type: str) -> int:
        """Encode show type as number"""
        encoding = {
            'bachelor': 0,
            'bachelorette': 1,
            'bachelor-in-paradise': 2,
            'golden-bachelor': 3,
            'golden-bachelorette': 4
        }
        return encoding.get(show_type, 0)

    async def _predict_elimination_probability(self, features: Dict[str, float]) -> float:
        """Predict probability of elimination in next episode"""
        try:
            if features.get('is_eliminated', False):
                return 1.0
            
            # Prepare feature vector
            feature_vector = self._prepare_feature_vector(features, 'elimination')
            feature_vector_scaled = self.scalers['elimination'].transform([feature_vector])
            
            # Get prediction
            prob = self.models['elimination'].predict_proba(feature_vector_scaled)[0][1]
            return float(np.clip(prob, 0, 1))
            
        except Exception as e:
            logger.error(f"Error predicting elimination: {str(e)}")
            return 0.5  # Default neutral probability

    async def _predict_winner_probability(self, features: Dict[str, float]) -> float:
        """Predict probability of winning the season"""
        try:
            if features.get('is_eliminated', False):
                return 0.0
            
            # Prepare feature vector
            feature_vector = self._prepare_feature_vector(features, 'winner')
            feature_vector_scaled = self.scalers['winner'].transform([feature_vector])
            
            # Get prediction
            prob = self.models['winner'].predict(feature_vector_scaled)[0]
            return float(np.clip(prob, 0, 1))
            
        except Exception as e:
            logger.error(f"Error predicting winner probability: {str(e)}")
            return 0.1  # Default low probability

    def _prepare_feature_vector(self, features: Dict[str, float], model_name: str) -> List[float]:
        """Prepare feature vector for specific model"""
        # In production, this would use the exact features the model was trained on
        expected_features = [
            'age', 'episode', 'roses_received', 'one_on_one_dates', 'group_dates',
            'screen_time', 'drama_score', 'sentiment_score', 'social_media_following',
            'show_type_encoded', 'episode_ratio', 'total_dates', 'roses_per_episode'
        ]
        
        return [features.get(feature, 0.0) for feature in expected_features]

    def _calculate_confidence_interval(self, prediction: float, features: Dict[str, float]) -> Tuple[float, float]:
        """Calculate confidence interval for prediction"""
        # Simple confidence interval based on data quality
        data_quality = self._assess_data_quality(features)
        uncertainty = (1 - data_quality) * 0.3  # Max 30% uncertainty
        
        lower = max(0, prediction - uncertainty)
        upper = min(1, prediction + uncertainty)
        
        return (lower, upper)

    def _assess_data_quality(self, features: Dict[str, float]) -> float:
        """Assess quality of input data for confidence calculation"""
        # More complete data = higher confidence
        completeness = sum(1 for v in features.values() if v != 0) / len(features)
        
        # Recent episode data is more reliable
        episode_recency = 1.0 - (features.get('episode', 1) / 12) * 0.3
        
        return min(1.0, completeness * episode_recency)

    async def _calculate_trend(self, contestant, features: Dict[str, float]) -> str:
        """Calculate if contestant is trending up, down, or stable"""
        try:
            # In production, this would compare recent performance to historical
            current_performance = (
                features.get('roses_per_episode', 0) * 0.4 +
                features.get('sentiment_score', 0) * 0.3 +
                (1 - features.get('drama_score', 0) / 10) * 0.3
            )
            
            # Mock historical average (in production, query from database)
            historical_average = 0.5
            
            if current_performance > historical_average * 1.1:
                return 'up'
            elif current_performance < historical_average * 0.9:
                return 'down'
            else:
                return 'stable'
                
        except Exception:
            return 'stable'

    def _identify_key_factors(self, features: Dict[str, float]) -> List[str]:
        """Identify key factors influencing prediction"""
        factors = []
        
        # High-impact positive factors
        if features.get('roses_received', 0) > 2:
            factors.append("High rose count")
        if features.get('one_on_one_dates', 0) > 1:
            factors.append("Multiple 1-on-1 dates")
        if features.get('sentiment_score', 0) > 0.3:
            factors.append("Positive fan sentiment")
        
        # High-impact negative factors
        if features.get('drama_score', 0) > 7:
            factors.append("High drama involvement")
        if features.get('screen_time', 0) < 5:
            factors.append("Limited screen time")
        
        # Neutral factors
        if not factors:
            factors.append("Average performance across metrics")
        
        return factors[:3]  # Return top 3 factors

    async def _fallback_predictions(self, contestant, features: Dict[str, float]) -> ContestantPredictions:
        """Simple heuristic-based predictions when ML models aren't available"""
        try:
            # Simple heuristics based on known Bachelor patterns
            roses = features.get('roses_received', 0)
            dates = features.get('one_on_one_dates', 0) + features.get('group_dates', 0)
            drama = features.get('drama_score', 0)
            episode = features.get('episode', 1)
            
            # Winner probability based on roses and dates
            winner_prob = min(0.8, (roses * 0.15 + dates * 0.1) / episode) if episode > 0 else 0.1
            
            # Elimination probability based on performance and drama
            elim_prob = max(0.1, (drama / 10) * 0.3 + (1 - winner_prob) * 0.5)
            
            return ContestantPredictions(
                elimination_probability=elim_prob,
                winner_probability=winner_prob,
                next_episode_safe=elim_prob < 0.4,
                confidence_interval=(max(0, winner_prob - 0.2), min(1, winner_prob + 0.2)),
                trend='stable',
                factors=['Basic performance metrics'],
                sentiment_score=0.0,
                social_media_momentum=0.0
            )
            
        except Exception as e:
            logger.error(f"Error in fallback predictions: {str(e)}")
            return ContestantPredictions(
                elimination_probability=0.5,
                winner_probability=0.1,
                next_episode_safe=True,
                confidence_interval=(0.05, 0.15),
                trend='stable',
                factors=['Insufficient data'],
                sentiment_score=0.0,
                social_media_momentum=0.0
            )

class SentimentAnalyzer:
    """Analyze social media sentiment for contestants"""
    
    def __init__(self):
        self.twitter_api = None
        self.setup_apis()

    def setup_apis(self):
        """Setup social media API connections"""
        try:
            # In production, use environment variables for API keys
            # self.twitter_api = tweepy.API(auth)
            pass
        except Exception as e:
            logger.warning(f"⚠️ Could not setup social media APIs: {str(e)}")

    async def analyze_contestant_sentiment(self, contestant) -> float:
        """Analyze sentiment for a contestant across social media"""
        try:
            # Collect mentions
            mentions = await self._collect_mentions(contestant)
            
            # Analyze sentiment
            if mentions:
                sentiment_scores = [self._analyze_text_sentiment(mention) for mention in mentions]
                return np.mean(sentiment_scores)
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return 0.0

    async def _collect_mentions(self, contestant) -> List[str]:
        """Collect social media mentions for contestant"""
        mentions = []
        
        try:
            # Mock social media data (in production, use real APIs)
            contestant_name = getattr(contestant, 'name', 'Unknown')
            
            # Simulate realistic mentions based on contestant performance
            roses = getattr(contestant, 'roses_received', 0)
            drama = getattr(contestant, 'drama_score', 0)
            
            # Generate mock mentions
            if roses > 2:
                mentions.extend([
                    f"{contestant_name} is such a catch! #Bachelor",
                    f"Really rooting for {contestant_name} this season",
                    f"{contestant_name} and the lead have great chemistry"
                ])
            
            if drama > 7:
                mentions.extend([
                    f"{contestant_name} is causing too much drama",
                    f"Not a fan of {contestant_name}'s behavior",
                    f"{contestant_name} needs to chill out #Bachelor"
                ])
            
            # Add neutral mentions
            mentions.extend([
                f"What do you think about {contestant_name}?",
                f"{contestant_name} looked great in tonight's episode"
            ])
            
        except Exception as e:
            logger.error(f"Error collecting mentions: {str(e)}")
        
        return mentions

    def _analyze_text_sentiment(self, text: str) -> float:
        """Analyze sentiment of individual text"""
        try:
            # Use TextBlob for basic sentiment analysis
            blob = TextBlob(text)
            return blob.sentiment.polarity
            
        except Exception:
            return 0.0

# Export main classes
__all__ = ['PredictionEngine', 'SentimentAnalyzer', 'ContestantPredictions']
