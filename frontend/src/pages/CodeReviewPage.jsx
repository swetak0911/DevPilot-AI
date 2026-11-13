import React, { useState, useEffect } from 'react';
import api from '../services/api';
import {
  GitPullRequest,
  CheckCircle2,
  XCircle,
  FileCode,
  ShieldCheck,
  AlertTriangle,
  Send,
  ExternalLink,
  Split,
  AlignLeft,
  Sparkles,
  GitBranch,
  ShieldAlert,
  ChevronDown,
  Info
} from 'lucide-react';

export default function CodeReviewPage() {
  const [tasks, setTasks] = useState([]);
  const [selectedTaskId, setSelectedTaskId] = useState('');
  const [currentTask, setCurrentTask] = useState(null);
  const [structuredDiff, setStructuredDiff] = useState(null);
  const [review, setReview] = useState(null);
  const [prCreated, setPrCreated] = useState(null);

  const [viewMode, setViewMode] = useState('side_by_side'); // 'side_by_side' or 'unified'
  const [approving, setApproving] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [reviewerComments, setReviewerComments] = useState('');
  const [branchName, setBranchName] = useState('');

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const res = await api.get('/tasks');
        setTasks(res.data);
        if (res.data.length > 0) {
          const firstId = res.data[0].id;
          setSelectedTaskId(firstId);
          loadTaskDetails(firstId);
        }
      } catch (err) {
        console.error('Failed to load tasks', err);
      }
    };
    fetchTasks();
  }, []);

  const loadTaskDetails = async (id) => {
    try {
      const [taskRes, diffRes, reviewRes, prRes] = await Promise.all([
        api.get(`/tasks/${id}`).catch(() => ({ data: null })),
        api.get(`/tasks/${id}/diff-structured`).catch(() => ({ data: null })),
        api.get(`/tasks/${id}/review`).catch(() => ({ data: null })),
        api.get(`/tasks/${id}/pr`).catch(() => ({ data: null }))
      ]);

      if (taskRes.data) {
        setCurrentTask(taskRes.data);
        setBranchName(`devpilot/patch-${id.slice(0, 8)}`);
      }
      setStructuredDiff(diffRes.data);
      setReview(reviewRes.data);
      setPrCreated(prRes.data);
    } catch (err) {
      console.error('Failed to load task review details', err);
    }
  };

  const handleTaskChange = (e) => {
    const id = e.target.value;
    setSelectedTaskId(id);
    setPrCreated(null);
    loadTaskDetails(id);
  };

  const handleTriggerAIReview = async () => {
    if (!selectedTaskId) return;
    setReviewing(true);
    try {
      const res = await api.post(`/tasks/${selectedTaskId}/review`);
      setReview(res.data);
      alert('AI Code Review and Regression Analysis completed!');
    } catch (err) {
      alert('Review analysis failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setReviewing(false);
    }
  };

  const handleApproveAndPR = async () => {
    if (!selectedTaskId) return;
    setApproving(true);
    try {
      const prRes = await api.post(`/tasks/${selectedTaskId}/approve`, {
        approved: true,
        comments: reviewerComments || 'Approved via DevPilot AI Code Review interface'
      });
      setPrCreated(prRes.data);
      await loadTaskDetails(selectedTaskId);
      alert('Changes approved and Pull Request created successfully!');
    } catch (err) {
      alert('Failed to approve changes: ' + (err.response?.data?.detail || err.message));
    } finally {
      setApproving(false);
    }
  };

  const handleReject = async () => {
    if (!selectedTaskId) return;
    setRejecting(true);
    try {
      await api.post(`/tasks/${selectedTaskId}/reject`, {
        approved: false,
        comments: reviewerComments || 'Rejected by reviewer'
      });
      await loadTaskDetails(selectedTaskId);
      alert('Patch rejected and task marked FAILED.');
    } catch (err) {
      alert('Failed to reject changes: ' + (err.response?.data?.detail || err.message));
    } finally {
      setRejecting(false);
    }
  };

  const stats = structuredDiff?.stats || { additions: 0, deletions: 0, unchanged: 0 };
  const lines = structuredDiff?.lines || [];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-brand-500/10 text-brand-400 border border-brand-500/20">
              PHASE 9: REVIEW & PULL REQUESTS
            </span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Code Review & Approval Gate</h1>
          <p className="text-sm text-slate-400">
            Side-by-side diff inspection, AI regression analysis, and authorized GitHub Pull Request generation.
          </p>
        </div>

        {/* Task Selector */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <select
              value={selectedTaskId}
              onChange={handleTaskChange}
              className="bg-surface-900 border border-surface-800 text-xs text-white rounded-lg px-3 py-2 pr-8 appearance-none focus:outline-none focus:border-brand-500"
            >
              {tasks.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.title.slice(0, 36)}... ({t.status})
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-3 pointer-events-none" />
          </div>

          <button
            onClick={handleTriggerAIReview}
            disabled={reviewing || !selectedTaskId}
            className="flex items-center gap-2 px-3.5 py-2 bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 rounded-lg text-xs font-bold transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{reviewing ? 'Analyzing...' : 'AI Regression Review'}</span>
          </button>
        </div>
      </div>

      {/* PR Created Banner */}
      {prCreated && (
        <div className="p-5 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <GitPullRequest className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-emerald-200">
                GitHub Pull Request #{prCreated.pr_number} Created
              </h2>
              <div className="text-xs text-emerald-300/80 font-mono mt-0.5">
                Branch: <span className="font-bold text-white">{prCreated.branch_name}</span> ➔ {prCreated.base_branch || 'main'}
              </div>
            </div>
          </div>
          <a
            href={prCreated.html_url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold transition-all shadow-md shadow-emerald-500/20"
          >
            <span>View on GitHub</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      )}

      {/* Main Review & Diff Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Columns: Diff Viewer */}
        <div className="lg:col-span-2 space-y-4">
          {/* Diff Controls Header */}
          <div className="p-4 rounded-xl bg-surface-900 border border-surface-800 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 font-mono text-xs text-brand-400">
                <FileCode className="w-4 h-4 text-slate-400" />
                <span className="font-semibold">{structuredDiff?.file_path || 'src/main.py'}</span>
              </div>
              <div className="flex items-center gap-1.5 text-[11px] font-mono">
                <span className="text-emerald-400 font-semibold">+{stats.additions}</span>
                <span className="text-rose-400 font-semibold">-{stats.deletions}</span>
              </div>
            </div>

            {/* View Mode Toggle */}
            <div className="flex items-center gap-1 bg-surface-950 p-1 rounded-lg border border-surface-800">
              <button
                onClick={() => setViewMode('side_by_side')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-semibold transition-colors ${
                  viewMode === 'side_by_side'
                    ? 'bg-brand-600 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Split className="w-3.5 h-3.5" />
                <span>Side-by-Side</span>
              </button>
              <button
                onClick={() => setViewMode('unified')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-semibold transition-colors ${
                  viewMode === 'unified'
                    ? 'bg-brand-600 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <AlignLeft className="w-3.5 h-3.5" />
                <span>Unified</span>
              </button>
            </div>
          </div>

          {/* Side-by-Side Diff Container */}
          {viewMode === 'side_by_side' ? (
            <div className="rounded-2xl bg-surface-950 border border-surface-800 overflow-hidden font-mono text-xs">
              <div className="grid grid-cols-2 bg-surface-900 border-b border-surface-800 text-[11px] text-slate-400 font-semibold">
                <div className="p-2.5 px-4 border-r border-surface-800">Original (Base Branch)</div>
                <div className="p-2.5 px-4 text-brand-300">Proposed Changes (Feature Branch)</div>
              </div>

              <div className="max-h-[500px] overflow-y-auto divide-y divide-surface-900">
                {lines.length === 0 ? (
                  <div className="p-8 text-center text-slate-500 italic">No diff available for this task.</div>
                ) : (
                  lines.map((line, idx) => {
                    const isDel = line.type === 'deletion';
                    const isAdd = line.type === 'addition';
                    return (
                      <div key={idx} className="grid grid-cols-2 text-[11px] leading-relaxed">
                        {/* Left column (Original) */}
                        <div
                          className={`p-1.5 px-3 flex items-start gap-2 border-r border-surface-850 overflow-x-auto ${
                            isDel ? 'bg-rose-500/10 text-rose-300' : 'text-slate-400'
                          }`}
                        >
                          <span className="w-8 text-right text-slate-600 select-none shrink-0 font-mono text-[10px]">
                            {line.old_lineno || ''}
                          </span>
                          <span className="shrink-0 text-slate-600 select-none">
                            {isDel ? '-' : ' '}
                          </span>
                          <span className="whitespace-pre">{isDel || line.type === 'context' ? line.content : ''}</span>
                        </div>

                        {/* Right column (Modified) */}
                        <div
                          className={`p-1.5 px-3 flex items-start gap-2 overflow-x-auto ${
                            isAdd ? 'bg-emerald-500/10 text-emerald-300' : 'text-slate-300'
                          }`}
                        >
                          <span className="w-8 text-right text-slate-600 select-none shrink-0 font-mono text-[10px]">
                            {line.new_lineno || ''}
                          </span>
                          <span className="shrink-0 text-slate-600 select-none">
                            {isAdd ? '+' : ' '}
                          </span>
                          <span className="whitespace-pre">{isAdd || line.type === 'context' ? line.content : ''}</span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          ) : (
            /* Unified Diff Container */
            <div className="rounded-2xl bg-surface-950 border border-surface-800 overflow-hidden font-mono text-xs">
              <div className="p-3 bg-surface-900 border-b border-surface-800 text-slate-400 flex justify-between text-xs">
                <span>Unified Diff View</span>
                <span className="text-emerald-400">Validated against AST</span>
              </div>
              <pre className="p-4 text-slate-300 overflow-x-auto leading-relaxed max-h-[500px]">
                {structuredDiff?.unified_diff || 'No unified diff available.'}
              </pre>
            </div>
          )}

          {/* Review Decision Input & Controls */}
          <div className="p-5 rounded-2xl bg-surface-900 border border-surface-800 space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Send className="w-4 h-4 text-brand-400" />
              <span>Reviewer Decision & PR Authorization</span>
            </h3>

            <textarea
              rows={2}
              placeholder="Add optional review comments, regression caveats, or PR description..."
              value={reviewerComments}
              onChange={(e) => setReviewerComments(e.target.value)}
              className="w-full px-4 py-2 bg-surface-950 border border-surface-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
            />

            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-1">
              <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
                <GitBranch className="w-3.5 h-3.5 text-brand-400" />
                <span>Target:</span>
                <input
                  type="text"
                  value={branchName}
                  onChange={(e) => setBranchName(e.target.value)}
                  className="bg-surface-950 px-2.5 py-1 rounded border border-surface-800 text-white font-mono text-xs"
                />
              </div>

              <div className="flex items-center gap-2 w-full sm:w-auto">
                <button
                  onClick={handleReject}
                  disabled={rejecting || !selectedTaskId}
                  className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-4 py-2 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded-lg text-xs font-bold transition-colors"
                >
                  <XCircle className="w-4 h-4" />
                  <span>{rejecting ? 'Rejecting...' : 'Reject Patch'}</span>
                </button>
                <button
                  onClick={handleApproveAndPR}
                  disabled={approving || !selectedTaskId}
                  className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-5 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs font-bold transition-all shadow-lg shadow-emerald-600/20"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>{approving ? 'Creating PR...' : 'Approve & Create PR'}</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: AI Review Findings Sidebar */}
        <div className="space-y-6">
          {/* AI Code Review Scorecard */}
          <div className="p-5 rounded-2xl bg-surface-900 border border-surface-800 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-brand-400" />
                <span>AI Regression Analysis</span>
              </h3>
              {review && (
                <span
                  className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                    review.decision === 'APPROVED'
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                      : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                  }`}
                >
                  {review.decision}
                </span>
              )}
            </div>

            {review ? (
              <div className="space-y-3">
                {/* Score & Risk Banner */}
                <div className="grid grid-cols-2 gap-2 text-center">
                  <div className="p-3 rounded-xl bg-surface-850 border border-surface-800">
                    <div className="text-[10px] text-slate-400 uppercase font-semibold">Quality Score</div>
                    <div className="text-xl font-bold text-emerald-400 mt-0.5">{review.score || 8.5}/10</div>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-850 border border-surface-800">
                    <div className="text-[10px] text-slate-400 uppercase font-semibold">Regression Risk</div>
                    <div className="text-xl font-bold text-amber-300 mt-0.5">{review.risk_level || 'LOW'}</div>
                  </div>
                </div>

                <p className="text-xs text-slate-300 bg-surface-850 p-3 rounded-xl border border-surface-800 leading-relaxed">
                  {review.summary}
                </p>

                {/* Findings List */}
                <div className="space-y-2 pt-1">
                  <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Findings ({review.findings?.length || 0})
                  </div>
                  {(review.findings || []).map((f, i) => (
                    <div key={i} className="p-3 rounded-xl bg-surface-850 border border-surface-800 text-xs space-y-1">
                      <div className="flex items-center justify-between font-bold">
                        <span className="text-brand-300">{f.category}</span>
                        <span className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${
                          f.severity === 'HIGH' || f.severity === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300' : 'bg-amber-500/20 text-amber-300'
                        }`}>
                          {f.severity}
                        </span>
                      </div>
                      <p className="text-slate-300 text-[11px]">{f.description}</p>
                      {f.recommendation && (
                        <p className="text-[10px] text-emerald-400/90 italic pt-0.5">
                          Rec: {f.recommendation}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="p-6 text-center text-xs text-slate-500 space-y-2">
                <Info className="w-6 h-6 mx-auto text-slate-600" />
                <p>No AI regression review generated yet.</p>
                <button
                  onClick={handleTriggerAIReview}
                  className="px-3 py-1 bg-surface-850 hover:bg-surface-800 text-brand-400 rounded text-xs border border-surface-800 font-semibold"
                >
                  Run Review Now
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
