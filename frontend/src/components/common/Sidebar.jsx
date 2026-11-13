import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderGit2,
  PlusCircle,
  Cpu,
  GitPullRequest,
  Workflow,
  AlertTriangle,
  Activity,
  Settings,
} from 'lucide-react';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/repositories', label: 'Repositories', icon: FolderGit2 },
  { to: '/tasks/new', label: 'New Task', icon: PlusCircle },
  { to: '/workspace', label: 'Agent Workspace', icon: Cpu },
  { to: '/review', label: 'Code Review', icon: GitPullRequest },
  { to: '/devops', label: 'DevOps & CI/CD', icon: Workflow },
  { to: '/risk', label: 'Deployment Risk', icon: AlertTriangle },
  { to: '/monitoring', label: 'Monitoring', icon: Activity },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export default function Sidebar() {
  return (
    <aside className="w-64 border-r border-surface-800 bg-surface-900 flex flex-col shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="p-4 flex-1">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 px-3 mb-2">
          Platform Modules
        </div>
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-brand-600/15 text-brand-400 border border-brand-500/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-surface-800/60'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      <div className="p-4 border-t border-surface-800">
        <div className="bg-surface-850 p-3 rounded-xl border border-surface-800 text-xs text-slate-400">
          <div className="flex items-center justify-between text-slate-300 font-medium mb-1">
            <span>Agent Engine</span>
            <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-1.5 py-0.5 rounded">
              READY
            </span>
          </div>
          <p className="text-[11px] text-slate-500">LangGraph Multi-Agent Orchestrator initialized</p>
        </div>
      </div>
    </aside>
  );
}
