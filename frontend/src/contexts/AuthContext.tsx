import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';

// Types
interface User {
  id: string;
  username: string;
  email: string;
  avatar?: string;
  totalPoints: number;
  currentRank: number;
  joinedAt: string;
  favoriteShow: string;
  profile: {
    firstName?: string;
    lastName?: string;
    bio?: string;
    location?: string;
    favoriteContestant?: string;
    predictionAccuracy: number;
    totalPredictions: number;
    correctPredictions: number;
    longestStreak: number;
    currentStreak: number;
  };
  preferences: {
    emailNotifications: boolean;
    pushNotifications: boolean;
    spoilerProtection: boolean;
    autoPickTeam: boolean;
    favoriteShowTypes: string[];
  };
  stats: {
    seasonsParticipated: number;
    totalLeagues: number;
    wins: number;
    topThreeFinishes: number;
    averageRank: number;
    bestRank: number;
    pointsThisSeason: number;
    pointsAllTime: number;
  };
}

interface LoginCredentials {
  email: string;
  password: string;
}

interface RegisterData {
  username: string;
  email: string;
  password: string;
  confirmPassword: string;
  favoriteShow?: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  updateProfile: (updates: Partial<User['profile']>) => Promise<void>;
  updatePreferences: (updates: Partial<User['preferences']>) => Promise<void>;
  refreshUser: () => void;
  resetPassword: (email: string) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
}

// Create Context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// API Functions
const authAPI = {
  // Get current user
  getCurrentUser: async (): Promise<User> => {
    const token = localStorage.getItem('authToken');
    if (!token) throw new Error('No auth token');

    const response = await fetch(`${process.env.REACT_APP_API_URL}/api/auth/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('authToken');
        localStorage.removeItem('refreshToken');
        throw new Error('Token expired');
      }
      throw new Error('Failed to get user');
    }

    return response.json();
  },

  // Login
  login: async (credentials: LoginCredentials): Promise<{ user: User; token: string; refreshToken: string }> => {
    const response = await fetch(`${process.env.REACT_APP_API_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(credentials),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Login failed');
    }

    return response.json();
  },

  // Register
  register: async (data: RegisterData): Promise<{ user: User; token: string; refreshToken: string }> => {
    const response = await fetch(`${process.env.REACT_APP_API_URL}/api/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Registration failed');
    }

    return response.json();
  },

  // Update profile
  updateProfile: async (updates: Partial<User['profile']>): Promise<User> => {
    const token = localStorage.getItem('authToken');
    const response = await fetch(`${process.env.REACT_APP_API_URL}/api/auth/profile`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updates),
    });

    if (!response.ok) throw new Error('Failed to update profile');
    return response.json();
  },

  // Update preferences
  updatePreferences: async (updates: Partial<User['preferences']>): Promise<User> => {
    const token = localStorage.getItem('authToken');
    const response = await fetch(`${process.env.REACT_APP_API_URL}/api/auth/preferences`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updates),
    });

    if (!response.ok) throw new Error('Failed to update preferences');
    return response.json();
  },

  // Reset password
  resetPassword: async (email: string): Promise<void> => {
    const response = await fetch(`${process.env.REACT_APP_API_URL}/api/auth/reset-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) throw new Error('Failed to send reset email');
  },

  // Change password
  changePassword: async (currentPassword: string, newPassword: string): Promise<void> => {
    const token = localStorage.getItem('authToken');
    const response = await fetch(`${process.env.REACT_APP_API_URL}/api/auth/change-password`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ currentPassword, newPassword }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to change password');
    }
  },
};

