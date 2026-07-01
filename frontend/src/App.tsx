import { useEffect, type ReactNode } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import WalletPage from './pages/WalletPage';
import GamesPage from './pages/GamesPage';
import AdminPage from './pages/AdminPage';
import MinesGamePage from './pages/MinesGamePage';
import SlotsPage from './pages/SlotsPage';
import ScratchCardPage from './pages/ScratchCardPage';
import VIPPage from './pages/VIPPage';
import PromotionsPage from './pages/PromotionsPage';

function PrivateRoute({ children }: { children: ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function App() {
  const { isAuthenticated, loadUser } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      loadUser();
    }
  }, [isAuthenticated, loadUser]);

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/dashboard"
        element={
          <PrivateRoute>
            <DashboardPage />
          </PrivateRoute>
        }
      />
      <Route
        path="/wallet"
        element={
          <PrivateRoute>
            <WalletPage />
          </PrivateRoute>
        }
      />
      <Route
        path="/games"
        element={
          <PrivateRoute>
            <GamesPage />
          </PrivateRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <PrivateRoute>
            <AdminPage />
          </PrivateRoute>
        }
      />
      <Route
        path="/games/mines"
        element={
          <PrivateRoute>
            <MinesGamePage />
          </PrivateRoute>
        }
      />
      <Route
        path="/slots"
        element={
          <PrivateRoute>
            <SlotsPage />
          </PrivateRoute>
        }
      />
      <Route
        path="/games/scratch-card"
        element={
          <PrivateRoute>
            <ScratchCardPage />
          </PrivateRoute>
        }
      />
      <Route
        path="/vip"
        element={
          <PrivateRoute>
            <VIPPage />
          </PrivateRoute>
        }
      />
      <Route
        path="/promotions"
        element={
          <PrivateRoute>
            <PromotionsPage />
          </PrivateRoute>
        }
      />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default App;
