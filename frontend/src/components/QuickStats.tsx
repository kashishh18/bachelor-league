import React from 'react';
import { 
  Trophy, 
  Target, 
  TrendingUp, 
  TrendingDown, 
  Users, 
  Star,
  Award,
  Zap,
  Calendar,
  Crown,
  Heart,
  BarChart3,
  Medal,
  Flame,
  ArrowUp,
  ArrowDown,
  Minus
} from 'lucide-react';
import { motion } from 'framer-motion';

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

interface QuickStatsProps {
  userTeam?: UserTeam;
  leagueStats?: LeagueStats;
  loading?: boolean;
}

interface StatCard {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ElementType;
  color: string;
  bgColor: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  isHighlight?: boolean;
}

const QuickStats: React.FC<QuickStatsProps> = ({ 
  userTeam, 
  leagueStats, 
  loading = false 
}) => {
  
  // Calculate user performance metrics
  const getUserPercentile = () => {
    if (!leagueStats || !userTeam) return 0;
    return Math.round(((leagueStats.totalUsers - leagueStats.userRank + 1) / leagueStats.totalUsers) * 100);
  };

  const getPerformanceRating = () => {
    const percentile = getUserPercentile();
    if (percentile >= 90) return { label: 'Elite', color: 'text-purple-600', icon: Crown };
    if (percentile >= 75) return { label: 'Excellent', color: 'text-green-600', icon: Trophy };
    if (percentile >= 50) return { label: 'Good', color: 'text-blue-600', icon: Star };
    if (percentile >= 25) return { label: 'Average', color: 'text-yellow-600', icon: Target };
    return { label: 'Improving', color: 'text-gray-600', icon: TrendingUp };
  };

  const getWeeklyTrend = () => {
    if (!userTeam) return 'neutral';
    if (userTeam.weeklyPoints > 50) return 'up';
    if (userTeam.weeklyPoints < 10) return 'down';
    return 'neutral';
  };

  const performance = getPerformanceRating();

  // Generate stat cards
  const getStatCards = (): StatCard[] => {
    if (!userTeam || !leagueStats) return [];

    return [
      {
        title: 'Current Rank',
        value: `#${leagueStats.userRank}`,
        subtitle: `of ${leagueStats.totalUsers.toLocaleString()}`,
        icon: Trophy,
        color: 'text-yellow-600',
        bgColor: 'bg-yellow-50',
        isHighlight: leagueStats.userRank <= 3
      },
      {
        title: 'Total Points',
        value: userTeam.totalPoints.toLocaleString(),
        subtitle: `vs ${Math.round(leagueStats.averageScore)} avg`,
        icon: Target,
        color: 'text-blue-600',
        bgColor: 'bg-blue-50',
        trend: userTeam.totalPoints > leagueStats.averageScore ? 'up' : 'down',
        trendValue: `${Math.abs(userTeam.totalPoints - leagueStats.averageScore)} pts`
      },
      {
        title: 'This Week',
        value: userTeam.weeklyPoints,
        subtitle: 'points earned',
        icon: Zap,
        color: 'text-rose-600',
        bgColor: 'bg-rose-50',
        trend: getWeeklyTrend(),
        trendValue: userTeam.weeklyPoints > 0 ? `+${userTeam.weeklyPoints}` : '0'
      },
      {
        title: 'Performance',
        value: performance.label,
        subtitle: `${getUserPercentile()}th percentile`,
        icon: performance.icon,
        color: performance.color,
        bgColor: performance.color.replace('text-', 'bg-').replace('-600', '-50'),
        isHighlight: getUserPercentile() >= 75
      }
    ];
  };

  const statCards = getStatCards();

  // Loading state
  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-white rounded-xl shadow-md p-6 animate-pulse">
            <div className="flex items-center justify-between mb-4">
              <div className="w-8 h-8 bg-gray-200 rounded-lg"></div>
              <div className="w-16 h-4 bg-gray-200 rounded"></div>
            </div>
            <div className="w-20 h-8 bg-gray-200 rounded mb-2"></div>
            <div className="w-24 h-4 bg-gray-200 rounded"></div>
          </div>
        ))}
      </div>
    );
  }

  // No data state
  if (!userTeam || !leagueStats) {
    return (
      <div className="bg-white rounded-xl shadow-md p-8 text-center">
        <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          No Fantasy Team Yet
        </h3>
        <p className="text-gray-600 mb-4">
          Create your fantasy team to start tracking your performance and competing with friends!
        </p>
        <button className="bg-rose-600 text-white px-6 py-2 rounded-lg hover:bg-rose-700 transition-colors">
          Create Team
        </button>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {statCards.map((stat, index) => (
        <motion.div
          key={stat.title}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1 }}
          className={`bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition-all duration-300 ${
            stat.isHighlight ? 'ring-2 ring-yellow-400 ring-opacity-50' : ''
          }`}
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <div className={`p-2 rounded-lg ${stat.bgColor}`}>
              <stat.icon className={`h-5 w-5 ${stat.color}`} />
            </div>
            
            {stat.isHighlight && (
              <div className="flex items-center gap-1">
                <Medal className="h-4 w-4 text-yellow-500" />
                <span className="text-xs font-medium text-yellow-600">TOP</span>
              </div>
            )}
          </div>

          {/* Main Value */}
          <div className="mb-2">
            <div className="text-2xl font-bold text-gray-900 leading-tight">
              {stat.value}
            </div>
            {stat.subtitle && (
              <div className="text-sm text-gray-600">
                {stat.subtitle}
              </div>
            )}
          </div>

          {/* Trend Indicator */}
          {stat.trend && stat.trendValue && (
            <div className="flex items-center gap-1">
              {stat.trend === 'up' && (
                <>
                  <ArrowUp className="h-3 w-3 text-green-500" />
                  <span className="text-xs text-green-600 font-medium">
                    {stat.trendValue}
                  </span>
                </>
              )}
              {stat.trend === 'down' && (
                <>
                  <ArrowDown className="h-3 w-3 text-red-500" />
                  <span className="text-xs text-red-600 font-medium">
                    {stat.trendValue}
                  </span>
                </>
              )}
              {stat.trend === 'neutral' && (
                <>
                  <Minus className="h-3 w-3 text-gray-400" />
                  <span className="text-xs text-gray-600 font-medium">
                    Stable
                  </span>
                </>
              )}
            </div>
          )}

          {/* Title */}
          <div className="text-xs font-medium text-gray-700 uppercase tracking-wider mt-2">
            {stat.title}
          </div>
        </motion.div>
      ))}

      {/* Additional Insights Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="sm:col-span-2 lg:col-span-4 bg-gradient-to-r from-rose-50 to-pink-50 rounded-xl shadow-md p-6"
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-white rounded-lg shadow-sm">
              <BarChart3 className="h-6 w-6 text-rose-600" />
            </div>
            
            <div>
              <h4 className="font-semibold text-gray-900 mb-1">
                League Performance Insights
              </h4>
              <div className="text-sm text-gray-600 space-y-1">
                <div className="flex items-center gap-4">
                  <span>
                    <strong>{leagueStats.weeklyLeader}</strong> leads this week with{' '}
                    <strong>{leagueStats.topScore}</strong> points
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <span>
                    You're <strong>{getUserPercentile()}%</strong> ahead of other players
                  </span>
                  {getUserPercentile() >= 90 && (
                    <div className="flex items-center gap-1">
                      <Flame className="h-4 w-4 text-orange-500" />
                      <span className="text-xs font-medium text-orange-600">ON FIRE</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-2">
            <button className="text-sm bg-white text-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-50 transition-colors border border-gray-200">
              View Details
            </button>
            <button className="text-sm bg-rose-600 text-white px-3 py-1.5 rounded-lg hover:bg-rose-700 transition-colors">
              Optimize Team
            </button>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-4">
          <div className="flex justify-between text-xs text-gray-600 mb-1">
            <span>Progress to Top 10</span>
            <span>{Math.min(getUserPercentile(), 90)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${Math.min(getUserPercentile(), 90)}%` }}
              transition={{ duration: 1, delay: 0.5 }}
              className="bg-gradient-to-r from-rose-500 to-pink-500 h-2 rounded-full"
            />
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default QuickStats;
