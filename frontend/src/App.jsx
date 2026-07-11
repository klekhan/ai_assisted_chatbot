import { BrowserRouter, Routes, Route } from "react-router-dom";
import ChatPage from "./pages/ChatPage";
import AdminLoginPage from "./pages/AdminLoginPage";
import AdminDashboardPage from "./pages/AdminDashboardPage";
import { useAdminAuth } from "./lib/useAdminAuth";

function AdminRoute() {
  const { adminKey, isAuthenticated, login, logout, verifying, error } = useAdminAuth();

  if (!isAuthenticated) {
    return <AdminLoginPage onLogin={login} verifying={verifying} error={error} />;
  }
  return <AdminDashboardPage adminKey={adminKey} onLogout={logout} />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ChatPage />} />
        <Route path="/admin" element={<AdminRoute />} />
      </Routes>
    </BrowserRouter>
  );
}
