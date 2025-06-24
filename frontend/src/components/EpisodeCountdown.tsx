import React, { useState, useEffect } from 'react';
import { 
  Clock, 
  Calendar, 
  Tv, 
  Bell, 
  BellRing,
  Users, 
  Heart, 
  Target,
  CheckCircle,
  AlertTriangle,
  Play,
  Star,
  MapPin,
  Timer
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useShow } from '../contexts/ShowContext';
import { useAuth } from '../contexts/AuthContext';

interface Show {
  id: string;
  name: string;
  type: 'bachelor' | 'bachelorette' | 'bachelor-in-paradise' | 'golden-bachelor' | 'golden-bachelorette';
  season: number;
  isActive: boolean;
  startDate: string;
  endDate?: string;
  lead: string;
  network: string;
  logoUrl: string;
  currentEpisode: number;
  totalEpisodes: number;
  description: string;
  location: string;
  premiereDate: string;
  finaleDate?: string;
  status: 'upcoming' | 'airing' | 'completed';
}

interface EpisodeCountdownProps {
  show: Show;
  compact?: boolean;
}

interface TimeRemaining {
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
  totalSeconds: number;
}

interface UpcomingEpisode {
  number: number;
  title: string;
  description: string;
  airDate: string;
  duration: number;
  type: 'regular' | 'special' | 'finale' | 'reunion';
  location: string;
  previewUrl?: string;
  contestantsRemaining: number;
}

