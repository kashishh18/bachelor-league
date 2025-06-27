import React, { createContext, useContext, useState, useEffect } from 'react';

interface Show {
  id: string;
  title: string;
  season: number;
  type: string;
  status: string;
  currentEpisode?: number;
}

interface ShowContextType {
  currentShow: Show | null;
  shows: Show[];
  activeShows: Show[];
  completedShows: Show[];
  upcomingShows: Show[];
  setCurrentShow: (show: Show) => void;
  loading: boolean;
}

const ShowContext = createContext<ShowContextType | undefined>(undefined);

export const ShowProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentShow, setCurrentShow] = useState<Show | null>(null);
  const [shows, setShows] = useState<Show[]>([]);
  const [loading, setLoading] = useState(false);

  // Filter shows by status
  const activeShows = shows.filter(show => show.status === 'active');
  const completedShows = shows.filter(show => show.status === 'completed');
  const upcomingShows = shows.filter(show => show.status === 'upcoming');

  return (
    <ShowContext.Provider value={{ 
      currentShow, 
      shows, 
      activeShows,
      completedShows,
      upcomingShows,
      setCurrentShow, 
      loading 
    }}>
      {children}
    </ShowContext.Provider>
  );
};

export const useShow = () => {
  const context = useContext(ShowContext);
  if (context === undefined) {
    throw new Error('useShow must be used within a ShowProvider');
  }
  return context;
};
