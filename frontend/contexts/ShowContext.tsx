import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import toast from 'react-hot-toast';

// Types
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

interface ShowContextType {
  shows: Show[];
  currentShow: Show | null;
  setCurrentShow: (show: Show) => void;
  activeShows: Show[];
  completedShows: Show[];
  upcomingShows: Show[];
  loading: boolean;
  error: string | null;
  refreshShows: () => void;
  getShowById: (id: string) => Show | undefined;
  getShowsByType: (type: Show['type']) => Show[];
}

// Create Context
const ShowContext = createContext<ShowContextType | undefined>(undefined);

// Show data with all Bachelor franchise shows
const INITIAL_SHOWS: Show[] = [
  // Current/Recent Seasons
  {
    id: 'bachelor-28',
    name: 'The Bachelor',
    type: 'bachelor',
    season: 28,
    isActive: true,
    startDate: '2024-01-22',
    lead: 'Joey Graziadei',
    network: 'ABC',
    logoUrl: '/images/bachelor-logo.png',
    currentEpisode: 8,
    totalEpisodes: 12,
    description: 'Joey Graziadei searches for love among 32 incredible women',
    location: 'Malta',
    premiereDate: '2024-01-22',
    status: 'airing'
  },
  {
    id: 'bachelorette-21',
    name: 'The Bachelorette',
    type: 'bachelorette',
    season: 21,
    isActive: false,
    startDate: '2024-07-08',
    endDate: '2024-09-03',
    lead: 'Jenn Tran',
    network: 'ABC',
    logoUrl: '/images/bachelorette-logo.png',
    currentEpisode: 12,
    totalEpisodes: 12,
    description: 'Jenn Tran\'s journey to find her perfect match',
    location: 'Various Locations',
    premiereDate: '2024-07-08',
    finaleDate: '2024-09-03',
    status: 'completed'
  },
  {
    id: 'bip-10',
    name: 'Bachelor in Paradise',
    type: 'bachelor-in-paradise',
    season: 10,
    isActive: false,
    startDate: '2024-09-26',
    endDate: '2024-11-07',
    lead: 'Various Singles',
    network: 'ABC',
    logoUrl: '/images/bip-logo.png',
    currentEpisode: 12,
    totalEpisodes: 12,
    description: 'Bachelor Nation favorites search for love in paradise',
    location: 'Playa Escondida, Mexico',
    premiereDate: '2024-09-26',
    finaleDate: '2024-11-07',
    status: 'completed'
  },
  {
    id: 'golden-bachelor-2',
    name: 'The Golden Bachelor',
    type: 'golden-bachelor',
    season: 2,
    isActive: true,
    startDate: '2025-01-29',
    lead: 'Charles Ling',
    network: 'ABC',
    logoUrl: '/images/golden-bachelor-logo.png',
    currentEpisode: 3,
    totalEpisodes: 8,
    description: 'Charles Ling, 66, searches for a second chance at love',
    location: 'Various Locations',
    premiereDate: '2025-01-29',
    status: 'airing'
  },
  {
    id: 'golden-bachelorette-1',
    name: 'The Golden Bachelorette',
    type: 'golden-bachelorette',
    season: 1,
    isActive: false,
    startDate: '2024-09-18',
    endDate: '2024-11-13',
    lead: 'Joan Vassos',
    network: 'ABC',
    logoUrl: '/images/golden-bachelorette-logo.png',
    currentEpisode: 8,
    totalEpisodes: 8,
    description: 'Joan Vassos\' journey to find love again at 61',
    location: 'Various Locations',
    premiereDate: '2024-09-18',
    finaleDate: '2024-11-13',
    status: 'completed'
  },
  // Upcoming Shows
  {
    id: 'bachelorette-22',
    name: 'The Bachelorette',
    type: 'bachelorette',
    season: 22,
    isActive: false,
    startDate: '2025-07-07',
    lead: 'TBA',
    network: 'ABC',
    logoUrl: '/images/bachelorette-logo.png',
    currentEpisode: 0,
    totalEpisodes: 12,
    description: 'A new Bachelorette\'s journey begins this summer',
    location: 'TBA',
    premiereDate: '2025-07-07',
    status: 'upcoming'
  }
];

// API functions
const fetchShows = async (): Promise<Show[]> => {
  try {
    const response = await fetch(`${process.env.REACT_APP_API_URL}/api/shows`);
    if (!response.ok) {
      throw new Error('Failed to fetch shows');
    }
    const data = await response.json();
    return data.shows || INITIAL_SHOWS;
  } catch (error) {
    console.warn('Using fallback show data:', error);
    return INITIAL_SHOWS;
  }
};

// Provider Component
export const ShowProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [currentShow, setCurrentShowState] = useState<Show | null>(null);

  // Fetch shows with React Query
  const {
    data: shows = [],
    isLoading: loading,
    error,
    refetch: refreshShows
  } = useQuery({
    queryKey: ['shows'],
    queryFn: fetchShows,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
  });

  // Set initial current show to the first active show
  useEffect(() => {
    if (shows.length > 0 && !currentShow) {
      const activeShow = shows.find(show => show.isActive) || shows[0];
      setCurrentShowState(activeShow);
    }
  }, [shows, currentShow]);

  // Computed values
  const activeShows = shows.filter(show => show.status === 'airing');
  const completedShows = shows.filter(show => show.status === 'completed');
  const upcomingShows = shows.filter(show => show.status === 'upcoming');

  // Helper functions
  const setCurrentShow = (show: Show) => {
    setCurrentShowState(show);
    localStorage.setItem('currentShowId', show.id);
    toast.success(`Switched to ${show.name} Season ${show.season}`);
  };

  const getShowById = (id: string): Show | undefined => {
    return shows.find(show => show.id === id);
  };

  const getShowsByType = (type: Show['type']): Show[] => {
    return shows.filter(show => show.type === type);
  };

  // Load saved current show from localStorage
  useEffect(() => {
    const savedShowId = localStorage.getItem('currentShowId');
    if (savedShowId && shows.length > 0) {
      const savedShow = getShowById(savedShowId);
      if (savedShow) {
        setCurrentShowState(savedShow);
      }
    }
  }, [shows]);

  const value: ShowContextType = {
    shows,
    currentShow,
    setCurrentShow,
    activeShows,
    completedShows,
    upcomingShows,
    loading,
    error: error?.message || null,
    refreshShows,
    getShowById,
    getShowsByType,
  };

  return (
    <ShowContext.Provider value={value}>
      {children}
    </ShowContext.Provider>
  );
};

// Custom hook to use the context
export const useShow = (): ShowContextType => {
  const context = useContext(ShowContext);
  if (context === undefined) {
    throw new Error('useShow must be used within a ShowProvider');
  }
  return context;
};

// Helper hook for show statistics
export const useShowStats = () => {
  const { shows } = useShow();

  const stats = {
    totalShows: shows.length,
    activeShows: shows.filter(s => s.status === 'airing').length,
    completedShows: shows.filter(s => s.status === 'completed').length,
    upcomingShows: shows.filter(s => s.status === 'upcoming').length,
    showsByType: {
      bachelor: shows.filter(s => s.type === 'bachelor').length,
      bachelorette: shows.filter(s => s.type === 'bachelorette').length,
      bachelorInParadise: shows.filter(s => s.type === 'bachelor-in-paradise').length,
      goldenBachelor: shows.filter(s => s.type === 'golden-bachelor').length,
      goldenBachelorette: shows.filter(s => s.type === 'golden-bachelorette').length,
    }
  };

  return stats;
};

export default ShowContext;
