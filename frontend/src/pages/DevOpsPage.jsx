import React, { useState, useEffect } from 'react';
import api from '../services/api';
import {
  Workflow,
  CheckCircle2,
  XCircle,
  Clock,
  Cpu,
  Layers,
  FileCode,
  AlertTriangle,
  Play,
  RotateCcw,
  GitBranch,
  GitCommit,
  UploadCloud,
  ShieldCheck,
  Terminal,
  Check,
  Copy,
  Sparkles,
  RefreshCw,
  Box,
  Server,
  CheckSquare,
  Sliders,
  ShieldAlert,
  Info,
  Database,
  Cloud,
  Lock,
  Flame,
  CheckCheck
} from 'lucide-react';

export default function DevOpsPage() {
  const [activeTab, setActiveTab] = useState('cicd'); // 'cicd' | 'docker' | 'k8s' | 'terraform'

  // CI/CD Runs & Analysis state
  const [runs, setRuns] = useState([]);
  const [selectedRun, setSelectedRun] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [remediating, setRemediating] = useState(false);
  const [remediationResult, setRemediationResult] = useState(null);

  // Framework detection state
  const [detecting, setDetecting] = useState(false);
  const [frameworkReport, setFrameworkReport] = useState(null);

  // Workflow synthesis options
  const [workflowName, setWorkflowName] = useState('DevPilot Continuous Integration');
  const [branches, setBranches] = useState('main, develop');
  const [includeLinting, setIncludeLinting] = useState(true);
  const [includeTests, setIncludeTests] = useState(true);
  const [includeMatrix, setIncludeMatrix] = useState(false);
  const [includeDocker, setIncludeDocker] = useState(false);
  const [includePostgres, setIncludePostgres] = useState(false);
  const [includeRedis, setIncludeRedis] = useState(false);

  // YAML Editor & Validator state
  const [generating, setGenerating] = useState(false);
  const [workflowYaml, setWorkflowYaml] = useState('');
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [commitBranch, setCommitBranch] = useState('devpilot/setup-cicd');
  const [committing, setCommitting] = useState(false);
  const [commitStatus, setCommitStatus] = useState(null);
  const [copied, setCopied] = useState(false);
  const [triggering, setTriggering] = useState(false);

  // Phase 12: Docker State
  const [dockerLang, setDockerLang] = useState('python');
  const [dockerPort, setDockerPort] = useState(8000);
  const [dockerMultiStage, setDockerMultiStage] = useState(true);
  const [dockerNonRoot, setDockerNonRoot] = useState(true);
  const [dockerHealthcheck, setDockerHealthcheck] = useState(true);
  const [dockerBaseImage, setDockerBaseImage] = useState('');
  const [dockerGenerating, setDockerGenerating] = useState(false);
  const [dockerfileContent, setDockerfileContent] = useState('');
  const [dockerignoreContent, setDockerignoreContent] = useState('');
  const [dockerActiveFileTab, setDockerActiveFileTab] = useState('dockerfile');
  const [dockerValidation, setDockerValidation] = useState(null);
  const [dockerOptimization, setDockerOptimization] = useState(null);
  const [dockerCommitting, setDockerCommitting] = useState(false);
  const [dockerCommitStatus, setDockerCommitStatus] = useState(null);
  const [dockerCopied, setDockerCopied] = useState(false);

  // Phase 13: Kubernetes State
  const [k8sAppName, setK8sAppName] = useState('devpilot-api');
  const [k8sNamespace, setK8sNamespace] = useState('default');
  const [k8sReplicas, setK8sReplicas] = useState(2);
  const [k8sPort, setK8sPort] = useState(8000);
  const [k8sServiceType, setK8sServiceType] = useState('ClusterIP');
  const [k8sEnableHpa, setK8sEnableHpa] = useState(true);
  const [k8sEnableIngress, setK8sEnableIngress] = useState(true);
  const [k8sGenerating, setK8sGenerating] = useState(false);
  const [k8sManifests, setK8sManifests] = useState(null);
  const [k8sActiveDocTab, setK8sActiveDocTab] = useState('all');
  const [k8sValidation, setK8sValidation] = useState(null);
  const [k8sCommitting, setK8sCommitting] = useState(false);
  const [k8sCommitStatus, setK8sCommitStatus] = useState(null);

  // Phase 13: Terraform State
  const defaultTfCode = `resource "aws_security_group" "app_sg" {
  name        = "app-sg"
  description = "Application Ingress Security Group"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Environment = "production"
    ManagedBy   = "devpilot"
  }
}

resource "aws_s3_bucket" "app_assets" {
  bucket = "devpilot-app-assets"
  acl    = "private"

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  tags = {
    Environment = "production"
  }
}
`;
  const [tfContent, setTfContent] = useState(defaultTfCode);
  const [tfAnalysis, setTfAnalysis] = useState(null);
  const [tfAnalyzing, setTfAnalyzing] = useState(false);
  const [tfFormatting, setTfFormatting] = useState(false);
  const [tfPlanText, setTfPlanText] = useState(
    'Plan: 2 to add, 1 to change, 1 to destroy.\n# aws_db_instance.main_db will be destroyed\n# aws_security_group.app_sg will be updated in-place\n# aws_s3_bucket.app_assets will be created\n# aws_ecs_service.api will be created'
  );
  const [tfPlanResult, setTfPlanResult] = useState(null);
  const [tfApprovalDecision, setTfApprovalDecision] = useState(null);

  // Load initial runs and auto-detect framework
  useEffect(() => {
    fetchRuns();
    handleDetectFramework();
  }, []);

  const fetchRuns = async () => {
    try {
      const res = await api.get('/cicd/runs');
      setRuns(res.data);
      if (res.data.length > 0) {
        setSelectedRun(res.data[0]);
      }
    } catch (err) {
      console.error('Failed to load CI runs', err);
    }
  };

  const handleDetectFramework = async () => {
    setDetecting(true);
    try {
      const res = await api.post('/cicd/detect-framework/default-repo');
      setFrameworkReport(res.data);
      if (res.data.has_docker) {
        setIncludeDocker(true);
      }
      if (res.data.primary_language) {
        const lang = res.data.primary_language.toLowerCase();
        setDockerLang(lang);
        const p = (lang === 'nodejs' || lang === 'javascript' || lang === 'typescript') ? 3000 : 8000;
        setDockerPort(p);
        setK8sPort(p);
      }
    } catch (err) {
      console.error('Failed to detect framework', err);
    } finally {
      setDetecting(false);
    }
  };

  const handleGenerateWorkflow = async () => {
    setGenerating(true);
    setCommitStatus(null);
    try {
      const services = [];
      if (includePostgres) services.push('postgres');
      if (includeRedis) services.push('redis');

      const branchList = branches.split(',').map((b) => b.trim()).filter(Boolean);

      const res = await api.post('/cicd/generate', {
        repository_id: 'default-repo',
        workflow_name: workflowName,
        branches: branchList.length > 0 ? branchList : ['main', 'develop'],
        include_linting: includeLinting,
        include_tests: includeTests,
        include_matrix: includeMatrix,
        include_docker: includeDocker,
        include_services: services,
      });

      setWorkflowYaml(res.data.workflow_yaml);
      setValidationResult({
        is_valid: res.data.validation_status === 'VALID',
        errors: res.data.validation_errors || [],
        warnings: res.data.warnings || [],
        lint_issues: [],
      });
    } catch (err) {
      alert('Failed to generate workflow');
    } finally {
      setGenerating(false);
    }
  };

  const handleValidateYaml = async () => {
    if (!workflowYaml) return;
    setValidating(true);
    try {
      const res = await api.post('/cicd/validate-workflow', {
        workflow_yaml: workflowYaml,
      });
      setValidationResult(res.data);
    } catch (err) {
      alert('Validation request failed');
    } finally {
      setValidating(false);
    }
  };

  const handleCommitWorkflow = async () => {
    if (!workflowYaml) return;
    setCommitting(true);
    setCommitStatus(null);
    try {
      const res = await api.post('/cicd/commit-workflow', {
        repository_id: 'default-repo',
        workflow_yaml: workflowYaml,
        file_path: '.github/workflows/ci.yml',
        branch_name: commitBranch || 'devpilot/setup-cicd',
        commit_message: 'ci: configure automated GitHub Actions pipeline with DevPilot AI',
      });
      setCommitStatus(res.data);
    } catch (err) {
      alert('Failed to commit workflow file');
    } finally {
      setCommitting(false);
    }
  };

  const handleTriggerRun = async () => {
    setTriggering(true);
    try {
      const res = await api.post('/cicd/trigger-run/default-repo', {
        repository_id: 'default-repo',
        workflow_name: workflowName,
        branch_name: commitBranch || 'main',
      });
      setRuns((prev) => [res.data, ...prev]);
      setSelectedRun(res.data);
    } catch (err) {
      alert('Failed to dispatch workflow run');
    } finally {
      setTriggering(false);
    }
  };

  const handleAnalyseFailure = async (runId) => {
    setAnalyzing(true);
    setRemediationResult(null);
    try {
      const res = await api.post(`/cicd/runs/${runId}/analyse`);
      setAnalysis(res.data);
    } catch (err) {
      alert('Failure analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleRemediateFailure = async (runId) => {
    if (!analysis?.recommended_patch) return;
    setRemediating(true);
    setRemediationResult(null);
    try {
      const res = await api.post(`/cicd/runs/${runId}/remediate`, {
        run_id: runId,
        patch: analysis.recommended_patch,
      });
      setRemediationResult(res.data);
    } catch (err) {
      alert('Remediation patch application failed');
    } finally {
      setRemediating(false);
    }
  };

  // Phase 12: Docker Handlers
  const handleGenerateDocker = async () => {
    setDockerGenerating(true);
    setDockerCommitStatus(null);
    try {
      const res = await api.post('/docker/generate', {
        language: dockerLang,
        port: parseInt(dockerPort, 10) || 8000,
        multi_stage: dockerMultiStage,
        non_root: dockerNonRoot,
        healthcheck: dockerHealthcheck,
        base_image: dockerBaseImage.trim() || null,
        repository_id: 'default-repo',
      });

      setDockerfileContent(res.data.dockerfile_content);
      setDockerignoreContent(res.data.dockerignore_content);
      setDockerValidation(res.data.validation);

      const optRes = await api.post('/docker/optimize', {
        language: dockerLang,
        base_image: res.data.base_image,
        multi_stage: dockerMultiStage,
        port: parseInt(dockerPort, 10) || 8000,
      });
      setDockerOptimization(optRes.data);
    } catch (err) {
      alert('Failed to synthesize Docker assets');
    } finally {
      setDockerGenerating(false);
    }
  };

  const handleCommitDocker = async () => {
    if (!dockerfileContent) return;
    setDockerCommitting(true);
    setDockerCommitStatus(null);
    try {
      const res = await api.post('/docker/commit', {
        repository_id: 'default-repo',
        branch_name: 'devpilot/dockerize',
        dockerfile_content: dockerfileContent,
        dockerignore_content: dockerignoreContent,
        commit_message: 'chore(docker): configure hardened multi-stage Dockerfile and .dockerignore',
      });
      setDockerCommitStatus(res.data);
    } catch (err) {
      alert('Failed to commit Docker artifacts');
    } finally {
      setDockerCommitting(false);
    }
  };

  // Phase 13: Kubernetes Handlers
  const handleGenerateK8s = async () => {
    setK8sGenerating(true);
    setK8sCommitStatus(null);
    try {
      const res = await api.post('/kubernetes/generate', {
        app_name: k8sAppName,
        namespace: k8sNamespace,
        replicas: parseInt(k8sReplicas, 10) || 2,
        container_port: parseInt(k8sPort, 10) || 8000,
        service_type: k8sServiceType,
        enable_hpa: k8sEnableHpa,
        enable_ingress: k8sEnableIngress,
      });

      setK8sManifests(res.data);
      setK8sValidation(res.data.validation);
    } catch (err) {
      alert('Failed to synthesize Kubernetes manifests');
    } finally {
      setK8sGenerating(false);
    }
  };

  const handleCommitK8s = async () => {
    if (!k8sManifests) return;
    setK8sCommitting(true);
    try {
      const res = await api.post('/kubernetes/commit', {
        repository_id: 'default-repo',
        branch_name: 'devpilot/k8s-manifests',
        manifest_yaml: k8sManifests.all_manifests_combined,
        commit_message: `chore(k8s): configure production manifests for ${k8sAppName}`,
      });
      setK8sCommitStatus(res.data);
    } catch (err) {
      alert('Failed to commit Kubernetes manifests');
    } finally {
      setK8sCommitting(false);
    }
  };

  // Phase 13: Terraform Handlers
  const handleFormatTf = async () => {
    if (!tfContent) return;
    setTfFormatting(true);
    try {
      const res = await api.post('/terraform/fmt', {
        hcl_content: tfContent,
      });
      setTfContent(res.data.formatted_content);
    } catch (err) {
      alert('Terraform formatting failed');
    } finally {
      setTfFormatting(false);
    }
  };

  const handleAnalyseTf = async () => {
    setTfAnalyzing(true);
    try {
      const res = await api.post('/terraform/analyse', {
        hcl_content: tfContent,
      });
      setTfAnalysis(res.data);
    } catch (err) {
      alert('Terraform security analysis failed');
    } finally {
      setTfAnalyzing(false);
    }
  };

  const handleEvaluatePlan = async () => {
    try {
      const res = await api.post('/terraform/plan', {
        plan_text: tfPlanText,
      });
      setTfPlanResult(res.data);
      setTfApprovalDecision(null);
    } catch (err) {
      alert('Plan evaluation failed');
    }
  };

  const handleApprovePlan = async (approved) => {
    if (!tfPlanResult?.approval_token) return;
    try {
      const res = await api.post('/terraform/approve', {
        approval_token: tfPlanResult.approval_token,
        approved: approved,
        approver: 'admin-developer',
        comment: approved ? 'Approved destructive infrastructure modification.' : 'Rejected by safety policy.',
      });
      setTfApprovalDecision(res.data);
    } catch (err) {
      alert('Plan approval submission failed');
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Page Title & Navigation Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-500/10 border border-brand-500/30 flex items-center justify-center text-brand-400">
            {activeTab === 'cicd' && <Workflow className="w-5 h-5" />}
            {activeTab === 'docker' && <Box className="w-5 h-5" />}
            {activeTab === 'k8s' && <Layers className="w-5 h-5" />}
            {activeTab === 'terraform' && <Cloud className="w-5 h-5" />}
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Intelligent DevOps & Cloud Engine</h1>
            <p className="text-sm text-slate-400">Continuous Integration, Docker Hardening, Kubernetes Manifests & Terraform IaC</p>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex flex-wrap items-center p-1 bg-surface-900 border border-surface-800 rounded-xl">
          <button
            onClick={() => setActiveTab('cicd')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'cicd' ? 'bg-brand-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Workflow className="w-3.5 h-3.5" />
            <span>CI/CD</span>
          </button>
          <button
            onClick={() => {
              setActiveTab('docker');
              if (!dockerfileContent) handleGenerateDocker();
            }}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'docker' ? 'bg-brand-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Box className="w-3.5 h-3.5" />
            <span>Docker</span>
          </button>
          <button
            onClick={() => {
              setActiveTab('k8s');
              if (!k8sManifests) handleGenerateK8s();
            }}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'k8s' ? 'bg-brand-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Kubernetes</span>
          </button>
          <button
            onClick={() => {
              setActiveTab('terraform');
              if (!tfAnalysis) handleAnalyseTf();
            }}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'terraform' ? 'bg-brand-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Cloud className="w-3.5 h-3.5" />
            <span>Terraform IaC</span>
          </button>
        </div>
      </div>

      {/* =========================================================================
          TAB 1: CI/CD Pipelines & Failure Intelligence
          ========================================================================= */}
      {activeTab === 'cicd' && (
        <div className="space-y-8">
          <div className="flex items-center justify-between p-4 rounded-xl bg-surface-900/60 border border-surface-800">
            <div className="flex items-center gap-3 text-xs text-slate-300">
              <span className="font-semibold text-white">Repository:</span> default-repo
              <span className="text-slate-600">|</span>
              <span className="font-semibold text-white">Detected:</span> {frameworkReport ? `${frameworkReport.primary_language} (${frameworkReport.build_tool})` : 'Scanning...'}
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={handleDetectFramework}
                disabled={detecting}
                className="flex items-center gap-2 px-3 py-1.5 bg-surface-800 hover:bg-surface-700 text-slate-200 border border-surface-700 rounded-lg text-xs font-semibold transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${detecting ? 'animate-spin' : ''}`} />
                <span>{detecting ? 'Inspecting...' : 'Re-scan Toolchain'}</span>
              </button>
              <button
                onClick={handleGenerateWorkflow}
                disabled={generating}
                className="flex items-center gap-2 px-4 py-1.5 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-md shadow-brand-500/20 transition-colors"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{generating ? 'Synthesizing...' : 'Synthesize Workflow'}</span>
              </button>
            </div>
          </div>

          {frameworkReport && (
            <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-white flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-brand-400" />
                  <span>Detected Repository Architecture & Toolchains</span>
                </h2>
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-medium">
                  Discovery Active
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                <div className="p-3 rounded-xl bg-surface-950/60 border border-surface-800">
                  <div className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Language</div>
                  <div className="text-sm font-bold text-white mt-1 capitalize">{frameworkReport.primary_language}</div>
                </div>
                <div className="p-3 rounded-xl bg-surface-950/60 border border-surface-800">
                  <div className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Build Tool</div>
                  <div className="text-sm font-bold text-white mt-1">{frameworkReport.build_tool}</div>
                </div>
                <div className="p-3 rounded-xl bg-surface-950/60 border border-surface-800">
                  <div className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Test Suite</div>
                  <div className="text-sm font-bold text-white mt-1">{frameworkReport.test_runner}</div>
                </div>
                <div className="p-3 rounded-xl bg-surface-950/60 border border-surface-800">
                  <div className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Linter</div>
                  <div className="text-sm font-bold text-white mt-1">{frameworkReport.linter || 'None detected'}</div>
                </div>
                <div className="p-3 rounded-xl bg-surface-950/60 border border-surface-800">
                  <div className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Container</div>
                  <div className="text-sm font-bold text-emerald-400 mt-1">{frameworkReport.has_docker ? 'Dockerfile Present' : 'None'}</div>
                </div>
                <div className="p-3 rounded-xl bg-surface-950/60 border border-surface-800">
                  <div className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Frameworks</div>
                  <div className="text-xs font-semibold text-slate-300 mt-1 truncate">
                    {frameworkReport.detected_frameworks?.join(', ') || 'Standard library'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Workflow Generator & Editor */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-5">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Sliders className="w-4 h-4 text-brand-400" />
                <span>Workflow Pipeline Generator</span>
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-slate-400 block mb-1.5">Workflow Name</label>
                  <input
                    type="text"
                    value={workflowName}
                    onChange={(e) => setWorkflowName(e.target.value)}
                    className="w-full px-3 py-2 bg-surface-950 border border-surface-700 rounded-lg text-xs text-white focus:outline-none focus:border-brand-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-medium text-slate-400 block mb-1.5">Trigger Branches</label>
                  <input
                    type="text"
                    value={branches}
                    onChange={(e) => setBranches(e.target.value)}
                    className="w-full px-3 py-2 bg-surface-950 border border-surface-700 rounded-lg text-xs text-white focus:outline-none focus:border-brand-500"
                  />
                </div>

                <div className="space-y-2.5 pt-2 border-t border-surface-800">
                  <div className="text-xs font-semibold text-slate-300 mb-2">Build & Test Jobs</div>
                  <label className="flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeLinting}
                      onChange={(e) => setIncludeLinting(e.target.checked)}
                      className="rounded border-surface-700 bg-surface-950 text-brand-500 focus:ring-0"
                    />
                    <span>Run Linting & Static Code Quality Checks</span>
                  </label>

                  <label className="flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeTests}
                      onChange={(e) => setIncludeTests(e.target.checked)}
                      className="rounded border-surface-700 bg-surface-950 text-brand-500 focus:ring-0"
                    />
                    <span>Run Automated Unit & Integration Tests</span>
                  </label>

                  <label className="flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeMatrix}
                      onChange={(e) => setIncludeMatrix(e.target.checked)}
                      className="rounded border-surface-700 bg-surface-950 text-brand-500 focus:ring-0"
                    />
                    <span>Enable Multi-Version Matrix Builds</span>
                  </label>

                  <label className="flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeDocker}
                      onChange={(e) => setIncludeDocker(e.target.checked)}
                      className="rounded border-surface-700 bg-surface-950 text-brand-500 focus:ring-0"
                    />
                    <span>Build & Validate Docker Image</span>
                  </label>
                </div>
              </div>
            </div>

            <div className="lg:col-span-2 p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-4 flex flex-col justify-between">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileCode className="w-4 h-4 text-brand-400" />
                    <h2 className="text-sm font-bold text-white">.github/workflows/ci.yml</h2>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleValidateYaml}
                      disabled={validating || !workflowYaml}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-800 hover:bg-surface-700 text-slate-200 border border-surface-700 rounded-lg text-xs font-semibold transition-colors"
                    >
                      <ShieldCheck className="w-3.5 h-3.5 text-brand-400" />
                      <span>{validating ? 'Linting...' : 'Validate YAML'}</span>
                    </button>
                    <button
                      onClick={() => {
                        if (workflowYaml) {
                          navigator.clipboard.writeText(workflowYaml);
                          setCopied(true);
                          setTimeout(() => setCopied(false), 2000);
                        }
                      }}
                      disabled={!workflowYaml}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-800 hover:bg-surface-700 text-slate-200 border border-surface-700 rounded-lg text-xs font-semibold transition-colors"
                    >
                      {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copied ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                </div>

                <textarea
                  rows={16}
                  value={workflowYaml}
                  onChange={(e) => setWorkflowYaml(e.target.value)}
                  placeholder="# Click 'Synthesize Workflow' above to generate production GitHub Actions pipeline..."
                  className="w-full p-4 rounded-xl bg-surface-950 font-mono text-xs text-slate-200 border border-surface-800 focus:outline-none focus:border-brand-500 leading-relaxed resize-y"
                />

                {validationResult && (
                  <div className={`p-3.5 rounded-xl border text-xs space-y-2 ${validationResult.is_valid ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-rose-500/10 border-rose-500/30 text-rose-300'}`}>
                    <div className="flex items-center justify-between font-semibold">
                      <span className="flex items-center gap-2">
                        {validationResult.is_valid ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <XCircle className="w-4 h-4 text-rose-400" />}
                        <span>{validationResult.is_valid ? 'Workflow Syntax Valid & Compliant' : 'Workflow Schema Errors Detected'}</span>
                      </span>
                    </div>
                  </div>
                )}
              </div>

              <div className="pt-4 border-t border-surface-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <GitBranch className="w-4 h-4 text-slate-400" />
                  <input
                    type="text"
                    value={commitBranch}
                    onChange={(e) => setCommitBranch(e.target.value)}
                    placeholder="Branch"
                    className="px-3 py-1.5 bg-surface-950 border border-surface-700 rounded-lg text-xs text-white focus:outline-none focus:border-brand-500"
                  />
                  <button
                    onClick={handleCommitWorkflow}
                    disabled={committing || !workflowYaml}
                    className="flex items-center gap-1.5 px-4 py-1.5 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-md transition-colors"
                  >
                    <GitCommit className="w-3.5 h-3.5" />
                    <span>{committing ? 'Committing...' : 'Commit Workflow'}</span>
                  </button>
                </div>

                <button
                  onClick={handleTriggerRun}
                  disabled={triggering}
                  className="flex items-center gap-1.5 px-4 py-1.5 bg-surface-800 hover:bg-surface-700 disabled:opacity-50 text-slate-200 border border-surface-700 rounded-lg text-xs font-semibold transition-colors"
                >
                  <Play className="w-3.5 h-3.5 text-emerald-400" />
                  <span>{triggering ? 'Dispatching...' : 'Trigger Workflow Run'}</span>
                </button>
              </div>
            </div>
          </div>

          {/* Execution History */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-4">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Clock className="w-4 h-4 text-brand-400" />
                <span>Workflow Execution History</span>
              </h2>
              <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
                {runs.map((run) => (
                  <button
                    key={run.id}
                    onClick={() => {
                      setSelectedRun(run);
                      setAnalysis(null);
                      setRemediationResult(null);
                    }}
                    className={`w-full p-3 rounded-xl border text-left transition-all ${selectedRun?.id === run.id ? 'bg-surface-800 border-brand-500/40' : 'bg-surface-950/60 border-surface-800/80 hover:bg-surface-800/40'}`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white truncate max-w-[180px]">{run.workflow_name}</span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${run.conclusion === 'success' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'}`}>
                        {run.conclusion || run.status}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="lg:col-span-2 p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-4">
              {selectedRun ? (
                <>
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-base font-bold text-white">{selectedRun.workflow_name}</h3>
                      <p className="text-xs text-slate-400">Run ID: {selectedRun.id}</p>
                    </div>
                    {selectedRun.conclusion === 'failure' && (
                      <button
                        onClick={() => handleAnalyseFailure(selectedRun.id)}
                        disabled={analyzing}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold shadow-md transition-colors"
                      >
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>{analyzing ? 'Diagnosing...' : 'Diagnose Failure'}</span>
                      </button>
                    )}
                  </div>

                  <div className="p-4 rounded-xl bg-surface-950 border border-surface-800 text-xs font-mono text-slate-300">
                    {selectedRun.logs_summary || 'Logs summary...'}
                  </div>

                  {analysis && (
                    <div className="p-4 rounded-xl bg-surface-950 border border-surface-800 space-y-3 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white uppercase">{analysis.failure_category}</span>
                        <span className="text-emerald-400 font-bold">{Math.round(analysis.confidence_score * 100)}% Confidence</span>
                      </div>
                      <div className="text-slate-300"><strong>Hypothesis:</strong> {analysis.root_cause_hypothesis}</div>
                      <div className="text-emerald-300"><strong>Fix:</strong> {analysis.suggested_fix}</div>
                    </div>
                  )}
                </>
              ) : (
                <div className="p-8 text-center text-slate-500 text-xs">Select a workflow run.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          TAB 2: Docker Automation (Phase 12)
          ========================================================================= */}
      {activeTab === 'docker' && (
        <div className="space-y-8">
          <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-white flex items-center gap-2">
                  <Box className="w-4 h-4 text-brand-400" />
                  <span>Multi-Stage Dockerfile Synthesizer & Hardening Engine</span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">Generates minimal runtimes, non-root user execution, and security linting.</p>
              </div>
              <button
                onClick={handleGenerateDocker}
                disabled={dockerGenerating}
                className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-md transition-colors"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{dockerGenerating ? 'Synthesizing...' : 'Synthesize Container Assets'}</span>
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-surface-800">
              <div>
                <label className="text-[11px] font-semibold text-slate-400 block mb-1">Language</label>
                <select
                  value={dockerLang}
                  onChange={(e) => setDockerLang(e.target.value)}
                  className="w-full px-3 py-1.5 bg-surface-950 border border-surface-700 rounded-lg text-xs text-white"
                >
                  <option value="python">Python</option>
                  <option value="nodejs">Node.js / TypeScript</option>
                  <option value="go">Go</option>
                  <option value="rust">Rust</option>
                  <option value="java">Java</option>
                </select>
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-400 block mb-1">Port</label>
                <input
                  type="number"
                  value={dockerPort}
                  onChange={(e) => setDockerPort(e.target.value)}
                  className="w-full px-3 py-1.5 bg-surface-950 border border-surface-700 rounded-lg text-xs text-white"
                />
              </div>
              <div className="flex items-center gap-4 pt-5 col-span-2">
                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={dockerMultiStage}
                    onChange={(e) => setDockerMultiStage(e.target.checked)}
                    className="rounded border-surface-700 bg-surface-950 text-brand-500"
                  />
                  <span>Multi-Stage</span>
                </label>
                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={dockerNonRoot}
                    onChange={(e) => setDockerNonRoot(e.target.checked)}
                    className="rounded border-surface-700 bg-surface-950 text-brand-500"
                  />
                  <span>Non-Root (UID 10001)</span>
                </label>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1 p-1 bg-surface-950 rounded-lg border border-surface-800">
                  <button
                    onClick={() => setDockerActiveFileTab('dockerfile')}
                    className={`px-3 py-1 rounded-md text-xs font-semibold ${dockerActiveFileTab === 'dockerfile' ? 'bg-surface-800 text-white' : 'text-slate-400'}`}
                  >
                    Dockerfile
                  </button>
                  <button
                    onClick={() => setDockerActiveFileTab('dockerignore')}
                    className={`px-3 py-1 rounded-md text-xs font-semibold ${dockerActiveFileTab === 'dockerignore' ? 'bg-surface-800 text-white' : 'text-slate-400'}`}
                  >
                    .dockerignore
                  </button>
                  <button
                    onClick={() => setDockerActiveFileTab('buildx')}
                    className={`px-3 py-1 rounded-md text-xs font-semibold ${dockerActiveFileTab === 'buildx' ? 'bg-surface-800 text-white' : 'text-slate-400'}`}
                  >
                    Buildx (Multi-Arch)
                  </button>
                </div>
                <button
                  onClick={handleCommitDocker}
                  disabled={dockerCommitting || !dockerfileContent}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold"
                >
                  <GitCommit className="w-3.5 h-3.5" />
                  <span>{dockerCommitting ? 'Committing...' : 'Commit Assets'}</span>
                </button>
              </div>

              <textarea
                rows={16}
                value={dockerActiveFileTab === 'dockerfile' ? dockerfileContent : dockerignoreContent}
                onChange={(e) => {
                  if (dockerActiveFileTab === 'dockerfile') setDockerfileContent(e.target.value);
                  else setDockerignoreContent(e.target.value);
                }}
                className="w-full p-4 rounded-xl bg-surface-950 font-mono text-xs text-slate-200 border border-surface-800 leading-relaxed resize-y"
              />

              {dockerCommitStatus && (
                <div className="p-3 rounded-xl bg-surface-950 border border-emerald-500/30 text-xs text-emerald-300">
                  Committed to branch <strong>{dockerCommitStatus.branch_name}</strong> ({dockerCommitStatus.commit_hash})
                </div>
              )}
            </div>

            <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-4">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-brand-400" />
                <span>Container Security Linter</span>
              </h3>
              {dockerValidation ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 rounded-xl bg-surface-950 border border-surface-800">
                    <span className="text-xs text-slate-400">Security Score</span>
                    <span className="text-sm font-bold text-emerald-400">{dockerValidation.security_score}/100</span>
                  </div>
                  <div className="space-y-2 max-h-[300px] overflow-y-auto">
                    {dockerValidation.issues?.map((iss, i) => (
                      <div key={i} className="p-2.5 rounded-lg border border-surface-800 bg-surface-950 text-xs space-y-1">
                        <div className="font-bold text-slate-200">{iss.code}: {iss.message}</div>
                        <div className="text-[10px] text-slate-400 italic">💡 {iss.suggestion}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-xs text-slate-500">Synthesize container assets to view security findings.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          TAB 3: Kubernetes Automation (Phase 13)
          ========================================================================= */}
      {activeTab === 'k8s' && (
        <div className="space-y-8">
          <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-white flex items-center gap-2">
                  <Layers className="w-4 h-4 text-brand-400" />
                  <span>Kubernetes Production Manifest Generator & PSS Validator</span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Deployment, ClusterIP Service, ConfigMap, HPA, and Ingress with Pod Security Standards (Restricted).
                </p>
              </div>

              <button
                onClick={handleGenerateK8s}
                disabled={k8sGenerating}
                className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-md transition-colors"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{k8sGenerating ? 'Synthesizing...' : 'Synthesize K8s Manifests'}</span>
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-surface-800">
              <div>
                <label className="text-[11px] font-semibold text-slate-400 block mb-1">Application Name</label>
                <input
                  type="text"
                  value={k8sAppName}
                  onChange={(e) => setK8sAppName(e.target.value)}
                  className="w-full px-3 py-1.5 bg-surface-950 border border-surface-700 rounded-lg text-xs text-white"
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-400 block mb-1">Namespace</label>
                <input
                  type="text"
                  value={k8sNamespace}
                  onChange={(e) => setK8sNamespace(e.target.value)}
                  className="w-full px-3 py-1.5 bg-surface-950 border border-surface-700 rounded-lg text-xs text-white"
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-400 block mb-1">Replicas</label>
                <input
                  type="number"
                  value={k8sReplicas}
                  onChange={(e) => setK8sReplicas(e.target.value)}
                  className="w-full px-3 py-1.5 bg-surface-950 border border-surface-700 rounded-lg text-xs text-white"
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-400 block mb-1">Container Port</label>
                <input
                  type="number"
                  value={k8sPort}
                  onChange={(e) => setK8sPort(e.target.value)}
                  className="w-full px-3 py-1.5 bg-surface-950 border border-surface-700 rounded-lg text-xs text-white"
                />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1 p-1 bg-surface-950 rounded-lg border border-surface-800">
                  <button
                    onClick={() => setK8sActiveDocTab('all')}
                    className={`px-3 py-1 rounded-md text-xs font-semibold ${k8sActiveDocTab === 'all' ? 'bg-surface-800 text-white' : 'text-slate-400'}`}
                  >
                    All Manifests
                  </button>
                  <button
                    onClick={() => setK8sActiveDocTab('deployment')}
                    className={`px-3 py-1 rounded-md text-xs font-semibold ${k8sActiveDocTab === 'deployment' ? 'bg-surface-800 text-white' : 'text-slate-400'}`}
                  >
                    Deployment
                  </button>
                  <button
                    onClick={() => setK8sActiveDocTab('service')}
                    className={`px-3 py-1 rounded-md text-xs font-semibold ${k8sActiveDocTab === 'service' ? 'bg-surface-800 text-white' : 'text-slate-400'}`}
                  >
                    Service
                  </button>
                  <button
                    onClick={() => setK8sActiveDocTab('hpa')}
                    className={`px-3 py-1 rounded-md text-xs font-semibold ${k8sActiveDocTab === 'hpa' ? 'bg-surface-800 text-white' : 'text-slate-400'}`}
                  >
                    HPA
                  </button>
                </div>
                <button
                  onClick={handleCommitK8s}
                  disabled={k8sCommitting || !k8sManifests}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold"
                >
                  <GitCommit className="w-3.5 h-3.5" />
                  <span>{k8sCommitting ? 'Committing...' : 'Commit Manifests'}</span>
                </button>
              </div>

              <textarea
                rows={18}
                value={
                  k8sManifests
                    ? k8sActiveDocTab === 'deployment'
                      ? k8sManifests.deployment_yaml
                      : k8sActiveDocTab === 'service'
                      ? k8sManifests.service_yaml
                      : k8sActiveDocTab === 'hpa'
                      ? k8sManifests.hpa_yaml || '# HPA not enabled'
                      : k8sManifests.all_manifests_combined
                    : '# Synthesize Kubernetes manifests to preview YAML...'
                }
                readOnly
                className="w-full p-4 rounded-xl bg-surface-950 font-mono text-xs text-slate-200 border border-surface-800 leading-relaxed resize-y"
              />

              {k8sCommitStatus && (
                <div className="p-3 rounded-xl bg-surface-950 border border-emerald-500/30 text-xs text-emerald-300">
                  Committed to branch <strong>{k8sCommitStatus.branch_name}</strong> ({k8sCommitStatus.commit_hash})
                </div>
              )}
            </div>

            <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-4">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-brand-400" />
                <span>OpenAPI & PSS Compliance</span>
              </h3>
              {k8sValidation ? (
                <div className="space-y-3 text-xs">
                  <div className="flex items-center justify-between p-3 rounded-xl bg-surface-950 border border-surface-800">
                    <span className="text-slate-400">Security Score</span>
                    <span className="text-sm font-bold text-emerald-400">{k8sValidation.security_score}/100</span>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-950 border border-surface-800 space-y-1">
                    <span className="text-slate-400 font-semibold">Resources Generated:</span>
                    <ul className="list-disc pl-4 text-slate-300 space-y-0.5">
                      {k8sValidation.resources_found?.map((r, i) => (
                        <li key={i}>{r.kind}: {r.name}</li>
                      ))}
                    </ul>
                  </div>
                  {k8sValidation.recommendations?.length > 0 && (
                    <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300">
                      {k8sValidation.recommendations[0]}
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-xs text-slate-500">Generate manifests to run compliance analysis.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          TAB 4: Terraform & Cloud IaC (Phase 13)
          ========================================================================= */}
      {activeTab === 'terraform' && (
        <div className="space-y-8">
          <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-white flex items-center gap-2">
                  <Cloud className="w-4 h-4 text-brand-400" />
                  <span>Terraform IaC Security Linter & Plan Approval Gate</span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Static analysis (tfsec/Checkov rules), 'terraform fmt' formatting, and destructive change approval gates.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={handleFormatTf}
                  disabled={tfFormatting}
                  className="flex items-center gap-1.5 px-3.5 py-2 bg-surface-800 hover:bg-surface-700 text-slate-200 border border-surface-700 rounded-lg text-xs font-semibold transition-colors"
                >
                  <FileCode className="w-3.5 h-3.5 text-brand-400" />
                  <span>{tfFormatting ? 'Formatting...' : 'Format (fmt)'}</span>
                </button>
                <button
                  onClick={handleAnalyseTf}
                  disabled={tfAnalyzing}
                  className="flex items-center gap-1.5 px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-semibold shadow-md transition-colors"
                >
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>{tfAnalyzing ? 'Scanning...' : 'Scan IaC Security'}</span>
                </button>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <FileCode className="w-4 h-4 text-brand-400" />
                  <span>main.tf (HCL Editor)</span>
                </h3>
              </div>

              <textarea
                rows={16}
                value={tfContent}
                onChange={(e) => setTfContent(e.target.value)}
                className="w-full p-4 rounded-xl bg-surface-950 font-mono text-xs text-slate-200 border border-surface-800 leading-relaxed resize-y"
              />

              {/* Execution Plan & Approval Gate Card */}
              <div className="p-5 rounded-xl bg-surface-950 border border-surface-800 space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                    <Flame className="w-4 h-4 text-amber-400" />
                    <span>Execution Plan Risk & Human Approval Gate</span>
                  </h4>
                  <button
                    onClick={handleEvaluatePlan}
                    className="px-3 py-1 bg-surface-800 hover:bg-surface-700 text-slate-200 border border-surface-700 rounded-lg text-xs font-semibold"
                  >
                    Analyze Plan
                  </button>
                </div>

                <textarea
                  rows={4}
                  value={tfPlanText}
                  onChange={(e) => setTfPlanText(e.target.value)}
                  className="w-full p-3 rounded-lg bg-surface-900 font-mono text-xs text-slate-300 border border-surface-800 resize-none"
                />

                {tfPlanResult && (
                  <div className="p-4 rounded-xl bg-surface-900 border border-surface-800 space-y-3 text-xs">
                    <div className="flex items-center justify-between font-bold">
                      <span>{tfPlanResult.plan_summary}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${tfPlanResult.destructive_changes ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' : 'bg-emerald-500/20 text-emerald-400'}`}>
                        {tfPlanResult.destructive_changes ? 'DESTRUCTIVE CHANGES DETECTED' : 'SAFE PLAN'}
                      </span>
                    </div>

                    {tfPlanResult.destructive_reasons?.map((reason, i) => (
                      <div key={i} className="text-rose-400 font-medium">⚠️ {reason}</div>
                    ))}

                    <div className="pt-3 border-t border-surface-800 flex items-center justify-between">
                      <span className="text-slate-400">Approval Status: <strong>{tfApprovalDecision?.status || tfPlanResult.approval_status}</strong></span>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleApprovePlan(false)}
                          className="px-3 py-1.5 bg-rose-600/80 hover:bg-rose-600 text-white rounded-lg text-xs font-semibold"
                        >
                          Reject
                        </button>
                        <button
                          onClick={() => handleApprovePlan(true)}
                          className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold shadow-sm"
                        >
                          Approve Infrastructure Apply
                        </button>
                      </div>
                    </div>

                    {tfApprovalDecision && (
                      <div className="p-2.5 rounded bg-surface-950 border border-surface-800 text-[11px] text-slate-300">
                        Decision recorded: <strong>{tfApprovalDecision.status}</strong> by {tfApprovalDecision.approver} ({tfApprovalDecision.comment})
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-4">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-brand-400" />
                <span>IaC Security Findings (tfsec/Checkov)</span>
              </h3>
              {tfAnalysis ? (
                <div className="space-y-3 text-xs">
                  <div className="flex items-center justify-between p-3 rounded-xl bg-surface-950 border border-surface-800">
                    <span className="text-slate-400">Security Score</span>
                    <span className="text-sm font-bold text-emerald-400">{tfAnalysis.security_score}/100</span>
                  </div>
                  <div className="space-y-2 max-h-[360px] overflow-y-auto">
                    {tfAnalysis.findings?.map((f, i) => (
                      <div key={i} className={`p-3 rounded-xl border space-y-1 ${f.severity === 'CRITICAL' ? 'bg-rose-500/10 border-rose-500/30 text-rose-300' : 'bg-surface-950 border-surface-800 text-slate-300'}`}>
                        <div className="flex items-center justify-between font-bold">
                          <span>{f.rule_id}</span>
                          <span className="text-[10px] uppercase">{f.severity}</span>
                        </div>
                        <div className="text-[11px]">{f.message}</div>
                        <div className="text-[10px] text-slate-400 italic">💡 {f.remediation}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-xs text-slate-500">Run security scan to inspect IaC findings.</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
