import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import api from '../services/api';
import {
  Cpu,
  Play,
  RotateCcw,
  CheckCircle2,
  Clock,
  Terminal,
  FileCode,
  Check,
  X,
  ChevronRight,
  ShieldCheck,
  AlertCircle,
  GitBranch,
  Layers,
  StopCircle,
  ThumbsUp,
  ThumbsDown,
  Bookmark
} from 'lucide-react';

export default function AgentWorkspacePage() {
  const [searchParams] = useSearchParams();
  const taskId = searchParams.get('taskId');
  const [tasks, setTasks] = useState([]);
  const [currentTask, setCurrentTask] = useState(null);
  const [logs, setLogs] = useState([]);
  const [diff, setDiff] = useState(null);
  const [tests, setTests] = useState(null);
  const [workflowState, setWorkflowState] = useState(null);
  const [checkpoints, setCheckpoints] = useState([]);
  const [loading, setLoading] = useState(true);

  const [runningTests, setRunningTests] = useState(false);
  const [runningRepair, setRunningRepair] = useState(false);
  const [runningOrchestration, setRunningOrchestration] = useState(false);
  const [humanFeedback, setHumanFeedback] = useState('');
  const [submittingApproval, setSubmittingApproval] = useState(false);

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const res = await api.get('/tasks');
        setTasks(res.data);
        if (res.data.length > 0) {
          const selected = taskId ? res.data.find((t) => t.id === taskId) || res.data[0] : res.data[0];
          setCurrentTask(selected);
          loadTaskArtifacts(selected.id);
        }
      } catch (err) {
        console.error('Failed to load tasks', err);
      } finally {
        setLoading(false);
      }
    };
    fetchTasks();
  }, [taskId]);

  const loadTaskArtifacts = async (id) => {
    try {
      const [logsRes, diffRes, testsRes, stateRes, cpRes] = await Promise.all([
        api.get(`/tasks/${id}/logs`).catch(() => ({ data: { logs: [] } })),
        api.get(`/tasks/${id}/diff`).catch(() => ({ data: null })),
        api.get(`/tasks/${id}/tests`).catch(() => ({ data: null })),
        api.get(`/tasks/${id}/workflow-state`).catch(() => ({ data: null })),
        api.get(`/tasks/${id}/checkpoints`).catch(() => ({ data: { checkpoints: [] } }))
      ]);
      setLogs(logsRes.data.logs || []);
      setDiff(diffRes.data);
      setTests(testsRes.data);
      setWorkflowState(stateRes.data);
      setCheckpoints(cpRes.data.checkpoints || []);
    } catch (err) {
      console.error('Failed to load artifacts', err);
    }
  };

  const handleRunTests = async () => {
    if (!currentTask) return;
    setRunningTests(true);
    try {
      await api.post(`/tasks/${currentTask.id}/run-tests`);
      await loadTaskArtifacts(currentTask.id);
      alert('Sandbox tests completed!');
    } catch (err) {
      alert('Test execution failed');
    } finally {
      setRunningTests(false);
    }
  };

  const handleTriggerRepair = async () => {
    if (!currentTask) return;
    setRunningRepair(true);
    try {
      const res = await api.post(`/tasks/${currentTask.id}/repair?max_attempts=3`);
      await loadTaskArtifacts(currentTask.id);
      alert(`Bounded repair loop completed (${res.data.status}) using ${res.data.attempts_used} attempts.`);
    } catch (err) {
      alert('Repair loop failed');
    } finally {
      setRunningRepair(false);
    }
  };

  const handleRunOrchestration = async () => {
    if (!currentTask) return;
    setRunningOrchestration(true);
    try {
      const res = await api.post(`/tasks/${currentTask.id}/orchestrate`, {
        human_approval_required: true,
        max_repair_attempts: 3
      });
      setWorkflowState(res.data);
      await loadTaskArtifacts(currentTask.id);
      const taskRes = await api.get(`/tasks/${currentTask.id}`);
      setCurrentTask(taskRes.data);
    } catch (err) {
      alert('LangGraph orchestration failed to run: ' + (err.response?.data?.detail || err.message));
    } finally {
      setRunningOrchestration(false);
    }
  };

  const handleHumanApproval = async (approved) => {
    if (!currentTask) return;
    setSubmittingApproval(true);
    try {
      const res = await api.post(`/tasks/${currentTask.id}/resume`, {
        approved,
        feedback: humanFeedback || (approved ? 'Approved by human reviewer' : 'Rejected by human reviewer')
      });
      setWorkflowState(res.data);
      setHumanFeedback('');
      await loadTaskArtifacts(currentTask.id);
      const taskRes = await api.get(`/tasks/${currentTask.id}`);
      setCurrentTask(taskRes.data);
    } catch (err) {
      alert('Failed to submit approval: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSubmittingApproval(false);
    }
  };

  const handleCancelWorkflow = async () => {
    if (!currentTask) return;
    try {
      await api.post(`/tasks/${currentTask.id}/cancel`);
      await loadTaskArtifacts(currentTask.id);
      const taskRes = await api.get(`/tasks/${currentTask.id}`);
      setCurrentTask(taskRes.data);
    } catch (err) {
      alert('Failed to cancel workflow');
    }
  };

  const handleStartTask = async () => {
    if (!currentTask) return;
    try {
      const res = await api.post(`/tasks/${currentTask.id}/start`);
      setCurrentTask(res.data);
      loadTaskArtifacts(currentTask.id);
    } catch (err) {
      alert('Failed to start task');
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Task Header */}
      <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-brand-500/10 text-brand-400 border border-brand-500/20">
              {currentTask?.task_type || 'TASK'}
            </span>
            <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full ${
              currentTask?.status === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
              currentTask?.status === 'RUNNING' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse' :
              'bg-slate-800 text-slate-300'
            }`}>
              {currentTask?.status || 'PENDING'}
            </span>
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">{currentTask?.title || 'Autonomous Agent Execution'}</h1>
          <p className="text-xs text-slate-400 max-w-3xl">{currentTask?.instruction}</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRunOrchestration}
            disabled={runningOrchestration || !currentTask}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-brand-600 to-purple-600 hover:from-brand-500 hover:to-purple-500 disabled:opacity-50 text-white rounded-lg text-sm font-semibold transition-all shadow-lg shadow-brand-500/10"
            title="Execute complete LangGraph StateGraph pipeline with conditional routing"
          >
            <GitBranch className="w-4 h-4" />
            <span>{runningOrchestration ? 'Orchestrating...' : 'Run LangGraph Pipeline'}</span>
          </button>

          {(currentTask?.status === 'RUNNING' || currentTask?.status === 'WAITING_FOR_APPROVAL') && (
            <button
              onClick={handleCancelWorkflow}
              className="flex items-center gap-2 px-3 py-2 bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30 rounded-lg text-sm font-semibold transition-colors"
              title="Cancel running workflow"
            >
              <StopCircle className="w-4 h-4" />
              <span>Cancel</span>
            </button>
          )}

          {currentTask?.status === 'PENDING' && (
            <button
              onClick={handleStartTask}
              className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-sm font-semibold transition-colors"
            >
              <Play className="w-4 h-4 fill-white" />
              <span>Start Execution</span>
            </button>
          )}
          <Link
            to="/review"
            className="flex items-center gap-2 px-4 py-2 bg-surface-850 hover:bg-surface-800 border border-surface-800 text-slate-300 rounded-lg text-sm font-semibold transition-colors"
          >
            <span>Review Diff</span>
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Human-in-the-Loop Interrupt Approval Banner */}
      {(currentTask?.status === 'WAITING_FOR_APPROVAL' || workflowState?.status === 'WAITING_FOR_APPROVAL') && (
        <div className="p-6 rounded-2xl bg-amber-500/10 border border-amber-500/30 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400">
                <AlertCircle className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-amber-200">Human-in-the-Loop Approval Required</h2>
                <p className="text-xs text-amber-300/80">
                  LangGraph paused at human approval gate. Tests passed in sandbox. Please review changes before finalizing PR.
                </p>
              </div>
            </div>
            <span className="text-xs font-mono font-bold px-3 py-1 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse">
              INTERRUPT PAUSED
            </span>
          </div>

          <div className="flex flex-col md:flex-row gap-3 pt-2">
            <input
              type="text"
              placeholder="Optional reviewer notes or instructions for repair..."
              value={humanFeedback}
              onChange={(e) => setHumanFeedback(e.target.value)}
              className="flex-1 px-4 py-2 bg-surface-950 border border-amber-500/30 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-400"
            />
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleHumanApproval(true)}
                disabled={submittingApproval}
                className="flex items-center gap-2 px-5 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-emerald-500/20"
              >
                <ThumbsUp className="w-3.5 h-3.5" />
                <span>Approve & Complete</span>
              </button>
              <button
                onClick={() => handleHumanApproval(false)}
                disabled={submittingApproval}
                className="flex items-center gap-2 px-4 py-2 bg-rose-600/80 hover:bg-rose-600 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition-colors"
              >
                <ThumbsDown className="w-3.5 h-3.5" />
                <span>Reject</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* LangGraph Node Stepper */}
      <div className="p-4 rounded-2xl bg-surface-900 border border-surface-800">
        <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <Layers className="w-3.5 h-3.5 text-brand-400" />
          <span>Multi-Agent StateGraph Pipeline</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2">
          {[
            { id: 'planning', label: '1. Planning', agent: 'Planning Agent' },
            { id: 'bug_detection', label: '2. Bug Scan', agent: 'Bug Detector' },
            { id: 'coding', label: '3. Patch Gen', agent: 'Coding Agent' },
            { id: 'validation', label: '4. AST Check', agent: 'Validator' },
            { id: 'testing', label: '5. Sandbox Test', agent: 'Test Runner' },
            { id: 'human_approval', label: '6. Review Gate', agent: 'Human HITL' },
            { id: 'completion', label: '7. Complete', agent: 'Finalizer' }
          ].map((n) => {
            const isCurrent = workflowState?.current_node === n.id;
            const isDone = workflowState?.messages?.some((m) => m.node === n.id);
            return (
              <div
                key={n.id}
                className={`p-2.5 rounded-xl border text-xs transition-all ${
                  isCurrent
                    ? 'bg-brand-500/20 border-brand-500 text-white shadow-md shadow-brand-500/10'
                    : isDone
                    ? 'bg-surface-850 border-emerald-500/30 text-emerald-300'
                    : 'bg-surface-850/50 border-surface-800 text-slate-500'
                }`}
              >
                <div className="font-semibold flex items-center justify-between">
                  <span>{n.label}</span>
                  {isDone && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">{n.agent}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Execution Plan & Agent Timeline */}
        <div className="space-y-6">
          <div className="p-5 rounded-2xl bg-surface-900 border border-surface-800 space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Cpu className="w-4 h-4 text-brand-400" />
              <span>LangGraph Execution Plan</span>
            </h3>
            <div className="space-y-3">
              {(currentTask?.execution_plan || []).map((step) => (
                <div key={step.step} className="p-3 rounded-xl bg-surface-850 border border-surface-800/80 flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-brand-500/20 text-brand-400 font-mono text-xs flex items-center justify-center shrink-0">
                    {step.step}
                  </div>
                  <div className="text-xs space-y-0.5">
                    <div className="font-bold text-slate-200">{step.agent}</div>
                    <div className="text-slate-400">{step.description}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Sandbox Test Results & Repair Trigger */}
          <div className="p-5 rounded-2xl bg-surface-900 border border-surface-800 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Sandbox Test Verification</span>
              </h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleRunTests}
                  disabled={runningTests || !currentTask}
                  className="px-2.5 py-1 bg-surface-850 hover:bg-surface-800 disabled:opacity-50 text-slate-300 rounded text-xs border border-surface-800"
                >
                  {runningTests ? 'Running...' : 'Run Tests'}
                </button>
                <button
                  onClick={handleTriggerRepair}
                  disabled={runningRepair || !currentTask}
                  className="px-2.5 py-1 bg-purple-600/80 hover:bg-purple-600 disabled:opacity-50 text-white rounded text-xs font-semibold"
                  title="Bounded repair loop (max 3 attempts)"
                >
                  {runningRepair ? 'Repairing...' : 'Repair (Max 3)'}
                </button>
              </div>
            </div>

            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {(tests?.test_results || []).map((tr, idx) => (
                <div key={idx} className="p-3 rounded-xl bg-surface-850 border border-surface-800 text-xs space-y-1.5">
                  <div className="flex justify-between items-center text-slate-300">
                    <span className="font-semibold text-white">Attempt #{tr.attempt_number || idx + 1}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                        (tr.failed === 0 && tr.exit_code === 0)
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}
                    >
                      {tr.failed === 0 && tr.exit_code === 0 ? 'PASSED' : 'FAILED'}
                    </span>
                  </div>
                  <div className="flex justify-between text-slate-400 text-[11px] font-mono">
                    <span>Passed: {tr.passed || 0} | Failed: {tr.failed || 0}</span>
                    <span>Exit: {tr.exit_code}</span>
                  </div>

                  {/* Failure Details if any */}
                  {tr.failure_details && tr.failure_details.length > 0 && (
                    <div className="mt-1 pt-1 border-t border-surface-800 text-[11px] space-y-1">
                      {tr.failure_details.map((fd, fIdx) => (
                        <div key={fIdx} className="text-rose-300">
                          <span className="font-mono font-bold">{fd.failure_type}:</span> {fd.test_name}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* LangGraph Checkpoints History */}
          <div className="p-5 rounded-2xl bg-surface-900 border border-surface-800 space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Bookmark className="w-4 h-4 text-brand-400" />
              <span>StateGraph Checkpoints</span>
            </h3>
            <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
              {checkpoints.length === 0 ? (
                <div className="text-xs text-slate-500 italic">No checkpoints recorded yet.</div>
              ) : (
                checkpoints.map((cp, idx) => (
                  <div key={idx} className="p-2.5 rounded-xl bg-surface-850 border border-surface-800 flex items-center justify-between text-xs">
                    <div className="space-y-0.5">
                      <span className="font-semibold text-slate-200">{cp.node_name}</span>
                      <div className="text-[10px] text-slate-400 font-mono">#{cp.step_number} • {cp.checkpoint_id}</div>
                    </div>
                    <span className="text-[10px] text-slate-500 font-mono">{cp.created_at?.slice(11, 19)}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right 2 Columns: Live Agent Console & Patches */}
        <div className="lg:col-span-2 space-y-6">
          {/* Real-time Agent Log Stream */}
          <div className="p-5 rounded-2xl bg-surface-900 border border-surface-800 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Terminal className="w-4 h-4 text-emerald-400" />
                <span>Agent Execution Timeline & Tool Calls</span>
              </h3>
              <span className="text-[10px] bg-surface-800 text-slate-400 px-2 py-0.5 rounded font-mono">
                LIVE
              </span>
            </div>
            <div className="bg-surface-950 p-4 rounded-xl border border-surface-800 font-mono text-xs space-y-2 max-h-[300px] overflow-y-auto">
              {logs.map((log, i) => (
                <div key={i} className="flex items-start gap-2 text-slate-300">
                  <span className="text-slate-500 shrink-0">[{log.timestamp.slice(11, 19)}]</span>
                  <span className="text-brand-400 font-semibold shrink-0">&lt;{log.agent}&gt;</span>
                  <span>{log.message}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Generated Patch Preview */}
          <div className="p-5 rounded-2xl bg-surface-900 border border-surface-800 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <FileCode className="w-4 h-4 text-purple-400" />
                <span>Generated Unified Diff Patch</span>
              </h3>
              <span className="text-[11px] text-brand-400 font-mono">
                {diff?.patches?.[0]?.file_path || 'backend/app/core/security.py'}
              </span>
            </div>
            <pre className="p-4 rounded-xl bg-surface-950 text-xs font-mono text-emerald-300 border border-surface-800 overflow-x-auto">
              {diff?.patches?.[0]?.unified_diff || 'No diff generated yet.'}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