const EpisodeCountdown: React.FC<EpisodeCountdownProps> = ({ show, compact = false }) => {
  const { user } = useAuth();
  const [timeRemaining, setTimeRemaining] = useState<TimeRemaining | null>(null);
  const [isLive, setIsLive] = useState(false);
  const [notificationsEnabled, setNotificationsEnabled] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  // Mock upcoming episode data (in real app, this would come from API)
  const upcomingEpisode: UpcomingEpisode = {
    number: show.currentEpisode + 1,
    title: getEpisodeTitle(show),
    description: getEpisodeDescription(show),
    airDate: getNextEpisodeDate(show),
    duration: show.type === 'bachelor-in-paradise' ? 120 : 90,
    type: getEpisodeType(show),
    location: show.location,
    contestantsRemaining: Math.max(12 - show.currentEpisode, 2),
    previewUrl: '/api/episodes/preview.mp4'
  };

  // Calculate time remaining until next episode
  useEffect(() => {
    const calculateTimeRemaining = () => {
      const now = new Date().getTime();
      const episodeTime = new Date(upcomingEpisode.airDate).getTime();
      const difference = episodeTime - now;

      if (difference <= 0) {
        setIsLive(true);
        setTimeRemaining(null);
        return;
      }

      const days = Math.floor(difference / (1000 * 60 * 60 * 24));
      const hours = Math.floor((difference % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((difference % (1000 * 60)) / 1000);

      setTimeRemaining({
        days,
        hours,
        minutes,
        seconds,
        totalSeconds: Math.floor(difference / 1000)
      });
      setIsLive(false);
    };

    calculateTimeRemaining();
    const interval = setInterval(calculateTimeRemaining, 1000);

    return () => clearInterval(interval);
  }, [upcomingEpisode.airDate]);

  // Check notification permissions
  useEffect(() => {
    if ('Notification' in window) {
      setNotificationsEnabled(Notification.permission === 'granted');
    }
  }, []);

  // Helper functions
  function getEpisodeTitle(show: Show): string {
    const episodeNumber = show.currentEpisode + 1;
    
    switch (show.type) {
      case 'bachelor':
      case 'bachelorette':
        if (episodeNumber === show.totalEpisodes) return 'The Final Rose';
        if (episodeNumber === show.totalEpisodes - 1) return 'Fantasy Suites';
        if (episodeNumber === show.totalEpisodes - 2) return 'Hometown Dates';
        return `Week ${episodeNumber}`;
      
      case 'bachelor-in-paradise':
        if (episodeNumber === show.totalEpisodes) return 'Paradise Finale';
        return `Paradise - Week ${Math.ceil(episodeNumber / 2)}`;
      
      case 'golden-bachelor':
      case 'golden-bachelorette':
        if (episodeNumber === show.totalEpisodes) return 'The Golden Rose';
        return `Golden Week ${episodeNumber}`;
      
      default:
        return `Episode ${episodeNumber}`;
    }
  }

  function getEpisodeDescription(show: Show): string {
    const episodeNumber = show.currentEpisode + 1;
    
    if (episodeNumber === show.totalEpisodes) {
      return `${show.lead} makes their final decision in an emotional finale!`;
    }
    
    switch (show.type) {
      case 'bachelor-in-paradise':
        return 'New arrivals shake up existing relationships as couples face tough decisions.';
      case 'golden-bachelor':
      case 'golden-bachelorette':
        return 'Meaningful connections deepen as our lead explores second chances at love.';
      default:
        return 'Dramatic dates and unexpected twists await as the journey for love continues.';
    }
  }

  function getNextEpisodeDate(show: Show): string {
    // Mock calculation - in real app, this would come from show schedule API
    const baseDate = new Date();
    
    // Most Bachelor shows air on Monday nights at 8 PM ET
    let nextMonday = new Date(baseDate);
    nextMonday.setDate(baseDate.getDate() + (1 + 7 - baseDate.getDay()) % 7);
    nextMonday.setHours(20, 0, 0, 0); // 8 PM ET
    
    // Paradise airs Tuesday nights
    if (show.type === 'bachelor-in-paradise') {
      nextMonday.setDate(nextMonday.getDate() + 1);
    }
    
    return nextMonday.toISOString();
  }

  function getEpisodeType(show: Show): UpcomingEpisode['type'] {
    const episodeNumber = show.currentEpisode + 1;
    
    if (episodeNumber === show.totalEpisodes) return 'finale';
    if (episodeNumber === show.totalEpisodes + 1) return 'reunion';
    if (episodeNumber === show.totalEpisodes - 1) return 'special';
    return 'regular';
  }

  // Request notification permission
  const requestNotifications = async () => {
    if ('Notification' in window) {
      const permission = await Notification.requestPermission();
      setNotificationsEnabled(permission === 'granted');
    }
  };

  // Get show type styling
  const getShowStyling = () => {
    switch (show.type) {
      case 'bachelor':
        return {
          gradient: 'from-blue-500 to-blue-600',
          accent: 'text-blue-600',
          bg: 'bg-blue-50',
          icon: '👑'
        };
      case 'bachelorette':
        return {
          gradient: 'from-pink-500 to-rose-600',
          accent: 'text-pink-600',
          bg: 'bg-pink-50',
          icon: '🌹'
        };
      case 'bachelor-in-paradise':
        return {
          gradient: 'from-green-500 to-teal-600',
          accent: 'text-green-600',
          bg: 'bg-green-50',
          icon: '🏝️'
        };
      case 'golden-bachelor':
        return {
          gradient: 'from-yellow-500 to-orange-600',
          accent: 'text-yellow-600',
          bg: 'bg-yellow-50',
          icon: '⭐'
        };
      case 'golden-bachelorette':
        return {
          gradient: 'from-rose-500 to-pink-600',
          accent: 'text-rose-600',
          bg: 'bg-rose-50',
          icon: '💫'
        };
      default:
        return {
          gradient: 'from-gray-500 to-gray-600',
          accent: 'text-gray-600',
          bg: 'bg-gray-50',
          icon: '📺'
        };
    }
  };

  const styling = getShowStyling();

  if (compact) {
    return (
      <div className={`${styling.bg} rounded-lg p-4`}>
        <div className="flex items-center gap-3">
          <div className="text-2xl">{styling.icon}</div>
          <div className="flex-1">
            <div className="font-semibold text-gray-900">
              {upcomingEpisode.title}
            </div>
            {timeRemaining ? (
              <div className="text-sm text-gray-600">
                {timeRemaining.days > 0 && `${timeRemaining.days}d `}
                {timeRemaining.hours}h {timeRemaining.minutes}m
              </div>
            ) : isLive ? (
              <div className="text-sm font-medium text-red-600 flex items-center gap-1">
                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                LIVE NOW
              </div>
            ) : (
              <div className="text-sm text-gray-600">Episode ended</div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden">
      {/* Header */}
      <div className={`bg-gradient-to-r ${styling.gradient} px-6 py-4 text-white`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="text-3xl">{styling.icon}</div>
            <div>
              <h3 className="text-lg font-semibold">Next Episode</h3>
              <p className="text-white/80 text-sm">
                {show.name} Season {show.season}
              </p>
            </div>
          </div>
          
          {!isLive && (
            <button
              onClick={requestNotifications}
              className={`p-2 rounded-lg bg-white/20 hover:bg-white/30 transition-colors ${
                notificationsEnabled ? 'text-yellow-300' : 'text-white/70'
              }`}
              title="Enable notifications"
            >
              {notificationsEnabled ? <BellRing className="h-5 w-5" /> : <Bell className="h-5 w-5" />}
            </button>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="p-6">
        {isLive ? (
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="text-center py-8"
          >
            <div className="inline-flex items-center gap-2 bg-red-100 text-red-800 px-4 py-2 rounded-full text-lg font-semibold mb-4">
              <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
              LIVE NOW
            </div>
            <h4 className="text-xl font-bold text-gray-900 mb-2">
              {upcomingEpisode.title}
            </h4>
            <p className="text-gray-600 mb-4">
              The episode is airing now! Fantasy points are being awarded in real-time.
            </p>
            <button className="inline-flex items-center gap-2 bg-rose-600 text-white px-4 py-2 rounded-lg hover:bg-rose-700 transition-colors">
              <Play className="h-4 w-4" />
              Watch Live Updates
            </button>
          </motion.div>
        ) : timeRemaining ? (
          <>
            {/* Countdown Timer */}
            <div className="text-center mb-6">
              <h4 className="text-xl font-bold text-gray-900 mb-2">
                {upcomingEpisode.title}
              </h4>
              <p className="text-gray-600 mb-4">
                {upcomingEpisode.description}
              </p>

              <div className="grid grid-cols-4 gap-4 mb-4">
                {[
                  { label: 'Days', value: timeRemaining.days },
                  { label: 'Hours', value: timeRemaining.hours },
                  { label: 'Minutes', value: timeRemaining.minutes },
                  { label: 'Seconds', value: timeRemaining.seconds }
                ].map(({ label, value }) => (
                  <div key={label} className="text-center">
                    <motion.div
                      key={value}
                      initial={{ scale: 1.1 }}
                      animate={{ scale: 1 }}
                      className={`text-2xl font-bold ${styling.accent} bg-gray-50 rounded-lg py-3`}
                    >
                      {value.toString().padStart(2, '0')}
                    </motion.div>
                    <div className="text-sm text-gray-600 mt-1">{label}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Episode Details */}
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-gray-400" />
                  <span className="text-gray-600">
                    {new Date(upcomingEpisode.airDate).toLocaleDateString('en-US', {
                      weekday: 'long',
                      month: 'short',
                      day: 'numeric'
                    })}
                  </span>
                </div>
                
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-gray-400" />
                  <span className="text-gray-600">
                    {new Date(upcomingEpisode.airDate).toLocaleTimeString('en-US', {
                      hour: 'numeric',
                      minute: '2-digit',
                      timeZoneName: 'short'
                    })}
                  </span>
                </div>
                
                <div className="flex items-center gap-2">
                  <Timer className="h-4 w-4 text-gray-400" />
                  <span className="text-gray-600">
                    {upcomingEpisode.duration} minutes
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-gray-400" />
                  <span className="text-gray-600">{upcomingEpisode.location}</span>
                </div>
                
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-gray-400" />
                  <span className="text-gray-600">
                    {upcomingEpisode.contestantsRemaining} contestants remaining
                  </span>
                </div>
              </div>
            </div>

            {/* Preparation Checklist */}
            <div className="mt-6 p-4 bg-gray-50 rounded-lg">
              <h5 className="font-semibold text-gray-900 mb-3">Episode Prep Checklist</h5>
              <div className="space-y-2 text-sm">
                {[
                  { task: 'Set your fantasy lineup', completed: true },
                  { task: 'Make elimination predictions', completed: false },
                  { task: 'Join friends for watch party', completed: false },
                  { task: 'Enable live notifications', completed: notificationsEnabled }
                ].map(({ task, completed }, index) => (
                  <div key={index} className="flex items-center gap-2">
                    {completed ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : (
                      <div className="h-4 w-4 border-2 border-gray-300 rounded"></div>
                    )}
                    <span className={completed ? 'text-gray-600 line-through' : 'text-gray-900'}>
                      {task}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="mt-6 flex gap-3">
              <button className="flex-1 bg-rose-600 text-white py-2 px-4 rounded-lg hover:bg-rose-700 transition-colors">
                Set Lineup
              </button>
              <button
                onClick={() => setShowPreview(!showPreview)}
                className="flex-1 border border-gray-300 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-50 transition-colors"
              >
                {showPreview ? 'Hide' : 'Show'} Preview
              </button>
            </div>

            {/* Episode Preview */}
            <AnimatePresence>
              {showPreview && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="mt-4 p-4 bg-gray-900 rounded-lg text-white"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Tv className="h-4 w-4" />
                    <span className="text-sm font-medium">Episode Preview</span>
                  </div>
                  <p className="text-sm text-gray-300">
                    Drama unfolds as {show.lead} makes difficult decisions. 
                    Who will receive roses, and who will go home heartbroken?
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </>
        ) : (
          <div className="text-center py-8">
            <AlertTriangle className="h-8 w-8 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">
              No upcoming episodes scheduled
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default EpisodeCountdown;
