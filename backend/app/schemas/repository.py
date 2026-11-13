"""Repository Schemas."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl


class RepositoryConnect(BaseModel):
    github_repo_url: str
    access_token: Optional[str] = None


class RepositoryResponse(BaseModel):
    id: str
    name: str
    full_name: str
    html_url: str
    clone_url: str
    default_branch: str
    description: Optional[str] = None
    primary_language: Optional[str] = None
    detected_frameworks: List[str] = []
    is_indexed: bool = False
    last_indexed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FileTreeNode(BaseModel):
    name: str
    path: str
    type: str  # "file" or "directory"
    size: Optional[int] = None
    language: Optional[str] = None
    children: Optional[List["FileTreeNode"]] = None


class CodeSearchRequest(BaseModel):
    query: str
    limit: int = 10
    search_type: str = "hybrid"  # keyword, semantic, hybrid


class CodeSearchResult(BaseModel):
    file_path: str
    symbol_name: Optional[str] = None
    chunk_type: str
    start_line: int
    end_line: int
    content: str
    similarity_score: float
    search_strategy: Optional[str] = "hybrid"


class ContextSnippet(BaseModel):
    file_path: str
    symbol_name: str
    start_line: int
    end_line: int
    content: str
    score: float
    token_count: int
    formatted_context: str


class ContextRetrievalRequest(BaseModel):
    query: str
    top_k: int = 5
    search_type: str = "hybrid"  # keyword, semantic, hybrid


class ContextRetrievalResponse(BaseModel):
    query: str
    total_retrieved: int
    total_tokens: int
    snippets: List[ContextSnippet]
    llm_context_prompt: str


class RetrievalBenchmarkCase(BaseModel):
    query: str
    expected_files: List[str] = []
    expected_symbols: List[str] = []


class RetrievalEvaluationRequest(BaseModel):
    benchmark_cases: List[RetrievalBenchmarkCase]
    k: int = 5


class RetrievalEvaluationResponse(BaseModel):
    recall_at_5: Optional[float] = None
    precision_at_5: Optional[float] = None
    mean_reciprocal_rank: float
    metrics: Dict[str, float] = {}

