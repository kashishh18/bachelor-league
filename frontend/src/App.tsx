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
import Home from './components/Home';

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

// Beautiful App Layout Component
const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-rose-50 via-pink-50 to-purple-50">
      <Navbar />
      <main className="relative">
        {/* Background decoration */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-40 -right-40 w-80 h-80 bg-gradient-to-br from-pink-200 to-purple-200 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-pulse"></div>
          <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-gradient-to-br from-rose-200 to-pink-200 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-pulse"></div>
        </div>
        
        <div className="relative z-10 container mx-auto px-4 py-8">
          {children}
        </div>
      </main>
      
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: 'rgba(255, 255, 255, 0.95)',
            color: '#374151',
            border: '1px solid rgba(236, 72, 153, 0.2)',
            borderRadius: '12px',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
            backdropFilter: 'blur(10px)',
          },
          success: {
            iconTheme: {
              primary: '#ec4899',
              secondary: '#ffffff',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#ffffff',
            },
          },
        }}
      />
    </div>
  );
};

// Public Layout (for login/register pages)
const PublicLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-rose-50 via-pink-50 to-purple-50 flex items-center justify-center">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-20 w-60 h-60 bg-gradient-to-br from-pink-200 to-purple-200 rounded-full mix-blend-multiply filter blur-xl opacity-40 animate-pulse"></div>
        <div className="absolute bottom-20 right-20 w-60 h-60 bg-gradient-to-br from-rose-200 to-pink-200 rounded-full mix-blend-multiply filter blur-xl opacity-40 animate-pulse"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-40 h-40 bg-gradient-to-br from-purple-200 to-indigo-200 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-pulse"></div>
      </div>
      
      <div className="relative z-10 w-full max-w-md mx-auto px-4">
        {children}
      </div>
      
      <Toaster position="top-center" />
    </div>
  );
};

// Main App Component
const App: React.FC = () => {
  const [socket, setSocket] = useState<any>(null);

  useEffect(() => {
    // Initialize socket connection
    const newSocket = io(process.env.REACT_APP_API_URL || 'https://bachelor-league-production.up.railway.app', {
      transports: ['websocket', 'polling'],
      upgrade: true,
      rememberUpgrade: true,
    });

    newSocket.on('connect', () => {
      console.log('📡 Connected to Bachelor League server');
    });

    newSocket.on('disconnect', () => {
      console.log('📡 Disconnected from server');
    });

    // Real-time score updates
    newSocket.on('score_update', (data) => {
      console.log('💯 Score update received:', data);
    });

    // Live episode events
    newSocket.on('episode_event', (data) => {
      console.log('📺 Episode event:', data);
    });

    // Prediction updates
    newSocket.on('prediction_update', (data) => {
      console.log('🤖 Prediction update:', data);
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
                {/* Public Routes with special layout */}
                <Route
                  path="/login"
                  element={
                    <PublicLayout>
                      <Login />
                    </PublicLayout>
                  }
                />
                <Route
                  path="/register"
                  element={
                    <PublicLayout>
                      <Register />
                    </PublicLayout>
                  }
                />
                
                {/* Home page - public but with nav */}
                <Route
                  path="/"
                  element={
                    <AppLayout>
                      <Home />
                    </AppLayout>
                  }
                />
                
                {/* Protected Routes with beautiful layout */}
                <Route
                  path="/dashboard"
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
