// src/components/Navbar/Navbar.jsx
import { useAuth } from "../../hooks/useAuth";

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="h-14 border-b border-slate-200 bg-white flex items-center justify-between px-6">
      <span className="font-semibold text-slate-800">Customer Data Platform</span>
      <div className="flex items-center gap-4">
        {user && <span className="text-sm text-slate-500">{user.username}</span>}
        <button className="btn-secondary" onClick={logout}>
          Logout
        </button>
      </div>
    </header>
  );
}
