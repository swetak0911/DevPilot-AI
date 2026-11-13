import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Terminal, Github, Bell, User, LogOut, CheckCircle2 } from 'lucide-react';

export default function Navbar() {
  const { user, logout, isAuthenticated } = useAuth();

  return (
    <header className="h-16 border-b border-surface-800 bg-surface-900/90 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-40">
      <div className="flex items-center gap-3">
        <Link to="/" className="flex items-center gap-2 text-brand-400 font-bold text-xl tracking-tight">
          <div className="w-9 h-9 rounded-lg bg-brand-500/20 border border-brand-500/40 flex items-center justify-center text-brand-400">
            <Terminal className="w-5 h-5" />
          </div>
          <span>DevPilot<span className="text-white">.AI</span></span>
        </Link>
        <div className="hidden md:flex items-center gap-2 ml-4 px-2.5 py-1 rounded-full bg-surface-800 text-xs text-slate-300 border border-surface-800">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>swetak0911/DevPilot-AI</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {isAuthenticated ? (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-sm text-slate-300">
              <div className="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center font-semibold text-white">
                {user?.username ? user.username[0].toUpperCase() : 'U'}
              </div>
              <span className="hidden sm:inline font-medium">{user?.username}</span>
            </div>
            <button
              onClick={logout}
              title="Logout"
              className="p-2 text-slate-400 hover:text-rose-400 hover:bg-surface-800 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Link
              to="/login"
              className="text-sm font-medium text-slate-300 hover:text-white px-3 py-1.5 rounded-lg hover:bg-surface-800 transition-colors"
            >
              Sign In
            </Link>
            <Link
              to="/register"
              className="text-sm font-medium bg-brand-600 hover:bg-brand-500 text-white px-3.5 py-1.5 rounded-lg transition-colors shadow-sm shadow-brand-500/20"
            >
              Get Started
            </Link>
          </div>
        )}
      </div>
    </header>
  );
}
