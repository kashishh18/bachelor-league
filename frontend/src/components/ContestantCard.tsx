import React, { useState } from 'react';
import { 
  Heart, 
  MapPin, 
  Briefcase, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  Star,
  Users,
  Calendar,
  Award,
  AlertTriangle,
  Instagram,
  Twitter,
  Plus,
  X
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Contestant {
  id: string;
  name: string;
  age: number;
  hometown: string;
  occupation: string;
  showId: string;
  isEliminated: boolean;
  eliminationEpisode?: number;
  profileImage: string;
  bio: string;
  socialMedia: {
    instagram?: string;
    twitter?: string;
  };
  stats: {
    rosesReceived: number;
    oneOnOneDates: number;
    groupDates: number;
    dramaScore: number;
    sentimentScore: number;
    screenTime: number;
  };
  predictions: {
    eliminationProbability: number;
    winnerProbability: number;
    nextEpisodeSafe: boolean;
    confidenceInterval: [number, number];
    trend: 'up' | 'down' | 'stable';
  };
  fantasyStats: {
    isOnUserTeam: boolean;
    points: number;
    weeklyPoints: number;
    pickPercentage: number;
  };
}

interface ContestantCardProps {
  contestant: Contestant;
  showType: 'bachelor' | 'bachelorette' | 'bachelor-in-paradise' | 'golden-bachelor' | 'golden-bachelorette';
  isOnUserTeam: boolean;
  onTeamToggle: (contestantId: string) => void;
  compact?: boolean;
}

const ContestantCard: React.FC<ContestantCardProps> = ({
  contestant,
  showType,
  isOnUserTeam,
  onTeamToggle,
  compact = false
}) => {
  const [showDetails, setShowDetails] = useState(false);
  const [imageError, setImageError] = useState(false);

  // Helper functions
  const getPredictionColor = (probability: number) => {
    if (probability >= 0.7) return 'text-green-600 bg-green-50';
    if (probability >= 0.4) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up': return <TrendingUp className="h-3 w-3 text-green-500" />;
      case 'down': return <TrendingDown className="h-3 w-3 text-red-500" />;
      default: return <Minus className="h-3 w-3 text-gray-400" />;
    }
  };

  const getShowSpecificStats = () => {
    switch (showType) {
      case 'bachelor-in-paradise':
        return {
          label: 'Connections',
          value: contestant.stats.rosesReceived + contestant.stats.groupDates,
          icon: Heart
        };
      case 'golden-bachelor':
      case 'golden-bachelorette':
        return {
          label: 'Wisdom Score',
          value: Math.round((contestant.stats.sentimentScore + 1) * 50),
          icon: Star
        };
      default:
        return {
          label: 'Roses',
          value: contestant.stats.rosesReceived,
          icon: Heart
        };
    }
  };

  const showStats = getShowSpecificStats();

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className={`bg-white rounded-xl shadow-md hover:shadow-lg transition-all duration-300 overflow-hidden ${
        contestant.isEliminated ? 'opacity-60' : ''
      } ${isOnUserTeam ? 'ring-2 ring-rose-400' : ''}`}
    >
      {/* Header Image */}
      <div className="relative">
        <div className={`${compact ? 'h-32' : 'h-48'} bg-gradient-to-br from-rose-100 to-pink-100 relative overflow-hidden`}>
          {!imageError ? (
            <img
              src={contestant.profileImage}
              alt={contestant.name}
              className="w-full h-full object-cover"
              onError={() => setImageError(true)}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <div className="text-4xl font-bold text-gray-400">
                {contestant.name.split(' ').map(n => n[0]).join('')}
              </div>
            </div>
          )}
          
          {/* Status Badges */}
          <div className="absolute top-2 left-2 flex gap-1">
            {contestant.isEliminated && (
              <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full">
                Eliminated
              </span>
            )}
            {isOnUserTeam && (
              <span className="bg-rose-500 text-white text-xs px-2 py-1 rounded-full flex items-center gap-1">
                <Star className="h-3 w-3" />
                Team
              </span>
            )}
          </div>

          {/* Prediction Trend */}
          <div className="absolute top-2 right-2 bg-white bg-opacity-90 rounded-full p-1">
            {getTrendIcon(contestant.predictions.trend)}
          </div>

          {/* Team Toggle Button */}
          <div className="absolute bottom-2 right-2">
            <button
              onClick={() => onTeamToggle(contestant.id)}
              disabled={contestant.isEliminated}
              className={`p-2 rounded-full transition-all duration-200 ${
                isOnUserTeam
                  ? 'bg-rose-500 text-white hover:bg-rose-600'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              } ${contestant.isEliminated ? 'opacity-50 cursor-not-allowed' : 'shadow-lg hover:shadow-xl'}`}
            >
              {isOnUserTeam ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Basic Info */}
        <div className="mb-3">
          <h3 className="font-bold text-lg text-gray-900 leading-tight">
            {contestant.name}
          </h3>
          <div className="flex items-center gap-4 text-sm text-gray-600 mt-1">
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {contestant.age}
            </span>
            <span className="flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {contestant.hometown}
            </span>
          </div>
          <div className="flex items-center gap-1 text-sm text-gray-600 mt-1">
            <Briefcase className="h-3 w-3" />
            {contestant.occupation}
          </div>
        </div>

        {/* Fantasy Stats */}
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div className="bg-gray-50 rounded-lg p-2 text-center">
            <div className="text-lg font-bold text-gray-900">
              {contestant.fantasyStats.points}
            </div>
            <div className="text-xs text-gray-600">Points</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-2 text-center">
            <div className="text-lg font-bold text-gray-900 flex items-center justify-center gap-1">
              <showStats.icon className="h-4 w-4" />
              {showStats.value}
            </div>
            <div className="text-xs text-gray-600">{showStats.label}</div>
          </div>
        </div>

        {/* ML Predictions */}
        <div className="space-y-2 mb-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">Win Probability</span>
            <span className={`text-sm font-semibold px-2 py-1 rounded ${
              getPredictionColor(contestant.predictions.winnerProbability)
            }`}>
              {Math.round(contestant.predictions.winnerProbability * 100)}%
            </span>
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">Next Episode Safe</span>
            <span className={`text-xs px-2 py-1 rounded-full ${
              contestant.predictions.nextEpisodeSafe 
                ? 'bg-green-100 text-green-800' 
                : 'bg-red-100 text-red-800'
            }`}>
              {contestant.predictions.nextEpisodeSafe ? 'Safe' : 'At Risk'}
            </span>
          </div>

          {!compact && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Picked by</span>
              <span className="text-sm font-medium">
                {Math.round(contestant.fantasyStats.pickPercentage)}% of users
              </span>
            </div>
          )}
        </div>

        {/* Social Media & More Details Button */}
        <div className="flex items-center justify-between">
          <div className="flex gap-2">
            {contestant.socialMedia.instagram && (
              <a
                href={`https://instagram.com/${contestant.socialMedia.instagram}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-gray-400 hover:text-pink-500 transition-colors"
              >
                <Instagram className="h-4 w-4" />
              </a>
            )}
            {contestant.socialMedia.twitter && (
              <a
                href={`https://twitter.com/${contestant.socialMedia.twitter}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-gray-400 hover:text-blue-500 transition-colors"
              >
                <Twitter className="h-4 w-4" />
              </a>
            )}
          </div>

          {!compact && (
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="text-xs text-rose-600 hover:text-rose-700 font-medium"
            >
              {showDetails ? 'Less' : 'More'} Details
            </button>
          )}
        </div>

        {/* Expanded Details */}
        <AnimatePresence>
          {showDetails && !compact && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="mt-4 pt-4 border-t border-gray-100 space-y-3"
            >
              {/* Bio */}
              <div>
                <h5 className="text-sm font-semibold text-gray-900 mb-1">Bio</h5>
                <p className="text-xs text-gray-600 leading-relaxed">
                  {contestant.bio || 'No bio available yet.'}
                </p>
              </div>

              {/* Detailed Stats */}
              <div>
                <h5 className="text-sm font-semibold text-gray-900 mb-2">Stats</h5>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-600">1-on-1 Dates:</span>
                    <span className="font-medium">{contestant.stats.oneOnOneDates}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Group Dates:</span>
                    <span className="font-medium">{contestant.stats.groupDates}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Drama Score:</span>
                    <span className="font-medium">{Math.round(contestant.stats.dramaScore * 10)}/10</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Fan Sentiment:</span>
                    <span className={`font-medium ${
                      contestant.stats.sentimentScore > 0.2 ? 'text-green-600' :
                      contestant.stats.sentimentScore < -0.2 ? 'text-red-600' : 'text-gray-600'
                    }`}>
                      {contestant.stats.sentimentScore > 0.2 ? 'Positive' :
                       contestant.stats.sentimentScore < -0.2 ? 'Negative' : 'Neutral'}
                    </span>
                  </div>
                </div>
              </div>

              {/* AI Confidence */}
              <div>
                <h5 className="text-sm font-semibold text-gray-900 mb-1">AI Confidence</h5>
                <div className="text-xs text-gray-600">
                  Prediction range: {Math.round(contestant.predictions.confidenceInterval[0] * 100)}% - {Math.round(contestant.predictions.confidenceInterval[1] * 100)}%
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Weekly Points Indicator */}
        {contestant.fantasyStats.weeklyPoints !== 0 && (
          <div className={`mt-3 p-2 rounded-lg text-center text-sm font-medium ${
            contestant.fantasyStats.weeklyPoints > 0 
              ? 'bg-green-50 text-green-700' 
              : 'bg-red-50 text-red-700'
          }`}>
            {contestant.fantasyStats.weeklyPoints > 0 ? '+' : ''}{contestant.fantasyStats.weeklyPoints} this week
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default ContestantCard;
