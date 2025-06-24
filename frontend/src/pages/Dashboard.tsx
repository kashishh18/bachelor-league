import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  Trophy, 
  Users, 
  TrendingUp, 
  Calendar, 
  Star, 
  Heart, 
  Clock,
  Award,
  Target,
  Zap
} from 'lucide-react';
import toast from 'react-hot-toast';

// Contexts
import { useShow } from '../contexts/ShowContext';
import { useAuth } from '../contexts/AuthContext';
import { useSocket } from '../contexts/SocketContext';

// Components
import ContestantCard from '../components/ContestantCard';
import ShowSelector from '../components/ShowSelector';
import LiveScoreboard from '../components/LiveScoreboard';
import EpisodeCountdown from '../components/EpisodeCountdown';
import PredictionAlert from '../components/PredictionAlert';
import QuickStats from '../components/QuickStats';

// Types
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

interface UserTeam {
  id: string;
  contestants: string[];
  totalPoints: number;
  weeklyPoints: number;
  rank: number;
  leagueName: string;
}

interface LeagueStats {
  totalUsers: number;
  userRank: number;
  averageScore: number;
  topScore: number;
  weeklyLeader: string;
}

// API Functions
const fetchContestants = async (showId: string): Promise<Contestant[]> => {
  const response = await fetch(`${process.env.REACT_APP_API_URL}/api/shows/${showId}/contestants`);
  if (!response.ok) throw new Error('Failed to fetch contestants');
  return response.json();
};

const fetchUserTeam = async (userId: string, showId: string): Promise<UserTeam> => {
  const response = await fetch(`${process.env.REACT_APP_API_URL}/api/users/${userId}/teams/${showId}`);
  if (!response.ok) throw new Error('Failed to fetch user team');
  return response.json();
};

const fetchLeagueStats = async (showId: string): Promise<LeagueStats> => {
  const response = await fetch(`${process.env.REACT_APP_API_URL}/api/shows/${showId}/league-stats`);
  if (!response.ok) throw new Error('Failed to fetch league stats');
  return response.json();
};

