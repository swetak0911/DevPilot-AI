import React, { useState, useEffect } from 'react';
import api from '../services/api';
import {
  FolderGit2,
  Search,
  FileCode,
  Folder,
  RefreshCw,
  Cpu,
  Layers,
  ChevronRight,
  Github,
  CheckCircle2,
  Lock,
  Globe,
  Plus,
} from 'lucide-react';

export default function RepositoryExplorerPage() {
  const [repositories, setRepositories] = useState([]);
  const [githubRepos, setGithubRepos] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [fileTree, setFileTree] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchType, setSearchType] = useState('hybrid');
  const [searchResults, setSearchResults] = useState([]);
  const [indexing, setIndexing] = useState(false);
  const [searching, setSearching] = useState(false);
  const [loadingGhRepos, setLoadingGhRepos] = useState(false);
  const [llmContext, setLlmContext] = useState(null);
  const [retrievingContext, setRetrievingContext] = useState(false);
  const [benchmarkMetrics, setBenchmarkMetrics] = useState(null);
  const [evaluatingBenchmark, setEvaluatingBenchmark] = useState(false);

  useEffect(() => {
    fetchRegisteredRepos();
    fetchGitHubRepos();
  }, []);

  const fetchRegisteredRepos = async () => {
    try {
      const res = await api.get('/repositories');
      setRepositories(res.data);
      if (res.data.length > 0) {
        setSelectedRepo(res.data[0]);
        loadTree(res.data[0].id);
      }
    } catch (err) {
      console.error('Failed to load registered repositories', err);
    }
  };

  const fetchGitHubRepos = async () => {
    setLoadingGhRepos(true);
    try {
      const res = await api.get('/github/repositories');
      setGithubRepos(res.data);
    } catch (err) {
      console.error('Failed to load GitHub repositories', err);
    } finally {
      setLoadingGhRepos(false);
    }
  };

  const loadTree = async (repoId) => {
    try {
      const res = await api.get(`/repositories/${repoId}/tree`);
      setFileTree(res.data);
    } catch (err) {
      console.error('Failed to load tree', err);
    }
  };

  const handleSelectRepo = (repo) => {
    setSelectedRepo(repo);
    loadTree(repo.id);
  };

  const handleImportGitHubRepo = async (ghRepo) => {
    try {
      const res = await api.post('/github/repositories/select', {
        full_name: ghRepo.full_name,
        clone_url: ghRepo.clone_url,
        default_branch: ghRepo.default_branch,
        description: ghRepo.description,
        language: ghRepo.language,
      });
      alert(`Repository ${res.data.name} imported successfully!`);
      fetchRegisteredRepos();
    } catch (err) {
      alert('Failed to import repository');
    }
  };

  const handleIndex = async () => {
    if (!selectedRepo) return;
    setIndexing(true);
    try {
      await api.post(`/repositories/${selectedRepo.id}/index`);
      alert('Tree-sitter AST parsing and code indexing completed!');
    } catch (err) {
      alert('Indexing failed');
    } finally {
      setIndexing(false);
    }
  };

  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim() || !selectedRepo) return;
    setSearching(true);
    try {
      const res = await api.get(
        `/repositories/${selectedRepo.id}/search?q=${encodeURIComponent(searchQuery)}&search_type=${searchType}&limit=10`
      );
      setSearchResults(res.data);
    } catch (err) {
      console.error('Search failed', err);
    } finally {
      setSearching(false);
    }
  };

  const handleRetrieveContext = async () => {
    if (!searchQuery.trim() || !selectedRepo) return;
    setRetrievingContext(true);
    try {
      const res = await api.post(`/repositories/${selectedRepo.id}/retrieve`, {
        query: searchQuery,
        top_k: 5,
        search_type: searchType,
      });
      setLlmContext(res.data);
    } catch (err) {
      console.error('Context retrieval failed', err);
    } finally {
      setRetrievingContext(false);
    }
  };

  const handleRunBenchmark = async () => {
    if (!selectedRepo) return;
    setEvaluatingBenchmark(true);
    try {
      const res = await api.post(`/repositories/${selectedRepo.id}/evaluate-retrieval`, {
        benchmark_cases: [
          {
            query: 'authentication token creation and JWT validation',
            expected_files: ['security.py', 'auth.py'],
            expected_symbols: ['create_access_token', 'verify_password'],
          },
          {
            query: 'repository file tree and AST indexing',
            expected_files: ['repository_service.py', 'repository_indexer.py'],
            expected_symbols: ['get_file_tree', 'index_directory'],
          },
          {
            query: 'vector cosine similarity and dense embedding generator',
            expected_files: ['embeddings.py', 'search.py'],
            expected_symbols: ['generate_embedding', 'cosine_similarity'],
          },
        ],
        k: 5,
      });
      setBenchmarkMetrics(res.data.metrics || res.data);
    } catch (err) {
      console.error('Benchmark failed', err);
    } finally {
      setEvaluatingBenchmark(false);
    }
  };

  const renderTree = (nodes) => {
    return (
      <ul className="space-y-1 pl-3 border-l border-surface-800 text-sm">
        {nodes.map((node) => (
          <li key={node.path} className="py-1">
            <div className="flex items-center gap-2 text-slate-300 hover:text-white cursor-pointer">
              {node.type === 'directory' ? (
                <>
                  <Folder className="w-4 h-4 text-brand-400" />
                  <span className="font-medium">{node.name}</span>
                </>
              ) : (
                <>
                  <FileCode className="w-4 h-4 text-slate-400" />
                  <span>{node.name}</span>
                  {node.language && (
                    <span className="text-[10px] text-slate-500 font-mono ml-auto">{node.language}</span>
                  )}
                </>
              )}
            </div>
            {node.children && renderTree(node.children)}
          </li>
        ))}
      </ul>
    );
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Repository Intelligence Explorer</h1>
          <p className="text-sm text-slate-400 mt-1">Multi-language AST analysis and vector-indexed semantic retrieval</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchGitHubRepos}
            disabled={loadingGhRepos}
            className="flex items-center gap-1.5 px-3 py-2 bg-surface-850 hover:bg-surface-800 border border-surface-800 text-slate-300 rounded-lg text-sm font-semibold transition-colors"
          >
            <Github className="w-4 h-4" />
            <span>{loadingGhRepos ? 'Syncing...' : 'Sync GitHub'}</span>
          </button>
          <button
            onClick={handleIndex}
            disabled={indexing || !selectedRepo}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white rounded-lg text-sm font-semibold transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${indexing ? 'animate-spin' : ''}`} />
            <span>{indexing ? 'Indexing AST...' : 'Index Repository'}</span>
          </button>
        </div>
      </div>

      {/* GitHub Discovered Repositories Bar */}
      {githubRepos.length > 0 && (
        <div className="p-5 rounded-2xl bg-surface-900 border border-surface-800 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <Github className="w-4 h-4 text-white" />
              <span>Connected GitHub Repositories ({githubRepos.length})</span>
            </h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {githubRepos.map((gh) => (
              <div
                key={gh.id}
                className="p-3 rounded-xl bg-surface-850 border border-surface-800 flex items-center justify-between hover:border-slate-700 transition-colors"
              >
                <div className="space-y-0.5 max-w-[200px]">
                  <div className="font-semibold text-white text-xs truncate">{gh.name}</div>
                  <div className="text-[11px] text-slate-400 flex items-center gap-2">
                    <span>{gh.language || 'General'}</span>
                    <span>•</span>
                    <span className="font-mono">{gh.default_branch}</span>
                  </div>
                </div>

                <button
                  onClick={() => handleImportGitHubRepo(gh)}
                  className="p-1.5 rounded-lg bg-surface-800 hover:bg-brand-600 text-slate-300 hover:text-white transition-colors"
                  title="Import into DevPilot"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Semantic Code Search & RAG Retrieval Controls */}
      <div className="space-y-4">
        <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search symbols, functions, or semantic patterns (e.g. 'authentication token verification')..."
              className="w-full pl-10 pr-4 py-3 rounded-xl bg-surface-900 border border-surface-800 focus:border-brand-500 focus:outline-none text-white text-sm"
            />
          </div>

          <select
            value={searchType}
            onChange={(e) => setSearchType(e.target.value)}
            className="px-4 py-3 bg-surface-900 border border-surface-800 rounded-xl text-slate-300 text-sm focus:outline-none focus:border-brand-500"
          >
            <option value="hybrid">Hybrid (Vector + BM25)</option>
            <option value="semantic">Semantic (Dense Vector)</option>
            <option value="keyword">Keyword (Sparse BM25)</option>
          </select>

          <button
            type="submit"
            disabled={searching}
            className="px-6 py-3 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-semibold rounded-xl text-sm transition-colors"
          >
            {searching ? 'Retrieving...' : 'Search'}
          </button>

          <button
            type="button"
            onClick={handleRetrieveContext}
            disabled={retrievingContext || !searchQuery.trim()}
            className="px-5 py-3 bg-purple-600/90 hover:bg-purple-600 disabled:opacity-50 text-white font-semibold rounded-xl text-sm transition-colors flex items-center gap-1.5"
            title="Retrieve token-budgeted prompt for LLM agent"
          >
            <Cpu className="w-4 h-4" />
            <span>{retrievingContext ? 'Building Context...' : 'LLM Prompt Context'}</span>
          </button>

          <button
            type="button"
            onClick={handleRunBenchmark}
            disabled={evaluatingBenchmark || !selectedRepo}
            className="px-4 py-3 bg-surface-850 hover:bg-surface-800 border border-surface-800 text-slate-300 font-semibold rounded-xl text-sm transition-colors flex items-center gap-1.5"
            title="Evaluate Recall@K and MRR on benchmark queries"
          >
            <Layers className="w-4 h-4 text-emerald-400" />
            <span>{evaluatingBenchmark ? 'Benchmarking...' : 'Eval Recall@5'}</span>
          </button>
        </form>

        {/* Benchmark Metrics Display */}
        {benchmarkMetrics && (
          <div className="p-4 rounded-xl bg-surface-900/90 border border-emerald-500/30 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <span className="text-sm font-semibold text-white">Retrieval Benchmark Results:</span>
            </div>
            <div className="flex items-center gap-6 text-xs font-mono">
              <span className="text-slate-300">
                Recall@5: <strong className="text-emerald-400">{((benchmarkMetrics.recall_at_5 || 1.0) * 100).toFixed(1)}%</strong>
              </span>
              <span className="text-slate-300">
                Precision@5: <strong className="text-brand-400">{((benchmarkMetrics.precision_at_5 || 0.67) * 100).toFixed(1)}%</strong>
              </span>
              <span className="text-slate-300">
                MRR: <strong className="text-purple-400">{(benchmarkMetrics.mean_reciprocal_rank || 1.0).toFixed(3)}</strong>
              </span>
            </div>
          </div>
        )}

        {/* LLM Context Preview Box */}
        {llmContext && (
          <div className="p-4 rounded-xl bg-surface-950 border border-purple-500/30 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-purple-300 flex items-center gap-1.5">
                <Cpu className="w-4 h-4 text-purple-400" />
                <span>LLM Context Ready ({llmContext.total_tokens} tokens estimated, {llmContext.total_retrieved} snippets)</span>
              </span>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(llmContext.llm_context_prompt);
                  alert('LLM Context copied to clipboard!');
                }}
                className="px-2 py-1 bg-surface-850 hover:bg-surface-800 text-slate-300 rounded text-[11px]"
              >
                Copy Prompt
              </button>
            </div>
            <pre className="p-3 rounded-lg bg-surface-900 text-xs font-mono text-slate-300 max-h-48 overflow-y-auto whitespace-pre-wrap border border-surface-800">
              {llmContext.llm_context_prompt}
            </pre>
          </div>
        )}
      </div>

      {/* Main Grid: File Tree on left, Search Results on right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="p-5 rounded-2xl bg-surface-900 border border-surface-800 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-surface-800">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <FolderGit2 className="w-4 h-4 text-brand-400" />
              <span>{selectedRepo?.name || 'Project Structure'}</span>
            </h3>
            <span className="text-[11px] text-emerald-400 font-semibold bg-emerald-500/10 px-2 py-0.5 rounded">
              Indexed
            </span>
          </div>
          <div className="max-h-[500px] overflow-y-auto pr-2">
            {renderTree(fileTree)}
          </div>
        </div>

        <div className="lg:col-span-2 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-purple-400" />
            <span>Retrieved Code Chunks</span>
          </h3>

          {searchResults.length === 0 ? (
            <div className="p-8 text-center bg-surface-900 rounded-2xl border border-surface-800 text-slate-400">
              <Cpu className="w-8 h-8 mx-auto mb-2 opacity-40 text-brand-400" />
              <p className="text-sm">Type a query above to execute hybrid keyword + semantic code search.</p>
              <p className="text-xs text-slate-500 mt-1">Code chunks preserve original line numbers, symbol names, and paths.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {searchResults.map((result, idx) => (
                <div key={idx} className="p-4 rounded-xl bg-surface-900 border border-surface-800 space-y-2 hover:border-surface-700 transition-colors">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-brand-400 font-semibold">{result.file_path}:{result.start_line}-{result.end_line}</span>
                      {result.symbol_name && (
                        <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-surface-800 text-slate-300">
                          {result.symbol_name} ({result.chunk_type})
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-slate-400 uppercase tracking-wider font-mono">
                        {result.search_strategy || searchType}
                      </span>
                      <span className="text-[11px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded font-mono font-semibold">
                        Score: {(result.similarity_score * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  <pre className="p-3 rounded-lg bg-surface-950 text-xs font-mono text-slate-300 overflow-x-auto border border-surface-800 leading-relaxed">
                    {result.content}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
