import React from 'react';
import { Link } from 'react-router-dom';
import { Terminal, Cpu, ShieldCheck, Workflow, GitPullRequest, ArrowRight, CheckCircle2 } from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-surface-950 text-slate-100 flex flex-col">
      {/* Hero Section */}
      <div className="relative overflow-hidden py-24 sm:py-32 px-6 lg:px-8 flex-1 flex flex-col justify-center items-center text-center">
        <div className="absolute inset-0 -z-10 bg-[radial-gradient(45rem_50rem_at_top,theme(colors.indigo.900),theme(colors.surface.950))] opacity-40"></div>
        
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/30 text-brand-300 text-xs font-semibold mb-8">
          <span className="w-2 h-2 rounded-full bg-brand-400 animate-pulse"></span>
          Autonomous Software Engineering & DevOps Intelligence Platform
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight max-w-4xl text-white">
          Ship code faster with <span className="bg-gradient-to-r from-brand-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">Multi-Agent Intelligence</span> & DevOps Automation
        </h1>

        <p className="mt-6 text-lg leading-8 text-slate-300 max-w-2xl">
          DevPilot AI connects to your GitHub repositories, diagnoses issues, runs unit tests in secure Docker sandboxes, repairs code, and generates production-ready CI/CD pipelines.
        </p>

        <div className="mt-10 flex items-center gap-4">
          <Link
            to="/register"
            className="flex items-center gap-2 bg-brand-600 hover:bg-brand-500 text-white font-semibold px-6 py-3 rounded-xl transition-all shadow-lg shadow-brand-500/25 hover:shadow-brand-500/40"
          >
            <span>Launch Workspace</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            to="/dashboard"
            className="px-6 py-3 rounded-xl font-semibold text-slate-300 hover:text-white bg-surface-850 hover:bg-surface-800 border border-surface-800 transition-colors"
          >
            Explore Dashboard
          </Link>
        </div>

        {/* Feature Highlights Grid */}
        <div className="mt-24 grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl text-left">
          <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800/80 hover:border-brand-500/30 transition-all">
            <div className="w-10 h-10 rounded-xl bg-brand-500/20 text-brand-400 flex items-center justify-center mb-4">
              <Cpu className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">LangGraph Multi-Agent Team</h3>
            <p className="text-sm text-slate-400">
              Coordinated specialized agents for Planning, Bug Detection, Patch Generation, Sandboxed Testing, and Code Review.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800/80 hover:border-brand-500/30 transition-all">
            <div className="w-10 h-10 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center mb-4">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Deep Learning Defect Prediction</h3>
            <p className="text-sm text-slate-400">
              CodeBERT-powered vulnerability classification and deployment risk scoring before changes reach production.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800/80 hover:border-brand-500/30 transition-all">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center mb-4">
              <Workflow className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Intelligent CI/CD & DevOps</h3>
            <p className="text-sm text-slate-400">
              Automated GitHub Actions generation, CI failure root cause analysis, Dockerfile optimization, and Kubernetes manifests.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
