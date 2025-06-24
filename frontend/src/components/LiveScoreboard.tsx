import React, { useState, useEffect, useRef } from 'react';
import { 
  Activity, 
  Users, 
  TrendingUp, 
  Trophy, 
  Heart, 
  Zap,
  Calendar,
  Clock,
  Wifi,
  WifiOff,
  Play,
  Pause,
  RotateCcw,
  Eye,
  Target,
  Award,
  ChevronRight,
  Signal
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useLiveScoring, useConnectionQuality, useSocket } from '../contexts/SocketContext';
import { useShow } from '../contexts/ShowContext';

interface LiveScoreboardProps {
  updates: any[];
  maxItems?: number;
  showConnectionStatus?: boolean;
  autoScroll?: boolean;
}

const LiveScoreboard: React.FC<LiveScoreboardProps> = ({ 
  updates,
  maxItems = 10,
  showConnectionStatus = true,
  autoScroll = true
}) => {
  const { scoreUpdates, episodeEvents, liveStats } = useLiveScoring();
  const { isConnected, qualityColor, qualityLabel } = useConnectionQuality();
  const { clearEvents, reconnect } = useSocket();
  const { currentShow } = useShow();
  
  const [isPaused, setIsPaused] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest updates
  useEffect(() => {
    if (autoScroll && !isPaused && scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [scoreUpdates, episodeEvents, autoScroll, isPaused]);

  // Get event icon based on type
  const getEventIcon = (event: any) => {
    switch (event.type) {
      case 'score_update':
        return <Heart className="h-4 w-4 text-rose-500" />;
      case 'episode_event':
        switch (event.eventType) {
          case 'rose_ceremony':
            return <Heart className="h-4 w-4 text-rose-500" />;
          case 'elimination':
            return <Trophy className="h-4 w-4 text-red-500" />;
          case 'one_on_one':
            return <Heart className="h-4 w-4 text-pink-500" />;
          case 'group_date':
            return <Users className="h-4 w-4 text-blue-500" />;
          case 'drama':
            return <Zap className="h-4 w-4 text-orange-500" />;
          case 'fantasy_suite':
            return <Heart className="h-4 w-4 text-purple-500" />;
          case 'hometown':
            return <Users className="h-4 w-4 text-green-500" />;
          case 'finale':
            return <Trophy className="h-4 w-4 text-gold-500" />;
          default:
            return <Activity className="h-4 w-4 text-gray-500" />;
        }
      case 'prediction_update':
        return <TrendingUp className="h-4 w-4 text-blue-500" />;
      case 'leaderboard_update':
        return <Trophy className="h-4 w-4 text-yellow-500" />;
      case 'friend_activity':
        return <Users className="h-4 w-4 text-indigo-500" />;
      default:
        return <Activity className="h-4 w-4 text-gray-500" />;
    }
  };

  // Format timestamp
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    return date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  };

  // Get event description
  const getEventDescription = (event: any) => {
    switch (event.type) {
      case 'score_update':
        return `${event.contestantName} earned ${event.points} points - ${event.reason}`;
      case 'episode_event':
        return event.description;
      case 'prediction_update':
        const change = Math.round((event.newPrediction - event.oldPrediction) * 100);
        const direction = change > 0 ? '↗️' : '↘️';
        return `${event.contestantName}'s win probability ${direction} ${Math.abs(change)}% (${Math.round(event.newPrediction * 100)}%)`;
      case 'leaderboard_update':
        const rankChange = event.oldRank - event.newRank;
        return rankChange > 0 
          ? `${event.username} moved up ${rankChange} spots to #${event.newRank}`
          : `${event.username} dropped ${Math.abs(rankChange)} spots to #${event.newRank}`;
      case 'friend_activity':
        return `${event.username} ${event.details}`;
      default:
        return 'Unknown event';
    }
  };

  // Combine and sort all events
  const allEvents = [...scoreUpdates, ...episodeEvents, ...updates]
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, maxItems);

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <Activity className="h-5 w-5 text-rose-600" />
              {isConnected && (
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
              )}
            </div>
            <h3 className="text-lg font-semibold text-gray-900">Live Updates</h3>
            {currentShow && (
              <span className="text-sm text-gray-600">
                Episode {currentShow.currentEpisode}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Connection Status */}
            {showConnectionStatus && (
              <div className="flex items-center gap-1">
                {isConnected ? (
                  <Wifi className={`h-4 w-4 ${qualityColor}`} />
                ) : (
                  <WifiOff className="h-4 w-4 text-red-500" />
                )}
                <span className={`text-xs font-medium ${qualityColor}`}>
                  {qualityLabel}
                </span>
              </div>
            )}

            {/* Controls */}
            <div className="flex items-center gap-1">
              <button
                onClick={() => setIsPaused(!isPaused)}
                className="p-1 rounded text-gray-400 hover:text-gray-600 transition-colors"
                title={isPaused ? 'Resume' : 'Pause'}
              >
                {isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
              </button>
              
              <button
                onClick={clearEvents}
                className="p-1 rounded text-gray-400 hover:text-gray-600 transition-colors"
                title="Clear events"
              >
                <RotateCcw className="h-4 w-4" />
              </button>

              {!isConnected && (
                <button
                  onClick={reconnect}
                  className="p-1 rounded text-red-400 hover:text-red-600 transition-colors"
                  title="Reconnect"
                >
                  <Signal className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Live Stats */}
        {liveStats && (
          <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-lg font-bold text-gray-900">{liveStats.viewersCount.toLocaleString()}</div>
              <div className="text-xs text-gray-600">Live Viewers</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-gray-900">{liveStats.activePredictions}</div>
              <div className="text-xs text-gray-600">Active Predictions</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-gray-900">{liveStats.totalPoints.toLocaleString()}</div>
              <div className="text-xs text-gray-600">Points Awarded</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-gray-900">{liveStats.topPerformer.points}</div>
              <div className="text-xs text-gray-600">{liveStats.topPerformer.username}</div>
            </div>
          </div>
        )}
      </div>

      {/* Events Feed */}
      <div 
        ref={scrollRef}
        className="max-h-80 overflow-y-auto"
        style={{ scrollBehavior: autoScroll ? 'smooth' : 'auto' }}
      >
        {!isConnected && (
          <div className="p-6 text-center">
            <WifiOff className="h-8 w-8 text-gray-400 mx-auto mb-2" />
            <p className="text-sm text-gray-600 mb-3">
              Connection lost. Live updates are paused.
            </p>
            <button
              onClick={reconnect}
              className="text-sm text-rose-600 hover:text-rose-700 font-medium"
            >
              Try reconnecting
            </button>
          </div>
        )}

        {allEvents.length === 0 && isConnected ? (
          <div className="p-6 text-center">
            <Eye className="h-8 w-8 text-gray-400 mx-auto mb-2" />
            <p className="text-sm text-gray-600">
              Waiting for live updates...
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Events will appear here when the episode airs
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            <AnimatePresence mode="popLayout">
              {allEvents.map((event, index) => (
                <motion.div
                  key={`${event.type}-${event.timestamp}-${index}`}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: isPaused ? 0.6 : 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ duration: 0.3 }}
                  className="p-4 hover:bg-gray-50 transition-colors cursor-pointer"
                  onClick={() => setShowDetails(!showDetails)}
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 mt-0.5">
                      {getEventIcon(event)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm text-gray-900 leading-relaxed">
                          {getEventDescription(event)}
                        </p>
                        <div className="flex-shrink-0 flex items-center gap-1">
                          <span className="text-xs text-gray-500">
                            {formatTime(event.timestamp)}
                          </span>
                          <ChevronRight className="h-3 w-3 text-gray-400" />
                        </div>
                      </div>

                      {/* Additional details */}
                      {showDetails && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="mt-2 text-xs text-gray-600 space-y-1"
                        >
                          {event.type === 'score_update' && (
                            <div>Episode {event.episode} • Show: {event.showId}</div>
                          )}
                          {event.type === 'prediction_update' && (
                            <div>
                              Confidence: {Math.round(event.confidence * 100)}% • 
                              Factors: {event.factors?.join(', ')}
                            </div>
                          )}
                          {event.contestants && event.contestants.length > 0 && (
                            <div>Contestants: {event.contestants.join(', ')}</div>
                          )}
                        </motion.div>
                      )}
                    </div>
                  </div>

                  {/* Point indicator for score updates */}
                  {event.type === 'score_update' && event.points && (
                    <div className="ml-7 mt-1">
                      <span className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full ${
                        event.points > 0 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {event.points > 0 ? '+' : ''}{event.points} pts
                      </span>
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
        <div className="flex items-center justify-between text-xs text-gray-600">
          <div className="flex items-center gap-4">
            <span>
              {allEvents.length} recent events
            </span>
            {isPaused && (
              <span className="flex items-center gap-1 text-orange-600">
                <Pause className="h-3 w-3" />
                Paused
              </span>
            )}
          </div>
          
          <div className="flex items-center gap-1">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span>{isConnected ? 'Live' : 'Offline'}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LiveScoreboard;