// Provider Component
export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isInitialized, setIsInitialized] = useState(false);
  const queryClient = useQueryClient();

  // Get user query
  const {
    data: user,
    isLoading: loading,
    error,
    refetch: refreshUser,
  } = useQuery({
    queryKey: ['currentUser'],
    queryFn: authAPI.getCurrentUser,
    enabled: !!localStorage.getItem('authToken'),
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
  });

  // Initialize auth state
  useEffect(() => {
    const token = localStorage.getItem('authToken');
    if (token) {
      refreshUser();
    }
    setIsInitialized(true);
  }, [refreshUser]);

  // Handle auth errors
  useEffect(() => {
    if (error) {
      localStorage.removeItem('authToken');
      localStorage.removeItem('refreshToken');
      queryClient.clear();
    }
  }, [error, queryClient]);

  // Login mutation
  const loginMutation = useMutation({
    mutationFn: authAPI.login,
    onSuccess: (data) => {
      localStorage.setItem('authToken', data.token);
      localStorage.setItem('refreshToken', data.refreshToken);
      queryClient.setQueryData(['currentUser'], data.user);
      toast.success(`Welcome back, ${data.user.username}!`);
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  // Register mutation
  const registerMutation = useMutation({
    mutationFn: authAPI.register,
    onSuccess: (data) => {
      localStorage.setItem('authToken', data.token);
      localStorage.setItem('refreshToken', data.refreshToken);
      queryClient.setQueryData(['currentUser'], data.user);
      toast.success(`Welcome to Bachelor Fantasy League, ${data.user.username}!`);
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  // Update profile mutation
  const updateProfileMutation = useMutation({
    mutationFn: authAPI.updateProfile,
    onSuccess: (updatedUser) => {
      queryClient.setQueryData(['currentUser'], updatedUser);
      toast.success('Profile updated successfully!');
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  // Update preferences mutation
  const updatePreferencesMutation = useMutation({
    mutationFn: authAPI.updatePreferences,
    onSuccess: (updatedUser) => {
      queryClient.setQueryData(['currentUser'], updatedUser);
      toast.success('Preferences updated!');
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  // Reset password mutation
  const resetPasswordMutation = useMutation({
    mutationFn: authAPI.resetPassword,
    onSuccess: () => {
      toast.success('Password reset email sent! Check your inbox.');
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  // Change password mutation
  const changePasswordMutation = useMutation({
    mutationFn: ({ currentPassword, newPassword }: { currentPassword: string; newPassword: string }) =>
      authAPI.changePassword(currentPassword, newPassword),
    onSuccess: () => {
      toast.success('Password changed successfully!');
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  // Auth functions
  const login = async (credentials: LoginCredentials) => {
    await loginMutation.mutateAsync(credentials);
  };

  const register = async (data: RegisterData) => {
    // Validate password confirmation
    if (data.password !== data.confirmPassword) {
      throw new Error('Passwords do not match');
    }
    
    // Validate password strength
    if (data.password.length < 8) {
      throw new Error('Password must be at least 8 characters long');
    }

    await registerMutation.mutateAsync(data);
  };

  const logout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('refreshToken');
    queryClient.clear();
    toast.success('Logged out successfully');
    window.location.href = '/login';
  };

  const updateProfile = async (updates: Partial<User['profile']>) => {
    await updateProfileMutation.mutateAsync(updates);
  };

  const updatePreferences = async (updates: Partial<User['preferences']>) => {
    await updatePreferencesMutation.mutateAsync(updates);
  };

  const resetPassword = async (email: string) => {
    await resetPasswordMutation.mutateAsync(email);
  };

  const changePassword = async (currentPassword: string, newPassword: string) => {
    await changePasswordMutation.mutateAsync({ currentPassword, newPassword });
  };

  // Context value
  const value: AuthContextType = {
    user: user || null,
    loading: loading || !isInitialized,
    isAuthenticated: !!user && !!localStorage.getItem('authToken'),
    login,
    register,
    logout,
    updateProfile,
    updatePreferences,
    refreshUser,
    resetPassword,
    changePassword,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook to use the context
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Helper hooks
export const useAuthActions = () => {
  const { login, register, logout, resetPassword, changePassword } = useAuth();
  return { login, register, logout, resetPassword, changePassword };
};

export const useUserProfile = () => {
  const { user, updateProfile, updatePreferences, loading } = useAuth();
  return { 
    profile: user?.profile, 
    preferences: user?.preferences, 
    stats: user?.stats,
    updateProfile, 
    updatePreferences, 
    loading 
  };
};

// Auth utilities
export const getAuthHeaders = () => {
  const token = localStorage.getItem('authToken');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export const isTokenExpired = (token: string): boolean => {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
};

// Token refresh utility
export const refreshAuthToken = async (): Promise<string | null> => {
  const refreshToken = localStorage.getItem('refreshToken');
  if (!refreshToken) return null;

  try {
    const response = await fetch(`${process.env.REACT_APP_API_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refreshToken }),
    });

    if (!response.ok) {
      localStorage.removeItem('authToken');
      localStorage.removeItem('refreshToken');
      return null;
    }

    const { token } = await response.json();
    localStorage.setItem('authToken', token);
    return token;
  } catch {
    localStorage.removeItem('authToken');
    localStorage.removeItem('refreshToken');
    return null;
  }
};

export default AuthContext;