const Dashboard: React.FC = () => {
  const { currentShow, activeShows, loading: showLoading } = useShow();
  const { user } = useAuth();
  const { socket } = useSocket();
  
  const [selectedTab, setSelectedTab] = useState<'all' | 'team' | 'predictions'>('all');
  const [sortBy, setSortBy] = useState<'points' | 'predictions' | 'popularity'>('points');
  const [liveUpdates, setLiveUpdates] = useState<any[]>([]);

  // Queries
  const { data: contestants = [], isLoading: contestantsLoading, refetch: refetchContestants } = useQuery({
    queryKey: ['contestants', currentShow?.id],
    queryFn: () => fetchContestants(currentShow!.id),
    enabled: !!currentShow,
    staleTime: 30 * 1000, // 30 seconds for live data
  });

  const { data: userTeam, isLoading: teamLoading } = useQuery({
    queryKey: ['userTeam', user?.id, currentShow?.id],
    queryFn: () => fetchUserTeam(user!.id, currentShow!.id),
    enabled: !!user && !!currentShow,
  });

  const { data: leagueStats, isLoading: statsLoading } = useQuery({
    queryKey: ['leagueStats', currentShow?.id],
    queryFn: () => fetchLeagueStats(currentShow!.id),
    enabled: !!currentShow,
  });

  // Socket event handlers
  useEffect(() => {
    if (!socket) return;

    const handleScoreUpdate = (data: any) => {
      setLiveUpdates(prev => [data, ...prev.slice(0, 4)]); // Keep last 5 updates
      toast.success(`🌹 ${data.contestantName} earned ${data.points} points!`);
      refetchContestants();
    };

    const handleEpisodeEvent = (data: any) => {
      toast.success(`📺 ${data.event}: ${data.description}`);
      refetchContestants();
    };

    const handlePredictionUpdate = (data: any) => {
      setLiveUpdates(prev => [{
        type: 'prediction',
        message: `AI updated predictions for ${data.contestantName}`,
        timestamp: new Date()
      }, ...prev.slice(0, 4)]);
    };

    socket.on('score_update', handleScoreUpdate);
    socket.on('episode_event', handleEpisodeEvent);
    socket.on('prediction_update', handlePredictionUpdate);

    return () => {
      socket.off('score_update', handleScoreUpdate);
      socket.off('episode_event', handleEpisodeEvent);
      socket.off('prediction_update', handlePredictionUpdate);
    };
  }, [socket, refetchContestants]);

  // Filter and sort contestants
  const filteredContestants = contestants.filter(contestant => {
    if (selectedTab === 'team') {
      return contestant.fantasyStats.isOnUserTeam;
    }
    if (selectedTab === 'predictions') {
      return contestant.predictions.winnerProbability > 0.1; // Top contenders
    }
    return true;
  });

  const sortedContestants = [...filteredContestants].sort((a, b) => {
    switch (sortBy) {
      case 'points':
        return b.fantasyStats.points - a.fantasyStats.points;
      case 'predictions':
        return b.predictions.winnerProbability - a.predictions.winnerProbability;
      case 'popularity':
        return b.fantasyStats.pickPercentage - a.fantasyStats.pickPercentage;
      default:
        return 0;
    }
  });

  if (showLoading || !currentShow) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-rose-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading shows...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              Fantasy Dashboard
            </h1>
            <p className="text-gray-600 mt-1">
              Welcome back, {user?.username}! Track your picks and predictions.
            </p>
          </div>
          
          <div className="flex items-center gap-4">
            <ShowSelector />
            {currentShow && (
              <div className="flex items-center gap-2 bg-rose-50 px-4 py-2 rounded-lg">
                <Calendar className="h-4 w-4 text-rose-600" />
                <span className="text-sm font-medium text-rose-800">
                  Episode {currentShow.currentEpisode} of {currentShow.totalEpisodes}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <QuickStats 
        userTeam={userTeam} 
        leagueStats={leagueStats} 
        loading={statsLoading || teamLoading}
      />

      {/* Live Updates & Countdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <EpisodeCountdown show={currentShow} />
        <LiveScoreboard updates={liveUpdates} />
      </div>

      {/* Main Content */}
      <div className="bg-white rounded-xl shadow-lg">
        {/* Tabs */}
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6">
            {[
              { key: 'all', label: 'All Contestants', icon: Users },
              { key: 'team', label: 'My Team', icon: Star },
              { key: 'predictions', label: 'Top Contenders', icon: Target }
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setSelectedTab(key as any)}
                className={`flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm ${
                  selectedTab === key
                    ? 'border-rose-500 text-rose-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
                {key === 'team' && userTeam && (
                  <span className="bg-rose-100 text-rose-800 text-xs px-2 py-1 rounded-full">
                    {userTeam.contestants.length}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        {/* Sort Controls */}
        <div className="px-6 py-4 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">
              {selectedTab === 'all' && 'All Contestants'}
              {selectedTab === 'team' && 'Your Fantasy Team'}
              {selectedTab === 'predictions' && 'AI Top Contenders'}
            </h3>
            
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Sort by:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="bg-white border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
              >
                <option value="points">Fantasy Points</option>
                <option value="predictions">Win Probability</option>
                <option value="popularity">Pick %</option>
              </select>
            </div>
          </div>
        </div>

        {/* Contestants Grid */}
        <div className="p-6">
          {contestantsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="animate-pulse">
                  <div className="bg-gray-200 rounded-lg h-48"></div>
                </div>
              ))}
            </div>
          ) : sortedContestants.length === 0 ? (
            <div className="text-center py-12">
              <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {selectedTab === 'team' ? 'No team members yet' : 'No contestants found'}
              </h3>
              <p className="text-gray-600">
                {selectedTab === 'team' 
                  ? 'Start building your fantasy team by selecting contestants!'
                  : 'Check back later for contestant updates.'
                }
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {sortedContestants.map((contestant) => (
                <ContestantCard
                  key={contestant.id}
                  contestant={contestant}
                  showType={currentShow.type}
                  isOnUserTeam={contestant.fantasyStats.isOnUserTeam}
                  onTeamToggle={() => {
                    // Handle team toggle
                    toast.success(
                      contestant.fantasyStats.isOnUserTeam 
                        ? `Removed ${contestant.name} from your team`
                        : `Added ${contestant.name} to your team`
                    );
                    refetchContestants();
                  }}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Prediction Alerts */}
      <PredictionAlert 
        contestants={contestants.filter(c => c.predictions.trend === 'up' || c.predictions.trend === 'down')} 
      />
    </div>
  );
};

export default Dashboard;
