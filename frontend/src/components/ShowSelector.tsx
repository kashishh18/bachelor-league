import React, { useState, useRef, useEffect } from 'react';
import { 
  ChevronDown, 
  Calendar, 
  Users, 
  Crown, 
  Heart, 
  Palmtree,
  Star,
  Clock,
  CheckCircle,
  AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useShow } from '../contexts/ShowContext';

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

const ShowSelector: React.FC = () => {
  const { 
    shows, 
    currentShow, 
    setCurrentShow, 
    activeShows, 
    completedShows, 
    upcomingShows,
    loading 
  } = useShow();
  
  const [isOpen, setIsOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<'active' | 'completed' | 'upcoming'>('active');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Get show icon based on type
  const getShowIcon = (type: Show['type']) => {
    switch (type) {
      case 'bachelor':
        return <Crown className="h-4 w-4 text-blue-600" />;
      case 'bachelorette':
        return <Heart className="h-4 w-4 text-pink-600" />;
      case 'bachelor-in-paradise':
        return <Palmtree className="h-4 w-4 text-green-600" />;
      case 'golden-bachelor':
        return <Star className="h-4 w-4 text-yellow-600" />;
      case 'golden-bachelorette':
        return <Star className="h-4 w-4 text-rose-600" />;
      default:
        return <Users className="h-4 w-4 text-gray-600" />;
    }
  };

  // Get show type label
  const getShowTypeLabel = (type: Show['type']) => {
    switch (type) {
      case 'bachelor':
        return 'The Bachelor';
      case 'bachelorette':
        return 'The Bachelorette';
      case 'bachelor-in-paradise':
        return 'Bachelor in Paradise';
      case 'golden-bachelor':
        return 'The Golden Bachelor';
      case 'golden-bachelorette':
        return 'The Golden Bachelorette';
      default:
        return 'Unknown Show';
    }
  };

  // Get status badge
  const getStatusBadge = (show: Show) => {
    switch (show.status) {
      case 'airing':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            LIVE
          </span>
        );
      case 'upcoming':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
            <Clock className="h-3 w-3" />
            Coming Soon
          </span>
        );
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded-full">
            <CheckCircle className="h-3 w-3" />
            Finished
          </span>
        );
    }
  };

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  // Get shows by category
  const getShowsByCategory = () => {
    switch (selectedCategory) {
      case 'active':
        return activeShows;
      case 'completed':
        return completedShows;
      case 'upcoming':
        return upcomingShows;
      default:
        return [];
    }
  };

  const categoryShows = getShowsByCategory();

  if (loading || !currentShow) {
    return (
      <div className="animate-pulse">
        <div className="bg-gray-200 rounded-lg h-10 w-48"></div>
      </div>
    );
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Current Show Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-3 bg-white border border-gray-300 rounded-lg px-4 py-2 hover:bg-gray-50 transition-colors min-w-[280px] text-left"
      >
        <div className="flex items-center gap-2">
          {getShowIcon(currentShow.type)}
          <div className="flex-1">
            <div className="font-medium text-gray-900">
              {getShowTypeLabel(currentShow.type)}
            </div>
            <div className="text-sm text-gray-600">
              Season {currentShow.season} • {currentShow.lead}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {getStatusBadge(currentShow)}
          <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="absolute top-full left-0 right-0 mt-2 bg-white border border-gray-200 rounded-xl shadow-lg z-50 max-h-96 overflow-hidden"
          >
            {/* Category Tabs */}
            <div className="border-b border-gray-100">
              <div className="flex">
                {[
                  { key: 'active', label: 'Active', count: activeShows.length },
                  { key: 'completed', label: 'Completed', count: completedShows.length },
                  { key: 'upcoming', label: 'Upcoming', count: upcomingShows.length }
                ].map(({ key, label, count }) => (
                  <button
                    key={key}
                    onClick={() => setSelectedCategory(key as any)}
                    className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                      selectedCategory === key
                        ? 'text-rose-600 bg-rose-50 border-b-2 border-rose-600'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                  >
                    {label}
                    {count > 0 && (
                      <span className={`ml-2 px-2 py-1 text-xs rounded-full ${
                        selectedCategory === key
                          ? 'bg-rose-100 text-rose-800'
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        {count}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Show List */}
            <div className="max-h-64 overflow-y-auto">
              {categoryShows.length === 0 ? (
                <div className="p-4 text-center text-gray-500">
                  <AlertCircle className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                  <div className="text-sm">
                    No {selectedCategory} shows available
                  </div>
                </div>
              ) : (
                <div className="py-2">
                  {categoryShows.map((show) => (
                    <button
                      key={show.id}
                      onClick={() => {
                        setCurrentShow(show);
                        setIsOpen(false);
                      }}
                      className={`w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors ${
                        currentShow.id === show.id ? 'bg-rose-50' : ''
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        {getShowIcon(show.type)}
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-gray-900 truncate">
                              {getShowTypeLabel(show.type)}
                            </span>
                            <span className="text-sm text-gray-600">
                              Season {show.season}
                            </span>
                          </div>
                          
                          <div className="text-sm text-gray-600 truncate">
                            {show.lead}
                          </div>
                          
                          <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                            <span className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              {formatDate(show.premiereDate)}
                            </span>
                            
                            {show.status === 'airing' && (
                              <span>
                                Episode {show.currentEpisode}/{show.totalEpisodes}
                              </span>
                            )}
                            
                            {show.location && (
                              <span className="truncate">
                                📍 {show.location}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="flex flex-col items-end gap-1">
                          {getStatusBadge(show)}
                          
                          {currentShow.id === show.id && (
                            <CheckCircle className="h-4 w-4 text-rose-600" />
                          )}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="border-t border-gray-100 px-4 py-3 bg-gray-50">
              <div className="text-xs text-gray-600 text-center">
                Switch between shows to track different fantasy leagues
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ShowSelector;
