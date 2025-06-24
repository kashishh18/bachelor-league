import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { Socket } from 'socket.io-client';
import toast from 'react-hot-toast';
import { useAuth } from './AuthContext';

// Types for real-time events
interface ScoreUpdate {
  type: 'score_update';
  contestantId: string;
  contestantName: string;
  showId: string;
  points: number;
  reason: string;
  episode: number;
  timestamp: string;
  userId?: string;
}

interface EpisodeEvent {
  type: 'episode_event';
  eventType: 'rose_ceremony' | 'one_on_one' | 'group_date' | 'drama' | 'elimination' | 'fantasy_suite' | 'hometown' | 'finale';
  showId: string;
  episode: number;
  contestants: string[];
  description: string;
  timestamp: string;
  points?: number;
}

interface PredictionUpdate {
  type: 'prediction_update';
  contestantId: string;
  contestantName: string;
  showId: string;
  oldPrediction: number;
  newPrediction: number;
  confidence: number;
  factors: string[];
  timestamp: string;
}

interface LeaderboardUpdate {
  type: 'leaderboard_update';
  showId: string;
  userId: string;
  username: string;
  oldRank: number;
  newRank: number;
  totalPoints: number;
  weeklyPoints: number;
  timestamp: string;
}

interface FriendActivity {
  type: 'friend_activity';
  userId: string;
  username: string;
  avatar?: string;
  action: 'team_update' | 'prediction_made' | 'achievement_unlocked' | 'league_joined';
  details: string;
  showId: string;
  timestamp: string;
}

interface LiveStats {
  viewersCount: number;
  activePredictions: number;
  totalPoints: number;
  topPerformer: {
    username: string;
    points: number;
  };
  recentEvents: number;
}

interface ConnectionStatus {
  isConnected: boolean;
  isReconnecting: boolean;
  lastConnected?: string;
  connectionQuality: 'excellent' | 'good' | 'poor' | 'disconnected';
}

type SocketEvent = ScoreUpdate | EpisodeEvent | PredictionUpdate | LeaderboardUpdate | FriendActivity;

interface SocketContextType {
  socket: Socket | null;
  isConnected: boolean;
  connectionStatus: ConnectionStatus;
  liveStats: LiveStats | null;
  recentEvents: SocketEvent[];
  subscribedShows: string[];
  subscribeToShow: (showId: string) => void;
  unsubscribeFromShow: (showId: string) => void;
  sendPrediction: (contestantId: string, prediction: any) => void;
  sendTeamUpdate: (teamData: any) => void;
  clearEvents: () => void;
  reconnect: () => void;
}

// Create Context
const SocketContext = createContext<SocketContextType | undefined>(undefined);

