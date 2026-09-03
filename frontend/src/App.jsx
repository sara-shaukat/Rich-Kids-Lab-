import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Welcome from './pages/Welcome';
import Dashboard from './pages/Dashboard';
import Save from './pages/Save';
import Spend from './pages/Spend';
import Grow from './pages/Grow';
import Give from './pages/Give';
import Quests from './pages/Quests';
import Mentor from './pages/Mentor';
import Vault from './pages/Vault';
import VaultLevel from './pages/VaultLevel';
import MoneyLab from './pages/MoneyLab';
import { getSession } from './services/api';

const STORAGE_KEY = 'rkl_child_id';

function AppRouter() {
  const [initialRoute, setInitialRoute] = useState(null); // null = still checking

  useEffect(() => {
    // Session resumption: check localStorage for existing Child ID
    const childId = localStorage.getItem(STORAGE_KEY);
    if (!childId) {
      setInitialRoute('/');
      return;
    }

    // Verify the session still exists on the backend
    getSession(childId).then((session) => {
      if (session) {
        setInitialRoute('/dashboard');
      } else {
        // Backend doesn't know this ID — clear and start fresh
        localStorage.removeItem(STORAGE_KEY);
        setInitialRoute('/');
      }
    });
  }, []);

  if (initialRoute === null) {
    // Still checking localStorage / backend — show loading
    return (
      <div className="app-loading">
        <p>Rich Kids Lab...</p>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Welcome />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/save" element={<Save />} />
        <Route path="/spend" element={<Spend />} />
        <Route path="/grow" element={<Grow />} />
        <Route path="/give" element={<Give />} />
        <Route path="/quests" element={<Quests />} />
        <Route path="/vault" element={<Vault />} />
        <Route path="/vault/:level" element={<VaultLevel />} />
        <Route path="/lab" element={<MoneyLab />} />
        <Route path="/mentor" element={<Mentor />} />
        <Route path="*" element={<Navigate to={initialRoute} replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default AppRouter;
