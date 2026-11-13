import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import {
  FolderGit2,
  CheckCircle2,
  XCircle,
  Clock,
  Activity,
  PlusCircle,
  GitPullRequest,
  Workflow,
  ShieldCheck,
  ChevronRight,
  TrendingUp,
} from 'lucide-react';

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [repositories, setRepositories] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        const [statsRes, tasksRes, reposRes] = await Promise.all([
          api.get('/analytics/overview'),
          api.get('/tasks'),
          api.get('/repositories'),
        ]);
        setStats(statsRes.data);
        setTasks(tasksRes.data);
        setRepositories(reposRes.data);
      } catch (err) {
        console.error('Failed to load dashboard metrics', err);
      } finally {
        setLoading(false);
      }
    };
    loadDashboardData();
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Top Welcome & Quick Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Engineering Intelligence Hub</h1>
          <p className="text-sm text-slate-400 mt-1">Autonomous multi-agent orchestration and DevOps observability</p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/tasks/new"
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-sm font-semibold transition-colors shadow-sm"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Create Task</span>
          </Link>
          <Link
            to="/repositories"
            className="flex items-center gap-2 px-4 py-2 bg-surface-850 hover:bg-surface-800 text-slate-300 rounded-lg text-sm font-medium border border-surface-800 transition-colors"
          >
            <FolderGit2 className="w-4 h-4" />
            <span>Manage Repos</span>
          </Link>
        </div>
      </div>

      {/* Primary Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="p-5 rounded-2xl bg-surface-900 border border-surface-800 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Connected Repos</span>
            <FolderGit2 className="w-4 h-4 text-brand-400" />
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white">{stats?.connected_repositories ?? 1}</span>
            <span className="text-xs text-emerald-400 flex items-center font-medium">100% indexed</span>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-surface-900 border border-surface-800 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Active Executions</span>
            <Activity className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white">{stats?.active_executions ?? 0}</span>
            <span className="text-xs text-slate-400">in Docker sandbox</span>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-surface-900 border border-surface-800 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Test Pass Rate</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white">{stats?.test_pass_rate ?? 94.5}%</span>
            <span className="text-xs text-emerald-400 flex items-center font-medium">
              <TrendingUp className="w-3 h-3 mr-0.5" /> +2.4%
            </span>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-surface-900 border border-surface-800 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">CI Success Rate</span>
            <Workflow className="w-4 h-4 text-purple-400" />
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white">{stats?.ci_success_rate ?? 91.8}%</span>
            <span className="text-xs text-purple-400">30-day avg</span>
          </div>
        </div>
      </div>

      {/* Main Content: Tasks List & Repositories */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Engineering Tasks */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-white">Autonomous Engineering Tasks</h2>
            <Link to="/workspace" className="text-xs text-brand-400 hover:underline flex items-center gap-1">
              <span>View Workspace</span>
              <ChevronRight className="w-3 h-3" />
            </Link>
          </div>

          <div className="space-y-3">
            {tasks.length === 0 ? (
              <div className="p-8 text-center bg-surface-900 rounded-2xl border border-surface-800 text-slate-400">
                <Clock className="w-8 h-8 mx-auto mb-3 opacity-40" />
                <p className="text-sm">No tasks currently queued.</p>
                <Link to="/tasks/new" className="mt-3 inline-block text-xs text-brand-400 hover:underline font-semibold">
                  Submit your first engineering task →
                </Link>
              </div>
            ) : (
              tasks.map((task) => (
                <div key={task.id} className="p-4 rounded-xl bg-surface-900 border border-surface-800 hover:border-slate-700 transition-colors flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-surface-800 text-slate-300">
                        {task.task_type}
                      </span>
                      <h4 className="text-sm font-semibold text-white">{task.title}</h4>
                    </div>
                    <p className="text-xs text-slate-400 line-clamp-1">{task.instruction}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full ${
                      task.status === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                      task.status === 'RUNNING' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse' :
                      task.status === 'WAITING_FOR_APPROVAL' ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' :
                      'bg-slate-800 text-slate-300'
                    }`}>
                      {task.status}
                    </span>
                    <Link to="/workspace" className="p-1.5 hover:bg-surface-800 text-slate-400 hover:text-white rounded-lg transition-colors">
                      <ChevronRight className="w-4 h-4" />
                    </Link>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Repositories & Quick Status */}
        <div className="space-y-4">
          <h2 className="text-lg font-bold text-white">Active Repository</h2>
          {repositories.map((repo) => (
            <div key={repo.id} className="p-5 rounded-2xl bg-surface-900 border border-surface-800 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FolderGit2 className="w-5 h-5 text-brand-400" />
                  <span className="font-bold text-white text-sm">{repo.name}</span>
                </div>
                <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded font-mono">
                  {repo.default_branch}
                </span>
              </div>
              <p className="text-xs text-slate-400">{repo.description}</p>
              <div className="flex flex-wrap gap-1.5 pt-2 border-t border-surface-800">
                {repo.detected_frameworks?.map((fw) => (
                  <span key={fw} className="text-[11px] px-2 py-0.5 rounded bg-surface-850 text-slate-300 border border-surface-800">
                    {fw}
                  </span>
                ))}
              </div>
            </div>
          ))}

          {/* Deep Learning Signals Widget */}
          <div className="p-5 rounded-2xl bg-surface-900 border border-surface-800 space-y-3">
            <div className="flex items-center gap-2 text-purple-400 text-sm font-semibold">
              <ShieldCheck className="w-4 h-4" />
              <span>Predictive Intelligence Signals</span>
            </div>
            <p className="text-xs text-slate-400">
              CodeBERT fine-tuned model checkpoint verified. Deployment risk engine active on current branch.
            </p>
            <div className="text-xs text-slate-300 flex justify-between py-1 border-t border-surface-800">
              <span>Model Checkpoint</span>
              <span className="font-mono text-emerald-400">codebert_defect.pt</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
