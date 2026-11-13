import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { PlusCircle, Cpu, Bug, Wrench, ShieldAlert, Sparkles, FolderGit2 } from 'lucide-react';

const TASK_TYPES = [
  { value: 'BUG_FIX', label: 'Bug Fix & Repair', icon: Bug, desc: 'Detect defect, generate patch, run unit tests, and self-heal.' },
  { value: 'FEATURE', label: 'Feature Implementation', icon: Sparkles, desc: 'Add new capabilities guided by architectural conventions.' },
  { value: 'REFACTOR', label: 'Refactoring', icon: Wrench, desc: 'Clean up code structure, enhance performance and type safety.' },
  { value: 'TEST_GENERATION', label: 'Test Suite Generation', icon: ShieldAlert, desc: 'Produce comprehensive pytest or Jest test cases.' },
  { value: 'CICD_GENERATE', label: 'CI/CD Pipeline Generator', icon: Cpu, desc: 'Generate multi-stage GitHub Actions workflows.' },
  { value: 'DOCKER_CONFIG', label: 'Docker Containerization', icon: FolderGit2, desc: 'Create optimized Dockerfiles and container configurations.' },
];

export default function TaskCreationPage() {
  const [repositories, setRepositories] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState('');
  const [taskType, setTaskType] = useState('BUG_FIX');
  const [title, setTitle] = useState('');
  const [instruction, setInstruction] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchRepos = async () => {
      try {
        const res = await api.get('/repositories');
        setRepositories(res.data);
        if (res.data.length > 0) setSelectedRepo(res.data[0].id);
      } catch (err) {
        console.error('Failed to load repositories', err);
      }
    };
    fetchRepos();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title || !instruction || !selectedRepo) return;
    setSubmitting(true);
    try {
      const res = await api.post('/tasks', {
        repository_id: selectedRepo,
        title,
        instruction,
        task_type: taskType,
      });
      navigate(`/workspace?taskId=${res.data.id}`);
    } catch (err) {
      alert('Failed to submit task');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Create Engineering Task</h1>
        <p className="text-sm text-slate-400 mt-1">Submit natural language instructions for autonomous multi-agent execution</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Repository Selection */}
        <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-4">
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">Target Repository</label>
          <select
            value={selectedRepo}
            onChange={(e) => setSelectedRepo(e.target.value)}
            className="w-full px-4 py-3 rounded-xl bg-surface-850 border border-surface-800 text-white text-sm focus:border-brand-500 focus:outline-none"
          >
            {repositories.map((repo) => (
              <option key={repo.id} value={repo.id}>
                {repo.full_name} ({repo.primary_language || 'General'})
              </option>
            ))}
          </select>
        </div>

        {/* Task Type Grid */}
        <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-4">
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">Task Category</label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {TASK_TYPES.map((type) => {
              const Icon = type.icon;
              const isSelected = taskType === type.value;
              return (
                <div
                  key={type.value}
                  onClick={() => setTaskType(type.value)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-brand-500/10 border-brand-500 text-white'
                      : 'bg-surface-850 border-surface-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <div className="flex items-center gap-2 font-bold text-sm mb-1">
                    <Icon className={`w-4 h-4 ${isSelected ? 'text-brand-400' : 'text-slate-500'}`} />
                    <span>{type.label}</span>
                  </div>
                  <p className="text-xs text-slate-400">{type.desc}</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Task Details */}
        <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Task Title</label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Fix token validation error and add boundary unit tests"
              className="w-full px-4 py-3 rounded-xl bg-surface-850 border border-surface-800 text-white text-sm focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Natural Language Instructions</label>
            <textarea
              required
              rows={5}
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              placeholder="Describe the objective in detail. Example: Analyze the authentication module, identify the login validation bug, fix it, generate unit tests, execute the tests in the sandbox, analyze any failures, and prepare a GitHub PR."
              className="w-full p-4 rounded-xl bg-surface-850 border border-surface-800 text-white text-sm focus:border-brand-500 focus:outline-none"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-3.5 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-bold rounded-xl transition-colors shadow-lg shadow-brand-500/20"
        >
          {submitting ? 'Initializing Agent Swarm...' : 'Dispatch to Agent Swarm'}
        </button>
      </form>
    </div>
  );
}
