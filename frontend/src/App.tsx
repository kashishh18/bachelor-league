import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import io from 'socket.io-client';

// Components
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Leaderboard from './pages/Leaderboard';
import Predictions from './pages/Predictions';
import Analytics from './pages/Analytics';
import Profile from './pages/Profile';
import Login from './pages/Login';
import Register from './pages/Register';
import LoadingSpinner from './components/LoadingSpinner';

// Contexts
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { SocketProvider } from './contexts/SocketContext';
import { ShowProvider } from './contexts/ShowContext';

// Types
export interface Show {
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
}

export interface User {
  id: string;
  username: string;
  email: string;
  avatar?: string;
  totalPoints: number;
  currentRank: number;
  joinedAt: string;
  favoriteShow: string;
}

export interface Contestant {
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
  };
  predictions: {
    eliminationProbability: number;
    winnerProbability: number;
    nextEpisodeSafe: boolean;
    confidenceInterval: [number, number];
  };
}

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes
    },
  },
});

// Protected Route Component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

// App Layout Component
const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-rose-50 to-pink-100">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        {children}
      </main>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#ffffff',
            color: '#374151',
            border: '1px solid #e5e7eb',
            borderRadius: '0.5rem',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
          },
        }}
      />
    </div>
  );
};

// Main App Component
const App: React.FC = () => {
  const [socket, setSocket] = useState<any>(null);

  useEffect(() => {
    // Initialize socket connection
    const newSocket = io(process.env.REACT_APP_API_URL || 'http://localhost:8000', {
      transports: ['websocket', 'polling'],
      upgrade: true,
      rememberUpgrade: true,
    });

    newSocket.on('connect', () => {
      console.log('Connected to server');
    });

    newSocket.on('disconnect', () => {
      console.log('Disconnected from server');
    });

    // Real-time score updates
    newSocket.on('score_update', (data) => {
      console.log('Score update received:', data);
    });

    // Live episode events
    newSocket.on('episode_event', (data) => {
      console.log('Episode event:', data);
    });

    // Prediction updates
    newSocket.on('prediction_update', (data) => {
      console.log('Prediction update:', data);
    });

    setSocket(newSocket);

    return () => {
      newSocket.close();
    };
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <SocketProvider socket={socket}>
          <ShowProvider>
            <Router>
              <Routes>
                {/* Public Routes */}
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                
                {/* Protected Routes */}
                <Route
                  path="/"
                  element={
                    <ProtectedRoute>
                      <AppLayout>
                        <Dashboard />
                      </AppLayout>
                    </ProtectedRoute>
                  }
                />
                
                <Route
                  path="/leaderboard"
                  element={
                    <ProtectedRoute>
                      <AppLayout>
                        <Leaderboard />
                      </AppLayout>
                    </ProtectedRoute>
                  }
                />
                
                <Route
                  path="/predictions"
                  element={
                    <ProtectedRoute>
                      <AppLayout>
                        <Predictions />
                      </AppLayout>
                    </ProtectedRoute>
                  }
                />
                
                <Route
                  path="/analytics"
                  element={
                    <ProtectedRoute>
                      <AppLayout>
                        <Analytics />
                      </AppLayout>
                    </ProtectedRoute>
                  }
                />
                
                <Route
                  path="/profile"
                  element={
                    <ProtectedRoute>
                      <AppLayout>
                        <Profile />
                      </AppLayout>
                    </ProtectedRoute>
                  }
                />
                
                {/* Catch all route */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Router>
          </ShowProvider>
        </SocketProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
};

export default App;
