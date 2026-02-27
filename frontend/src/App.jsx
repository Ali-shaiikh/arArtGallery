import { Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect, createContext, useContext } from 'react';
import Gallery from './pages/Gallery';
import Start from './pages/Start';
import SelectRole from './pages/SelectRole';
import Buyer from './pages/Buyer';
import Seller from './pages/Seller';
import ARViewer from './pages/ARViewer';
import ArtworkDetail from './pages/ArtworkDetail';

const AuthContext = createContext(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  return ctx;
}

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/me', { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        setUser(data?.user ?? null);
        setLoading(false);
      })
      .catch(() => {
        setUser(null);
        setLoading(false);
      });
  }, []);

  const login = async (email, password) => {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || 'Login failed');
    setUser(data.user);
    return data;
  };

  const signup = async (name, email, password) => {
    const res = await fetch('/api/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ name, email, password }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || 'Signup failed');
    setUser(data.user);
    return data;
  };

  const logout = () => {
    setUser(null);
    window.location.href = '/logout';
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-page">Loading...</div>;
  if (!user) return <Navigate to="/start" replace />;
  return children;
}

function PublicOnlyRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-page">Loading...</div>;
  if (user) return <Navigate to="/select-role" replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Gallery />} />
        <Route
          path="/start"
          element={
            <PublicOnlyRoute>
              <Start />
            </PublicOnlyRoute>
          }
        />
        <Route
          path="/select-role"
          element={
            <ProtectedRoute>
              <SelectRole />
            </ProtectedRoute>
          }
        />
        <Route
          path="/buyer"
          element={
            <ProtectedRoute>
              <Buyer />
            </ProtectedRoute>
          }
        />
        <Route
          path="/seller"
          element={
            <ProtectedRoute>
              <Seller />
            </ProtectedRoute>
          }
        />
        <Route path="/ar-viewer" element={<ARViewer />} />
        <Route path="/artwork/:id" element={<ArtworkDetail />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
