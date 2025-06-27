import React, { createContext, useContext, useState, useEffect } from 'react';

interface Show {
  id: string;
  title: string;
  season: number;
  type: string;
  status: string;
}

interface ShowContextType {
  currentShow: Show | null;
  shows: Show[];
  setCurrentShow: (show: Show) => void;
  loading: boolean;
}

const ShowContext = createContext<ShowContextType | undefined>(undefined);

export const ShowProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentShow, setCurrentShow] = useState<Show | null>(null);
  const [shows, setShows] = useState<Show[]>([]);
  const [loading, setLoading] = useState(false);

  return (
    <ShowContext.Provider value={{ currentShow, shows, setCurrentShow, loading }}>
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
