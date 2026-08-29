// ==============================================================================
// MediGen AI - Authentication Context & Role Management
// ==============================================================================

import React, { createContext, useContext, useEffect, useState } from 'react';
import { authApi, clearStoredToken, getStoredToken, setStoredToken } from '../api/client';
import { User, UserRole } from '../types';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string, remember?: boolean) => Promise<void>;
  register: (name: string, email: string, password: string, role: UserRole) => Promise<void>;
  logout: () => void;
  hasRole: (roles: UserRole | UserRole[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(getStoredToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initialize session on mount
  useEffect(() => {
    const initAuth = async () => {
      const existingToken = getStoredToken();
      if (existingToken) {
        try {
          const userData = await authApi.getMe();
          setUser(userData);
        } catch {
          clearStoredToken();
          setToken(null);
          setUser(null);
        }
      }
      setIsLoading(false);
    };

    initAuth();

    // Listen for unauthorized events from api client
    const handleUnauthorized = () => {
      setUser(null);
      setToken(null);
    };

    window.addEventListener('medigen:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('medigen:unauthorized', handleUnauthorized);
  }, []);

  const login = async (email: string, password: string, remember = true): Promise<void> => {
    setIsLoading(true);
    try {
      const res = await authApi.login(email, password);
      setStoredToken(res.access_token, remember);
      setToken(res.access_token);
      setUser(res.user);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (
    name: string,
    email: string,
    password: string,
    role: UserRole
  ): Promise<void> => {
    setIsLoading(true);
    try {
      await authApi.register(name, email, password, role);
      // Auto-login after registration
      await login(email, password);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    clearStoredToken();
    setToken(null);
    setUser(null);
  };

  const hasRole = (roles: UserRole | UserRole[]): boolean => {
    if (!user) return false;
    const allowed = Array.isArray(roles) ? roles : [roles];
    return allowed.includes(user.role);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        register,
        logout,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