// Provider Component
export const SocketProvider: React.FC<{ children: ReactNode; socket: Socket | null }> = ({ 
  children, 
  socket 
}) => {
  const { user, isAuthenticated } = useAuth();
  
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    isConnected: false,
    isReconnecting: false,
    connectionQuality: 'disconnected'
  });
  const [liveStats, setLiveStats] = useState<LiveStats | null>(null);
  const [recentEvents, setRecentEvents] = useState<SocketEvent[]>([]);
  const [subscribedShows, setSubscribedShows] = useState<string[]>([]);

  // Connection management
  useEffect(() => {
    if (!socket) return;

    const handleConnect = () => {
      console.log('📡 Connected to real-time server');
      setIsConnected(true);
      setConnectionStatus({
        isConnected: true,
        isReconnecting: false,
        lastConnected: new Date().toISOString(),
        connectionQuality: 'excellent'
      });
      
      toast.success('🔴 Live updates connected!', {
        duration: 2000,
        icon: '📡'
      });

      // Authenticate socket connection
      if (isAuthenticated && user) {
        socket.emit('authenticate', {
          userId: user.id,
          username: user.username
        });
      }
    };

    const handleDisconnect = (reason: string) => {
      console.log('📡 Disconnected from server:', reason);
      setIsConnected(false);
      setConnectionStatus(prev => ({
        ...prev,
        isConnected: false,
        connectionQuality: 'disconnected'
      }));
      
      if (reason !== 'io client disconnect') {
        toast.error('Connection lost. Reconnecting...', {
          duration: 3000,
          icon: '📡'
        });
      }
    };

    const handleReconnect = () => {
      console.log('📡 Reconnected to server');
      setConnectionStatus(prev => ({
        ...prev,
        isReconnecting: false,
        isConnected: true,
        connectionQuality: 'good'
      }));
      
      toast.success('🔄 Reconnected to live updates!', {
        duration: 2000
      });
    };

    const handleReconnectAttempt = () => {
      setConnectionStatus(prev => ({
        ...prev,
        isReconnecting: true,
        connectionQuality: 'poor'
      }));
    };

    // Socket event listeners
    socket.on('connect', handleConnect);
    socket.on('disconnect', handleDisconnect);
    socket.on('reconnect', handleReconnect);
    socket.on('reconnect_attempt', handleReconnectAttempt);

    return () => {
      socket.off('connect', handleConnect);
      socket.off('disconnect', handleDisconnect);
      socket.off('reconnect', handleReconnect);
      socket.off('reconnect_attempt', handleReconnectAttempt);
    };
  }, [socket, isAuthenticated, user]);

  // Real-time event handlers
  useEffect(() => {
    if (!socket || !isConnected) return;

    // Score updates (when contestants earn points)
    const handleScoreUpdate = (data: ScoreUpdate) => {
      console.log('💯 Score update:', data);
      setRecentEvents(prev => [data, ...prev.slice(0, 19)]); // Keep last 20 events
      
      // Show toast for user's team members
      if (data.userId === user?.id) {
        toast.success(
          `🌹 ${data.contestantName} earned ${data.points} points!\n${data.reason}`,
          {
            duration: 4000,
            icon: '🎉'
          }
        );
      }
    };

    // Episode events (roses, dates, eliminations)
    const handleEpisodeEvent = (data: EpisodeEvent) => {
      console.log('📺 Episode event:', data);
      setRecentEvents(prev => [data, ...prev.slice(0, 19)]);
      
      let icon = '📺';
      let message = data.description;
      
      switch (data.eventType) {
        case 'rose_ceremony':
          icon = '🌹';
          break;
        case 'elimination':
          icon = '😢';
          message = `${data.description} - Fantasy points updated!`;
          break;
        case 'one_on_one':
          icon = '💕';
          break;
        case 'group_date':
          icon = '👥';
          break;
        case 'drama':
          icon = '🔥';
          break;
        case 'fantasy_suite':
          icon = '🏨';
          break;
        case 'hometown':
          icon = '🏠';
          break;
        case 'finale':
          icon = '👑';
          break;
      }
      
      toast(message, {
        icon,
        duration: 5000,
        style: {
          background: '#fef2f2',
          border: '1px solid #fecaca',
          color: '#991b1b'
        }
      });
    };

    // ML prediction updates
    const handlePredictionUpdate = (data: PredictionUpdate) => {
      console.log('🤖 Prediction update:', data);
      setRecentEvents(prev => [data, ...prev.slice(0, 19)]);
      
      const change = data.newPrediction - data.oldPrediction;
      const direction = change > 0 ? '📈' : '📉';
      
      toast(
        `${direction} AI updated ${data.contestantName}'s win probability: ${Math.round(data.newPrediction * 100)}%`,
        {
          duration: 3000,
          icon: '🤖'
        }
      );
    };

    // Leaderboard updates
    const handleLeaderboardUpdate = (data: LeaderboardUpdate) => {
      console.log('🏆 Leaderboard update:', data);
      setRecentEvents(prev => [data, ...prev.slice(0, 19)]);
      
      if (data.userId === user?.id) {
        const rankChange = data.oldRank - data.newRank;
        if (rankChange > 0) {
          toast.success(
            `🚀 You moved up ${rankChange} spot${rankChange > 1 ? 's' : ''} to rank #${data.newRank}!`,
            {
              duration: 4000,
              icon: '🏆'
            }
          );
        }
      }
    };

    // Friend activity
    const handleFriendActivity = (data: FriendActivity) => {
      console.log('👥 Friend activity:', data);
      setRecentEvents(prev => [data, ...prev.slice(0, 19)]);
      
      // Only show notifications for close friends or significant activities
      if (data.action === 'achievement_unlocked') {
        toast(`🎉 ${data.username} ${data.details}`, {
          duration: 3000,
          icon: '🏅'
        });
      }
    };

    // Live statistics updates
    const handleLiveStats = (data: LiveStats) => {
      setLiveStats(data);
    };

    // Register event listeners
    socket.on('score_update', handleScoreUpdate);
    socket.on('episode_event', handleEpisodeEvent);
    socket.on('prediction_update', handlePredictionUpdate);
    socket.on('leaderboard_update', handleLeaderboardUpdate);
    socket.on('friend_activity', handleFriendActivity);
    socket.on('live_stats', handleLiveStats);

    return () => {
      socket.off('score_update', handleScoreUpdate);
      socket.off('episode_event', handleEpisodeEvent);
      socket.off('prediction_update', handlePredictionUpdate);
      socket.off('leaderboard_update', handleLeaderboardUpdate);
      socket.off('friend_activity', handleFriendActivity);
      socket.off('live_stats', handleLiveStats);
    };
  }, [socket, isConnected, user]);

  // Show subscription management
  const subscribeToShow = (showId: string) => {
    if (!socket || !isConnected) return;
    
    socket.emit('subscribe_show', { showId, userId: user?.id });
    setSubscribedShows(prev => [...new Set([...prev, showId])]);
    
    toast.success('📺 Subscribed to live updates for this show!', {
      duration: 2000
    });
  };

  const unsubscribeFromShow = (showId: string) => {
    if (!socket || !isConnected) return;
    
    socket.emit('unsubscribe_show', { showId, userId: user?.id });
    setSubscribedShows(prev => prev.filter(id => id !== showId));
  };

  // Send prediction to server
  const sendPrediction = (contestantId: string, prediction: any) => {
    if (!socket || !isConnected || !user) return;
    
    socket.emit('user_prediction', {
      userId: user.id,
      contestantId,
      prediction,
      timestamp: new Date().toISOString()
    });
  };

  // Send team update to server
  const sendTeamUpdate = (teamData: any) => {
    if (!socket || !isConnected || !user) return;
    
    socket.emit('team_update', {
      userId: user.id,
      teamData,
      timestamp: new Date().toISOString()
    });
  };

  // Clear recent events
  const clearEvents = () => {
    setRecentEvents([]);
  };

  // Manual reconnection
  const reconnect = () => {
    if (socket) {
      socket.disconnect();
      socket.connect();
    }
  };

  // Auto-subscribe to shows when user changes
  useEffect(() => {
    if (isConnected && user?.favoriteShow) {
      subscribeToShow(user.favoriteShow);
    }
  }, [isConnected, user?.favoriteShow]);

  const value: SocketContextType = {
    socket,
    isConnected,
    connectionStatus,
    liveStats,
    recentEvents,
    subscribedShows,
    subscribeToShow,
    unsubscribeFromShow,
    sendPrediction,
    sendTeamUpdate,
    clearEvents,
    reconnect,
  };

  return (
    <SocketContext.Provider value={value}>
      {children}
    </SocketContext.Provider>
  );
};

