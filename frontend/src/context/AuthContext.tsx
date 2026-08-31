// ==============================================================================
// MediGen AI - Authentication Context & Role Management
// ==============================================================================

import React, { createContext, useContext, useEffect, useState } from 'react';
import {
  authApi,
  tenantApi,
  clearStoredToken,
  getActiveFacilityId,
  getStoredToken,
  setActiveFacilityId,
  setStoredToken,
} from '../api/client';
import { ClinicalFacility, User, UserRole } from '../types';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  activeFacilityId: string | null;
  activeFacility: ClinicalFacility | null;
  availableFacilities: ClinicalFacility[];
  setActiveFacility: (facility: ClinicalFacility | string) => void;
  login: (email: string, password: string, remember?: boolean) => Promise<void>;
  register: (name: string, email: string, password: string, role: UserRole) => Promise<void>;
  logout: () => void;
  hasRole: (roles: UserRole | UserRole[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => {
    try {
      return typeof getStoredToken === 'function' ? getStoredToken() : null;
    } catch {
      return null;
    }
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [activeFacilityId, setActiveFacilityIdState] = useState<string | null>(() => {
    try {
      return typeof getActiveFacilityId === 'function' ? getActiveFacilityId() : null;
    } catch {
      return null;
    }
  });
  const [activeFacility, setActiveFacilityState] = useState<ClinicalFacility | null>(null);
  const [availableFacilities, setAvailableFacilities] = useState<ClinicalFacility[]>([]);

  const resolveAndSetFacility = (facs: ClinicalFacility[], currentUser: User | null) => {
    setAvailableFacilities(facs);
    let storedId: string | null = null;
    try {
      storedId = typeof getActiveFacilityId === 'function' ? getActiveFacilityId() : null;
    } catch {
      storedId = null;
    }

    let matched: ClinicalFacility | undefined;
    if (storedId) {
      matched = facs.find((f) => f.facility_id === storedId);
    }
    if (!matched && currentUser?.default_facility_id) {
      matched = facs.find((f) => f.facility_id === currentUser.default_facility_id);
    }
    if (!matched && facs.length > 0) {
      matched = facs[0];
    }

    if (matched) {
      try {
        if (typeof setActiveFacilityId === 'function') {
          setActiveFacilityId(matched.facility_id);
        }
      } catch {
        // no-op
      }
      setActiveFacilityIdState(matched.facility_id);
      setActiveFacilityState(matched);
    } else {
      setActiveFacilityState(null);
    }
  };

  const loadUserFacilities = async (currentUser: User) => {
    try {
      if (tenantApi && typeof tenantApi.listFacilities === 'function') {
        const facs = await tenantApi.listFacilities();
        resolveAndSetFacility(facs, currentUser);
      }
    } catch {
      // Graceful fallback for API failure
    }
  };

  const handleSetActiveFacility = (facility: ClinicalFacility | string) => {
    const facId = typeof facility === 'string' ? facility : facility.facility_id;
    try {
      if (typeof setActiveFacilityId === 'function') {
        setActiveFacilityId(facId);
      }
    } catch {
      // no-op
    }
    setActiveFacilityIdState(facId);
    const matched = availableFacilities.find((f) => f.facility_id === facId);
    if (matched) {
      setActiveFacilityState(matched);
    } else if (typeof facility !== 'string') {
      setActiveFacilityState(facility);
    }
  };

  // Initialize session on mount
  useEffect(() => {
    const initAuth = async () => {
      const existingToken = getStoredToken();
      if (existingToken) {
        try {
          const userData = await authApi.getMe();
          setUser(userData);
          await loadUserFacilities(userData);
        } catch {
          clearStoredToken();
          setToken(null);
          setUser(null);
          setActiveFacilityIdState(null);
          setActiveFacilityState(null);
          setAvailableFacilities([]);
        }
      }
      setIsLoading(false);
    };

    initAuth();

    // Listen for unauthorized events from api client
    const handleUnauthorized = () => {
      setUser(null);
      setToken(null);
      setActiveFacilityIdState(null);
      setActiveFacilityState(null);
      setAvailableFacilities([]);
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
      await loadUserFacilities(res.user);
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
    setActiveFacilityIdState(null);
    setActiveFacilityState(null);
    setAvailableFacilities([]);
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
        activeFacilityId,
        activeFacility,
        availableFacilities,
        setActiveFacility: handleSetActiveFacility,
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
