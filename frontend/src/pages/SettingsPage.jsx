import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Settings as SettingsIcon, Github, Key, Check, AlertCircle, Save, Trash2, ExternalLink, RefreshCw } from 'lucide-react';

export default function SettingsPage() {
  const [llmProvider, setLlmProvider] = useState('openai');
  const [modelName, setModelName] = useState('gpt-4o-mini');
  const [apiKey, setApiKey] = useState('');
  
  // GitHub Integration state
  const [githubStatus, setGithubStatus] = useState(null);
  const [githubToken, setGithubToken] = useState('');
  const [githubUsername, setGithubUsername] = useState('');
  const [loadingGhStatus, setLoadingGhStatus] = useState(true);
  const [connectingGh, setConnectingGh] = useState(false);
  const [disconnectingGh, setDisconnectingGh] = useState(false);

  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const fetchGitHubStatus = async () => {
    try {
      const res = await api.get('/github/status');
      setGithubStatus(res.data);
      if (res.data.github_username) {
        setGithubUsername(res.data.github_username);
      }
    } catch (err) {
      console.error('Failed to load GitHub status', err);
    } finally {
      setLoadingGhStatus(false);
    }
  };

  useEffect(() => {
    fetchGitHubStatus();
  }, []);

  const handleConnectGitHub = async (e) => {
    e.preventDefault();
    if (!githubToken.trim()) return;
    setConnectingGh(true);
    try {
      const res = await api.post('/github/connect', {
        access_token: githubToken.trim(),
        github_username: githubUsername.trim() || undefined,
      });
      setGithubStatus(res.data);
      setGithubToken('');
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to connect GitHub token');
    } finally {
      setConnectingGh(false);
    }
  };

  const handleDisconnectGitHub = async () => {
    if (!confirm('Are you sure you want to disconnect your GitHub account?')) return;
    setDisconnectingGh(true);
    try {
      await api.delete('/github/disconnect');
      setGithubStatus({ is_connected: false });
      setGithubUsername('');
    } catch (err) {
      alert('Failed to disconnect GitHub account');
    } finally {
      setDisconnectingGh(false);
    }
  };

  const handleOAuthConnect = async () => {
    try {
      const res = await api.get('/github/authorize-url');
      window.location.href = res.data.authorize_url;
    } catch (err) {
      alert('Failed to initialize GitHub OAuth authorization');
    }
  };

  const handleSaveLLMSettings = async (e) => {
    e.preventDefault();
    setSaving(true);
    // Simulates saving LLM configurations to local state / preferences
    setTimeout(() => {
      setSaving(false);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    }, 400);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Platform Configuration & Keys</h1>
        <p className="text-sm text-slate-400 mt-1">Configure LLM providers, GitHub API tokens, and runtime environments</p>
      </div>

      {savedSuccess && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm flex items-center gap-2">
          <Check className="w-4 h-4" />
          <span>Configuration saved successfully!</span>
        </div>
      )}

      {/* GitHub Integration Section (Phase 2 Focus) */}
      <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-surface-800 flex items-center justify-center text-white">
              <Github className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">GitHub Integration</h3>
              <p className="text-xs text-slate-400">OAuth / Personal Access Token with encrypted storage</p>
            </div>
          </div>

          {githubStatus?.is_connected ? (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Connected (@{githubStatus.github_username})
            </span>
          ) : (
            <span className="px-3 py-1 rounded-full bg-slate-800 text-slate-400 text-xs font-semibold">
              Not Connected
            </span>
          )}
        </div>

        {githubStatus?.is_connected ? (
          <div className="p-4 rounded-xl bg-surface-850 border border-surface-800 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {githubStatus.github_avatar_url ? (
                  <img
                    src={githubStatus.github_avatar_url}
                    alt={githubStatus.github_username}
                    className="w-10 h-10 rounded-full border border-surface-700"
                  />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-brand-600 flex items-center justify-center font-bold text-white">
                    {githubStatus.github_username?.[0]?.toUpperCase() || 'G'}
                  </div>
                )}
                <div>
                  <div className="text-sm font-bold text-white">@{githubStatus.github_username}</div>
                  <div className="text-xs text-slate-400">
                    Scopes: {githubStatus.scopes?.join(', ') || 'repo, workflow'}
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={handleDisconnectGitHub}
                disabled={disconnectingGh}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-semibold transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Disconnect</span>
              </button>
            </div>

            {githubStatus.rate_limit && (
              <div className="text-xs text-slate-400 flex justify-between pt-2 border-t border-surface-800">
                <span>GitHub API Rate Limit:</span>
                <span className="font-mono text-emerald-400">
                  {githubStatus.rate_limit.remaining} / {githubStatus.rate_limit.limit} requests remaining
                </span>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <form onSubmit={handleConnectGitHub} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Personal Access Token (PAT)
                </label>
                <input
                  type="password"
                  required
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                  placeholder="ghp_••••••••••••••••••••••••••••••••"
                  className="w-full px-4 py-2.5 rounded-xl bg-surface-850 border border-surface-800 text-white text-sm focus:border-brand-500 focus:outline-none font-mono"
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  Requires <code>repo</code> and <code>workflow</code> permissions. Encrypted before database storage.
                </p>
              </div>

              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={connectingGh}
                  className="flex-1 py-2.5 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-semibold rounded-xl text-sm transition-colors"
                >
                  {connectingGh ? 'Verifying & Encrypting...' : 'Link GitHub via PAT'}
                </button>

                <button
                  type="button"
                  onClick={handleOAuthConnect}
                  className="px-4 py-2.5 bg-surface-850 hover:bg-surface-800 border border-surface-800 text-slate-200 font-semibold rounded-xl text-sm transition-colors flex items-center gap-1.5"
                >
                  <ExternalLink className="w-4 h-4" />
                  <span>GitHub OAuth</span>
                </button>
              </div>
            </form>
          </div>
        )}
      </div>

      {/* LLM Provider Settings */}
      <form onSubmit={handleSaveLLMSettings} className="space-y-6">
        <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Key className="w-4 h-4 text-brand-400" />
            <span>LLM Provider Abstraction</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Provider</label>
              <select
                value={llmProvider}
                onChange={(e) => setLlmProvider(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-surface-850 border border-surface-800 text-white text-sm focus:border-brand-500 focus:outline-none"
              >
                <option value="openai">OpenAI (GPT-4o, GPT-4o-mini)</option>
                <option value="gemini">Google Gemini (Gemini 1.5 Pro, Flash)</option>
                <option value="groq">Groq (Llama-3.3-70B)</option>
                <option value="ollama">Ollama (Local / Open-weight models)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Model Identifier</label>
              <input
                type="text"
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-surface-850 border border-surface-800 text-white text-sm focus:border-brand-500 focus:outline-none font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Provider API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-••••••••••••••••••••••••••••••••"
              className="w-full px-4 py-2.5 rounded-xl bg-surface-850 border border-surface-800 text-white text-sm focus:border-brand-500 focus:outline-none font-mono"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="flex items-center justify-center gap-2 w-full py-3 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-bold rounded-xl transition-colors shadow-lg shadow-brand-500/20"
        >
          <Save className="w-4 h-4" />
          <span>{saving ? 'Updating...' : 'Save LLM Configuration'}</span>
        </button>
      </form>
    </div>
  );
}