// Custom hook to use the context
export const useSocket = (): SocketContextType => {
  const context = useContext(SocketContext);
  if (context === undefined) {
    throw new Error('useSocket must be used within a SocketProvider');
  }
  return context;
};

// Helper hooks for specific functionality
export const useLiveScoring = () => {
  const { recentEvents, liveStats } = useSocket();
  
  const scoreUpdates = recentEvents.filter(event => event.type === 'score_update') as ScoreUpdate[];
  const episodeEvents = recentEvents.filter(event => event.type === 'episode_event') as EpisodeEvent[];
  
  return {
    scoreUpdates: scoreUpdates.slice(0, 10),
    episodeEvents: episodeEvents.slice(0, 5),
    liveStats
  };
};

export const usePredictionUpdates = () => {
  const { recentEvents, sendPrediction } = useSocket();
  
  const predictionUpdates = recentEvents.filter(event => event.type === 'prediction_update') as PredictionUpdate[];
  
  return {
    predictionUpdates: predictionUpdates.slice(0, 10),
    sendPrediction
  };
};

export const useLeaderboardUpdates = () => {
  const { recentEvents } = useSocket();
  
  const leaderboardUpdates = recentEvents.filter(event => event.type === 'leaderboard_update') as LeaderboardUpdate[];
  
  return {
    leaderboardUpdates: leaderboardUpdates.slice(0, 10)
  };
};

export const useFriendActivity = () => {
  const { recentEvents } = useSocket();
  
  const friendActivities = recentEvents.filter(event => event.type === 'friend_activity') as FriendActivity[];
  
  return {
    friendActivities: friendActivities.slice(0, 10)
  };
};

// Connection quality indicator
export const useConnectionQuality = () => {
  const { connectionStatus } = useSocket();
  
  const getQualityColor = () => {
    switch (connectionStatus.connectionQuality) {
      case 'excellent': return 'text-green-500';
      case 'good': return 'text-yellow-500';
      case 'poor': return 'text-orange-500';
      case 'disconnected': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };
  
  const getQualityLabel = () => {
    switch (connectionStatus.connectionQuality) {
      case 'excellent': return 'Excellent';
      case 'good': return 'Good';
      case 'poor': return 'Poor';
      case 'disconnected': return 'Disconnected';
      default: return 'Unknown';
    }
  };
  
  return {
    ...connectionStatus,
    qualityColor: getQualityColor(),
    qualityLabel: getQualityLabel()
  };
};

export default SocketContext;
