"""
Context Retriever Service
Provides LLM-ready context retrieval for AI agents with token budgeting,
symbol re-ranking, and Recall@K / MRR benchmark evaluation.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.services.search import search_service, SearchResultItem


@dataclass
class RetrievedSnippet:
    file_path: str
    symbol_name: str
    start_line: int
    end_line: int
    content: str
    score: float
    token_count: int
    formatted_context: str


@dataclass
class RetrievalResponse:
    query: str
    total_retrieved: int
    total_tokens: int
    snippets: List[RetrievedSnippet]
    llm_context_prompt: str


class ContextRetriever:
    """Manages token budgeting and context preparation for LLM agents."""

    def __init__(self, max_context_tokens: int = 4000):
        self.max_context_tokens = max_context_tokens

    def retrieve_context(
        self,
        db: Session,
        repository_id: str,
        query: str,
        top_k: int = 5,
        search_type: str = "hybrid"
    ) -> RetrievalResponse:
        """
        Retrieves top relevant code chunks, applies reranking, formats for LLMs,
        and enforces strict token budgeting so the context window is never overloaded.
        """
        results = search_service.search(
            db=db,
            repository_id=repository_id,
            query=query,
            search_type=search_type,
            limit=top_k * 2
        )

        # Re-rank: boost if query terms appear in symbol name or file path
        q_lower = query.lower()
        scored_items = []
        for r in results:
            boost = 1.0
            if r.symbol_name.lower() in q_lower or q_lower in r.symbol_name.lower():
                boost += 0.25
            if any(term in r.file_path.lower() for term in q_lower.split()):
                boost += 0.15
            final_score = round(min(r.similarity_score * boost, 1.0), 4)
            scored_items.append((final_score, r))

        scored_items.sort(key=lambda x: x[0], reverse=True)

        snippets: List[RetrievedSnippet] = []
        current_tokens = 0
        formatted_blocks = []

        for score, item in scored_items:
            token_est = max(len(item.content) // 4, 1)
            if current_tokens + token_est > self.max_context_tokens:
                continue

            block = (
                f"### [Snippet {len(snippets) + 1}] Source: {item.file_path} (Lines {item.start_line}-{item.end_line})\n"
                f"### Symbol: {item.symbol_name} ({item.chunk_type}) | Relevance Score: {score:.2f}\n"
                f"```\n{item.content}\n```"
            )
            formatted_blocks.append(block)

            snippets.append(RetrievedSnippet(
                file_path=item.file_path,
                symbol_name=item.symbol_name,
                start_line=item.start_line,
                end_line=item.end_line,
                content=item.content,
                score=score,
                token_count=token_est,
                formatted_context=block
            ))
            current_tokens += token_est

            if len(snippets) >= top_k:
                break

        llm_context = "\n\n".join(formatted_blocks)
        return RetrievalResponse(
            query=query,
            total_retrieved=len(snippets),
            total_tokens=current_tokens,
            snippets=snippets,
            llm_context_prompt=llm_context
        )

    def evaluate_retrieval(
        self,
        db: Session,
        repository_id: str,
        benchmark_cases: List[Dict[str, Any]],
        k: int = 5
    ) -> Dict[str, float]:
        """
        Evaluates retrieval performance across Recall@K, Precision@K, and MRR.
        benchmark_cases format:
        [{"query": "create access token", "expected_files": ["security.py"], "expected_symbols": ["create_access_token"]}]
        """
        if not benchmark_cases:
            return {"recall_at_k": 1.0, "precision_at_k": 1.0, "mrr": 1.0}

        total_recall = 0.0
        total_precision = 0.0
        total_mrr = 0.0

        for case in benchmark_cases:
            query = case["query"]
            expected_files = case.get("expected_files", [])
            expected_symbols = case.get("expected_symbols", [])

            res = self.retrieve_context(db, repository_id, query, top_k=k)
            retrieved = res.snippets

            hits = 0
            first_hit_rank = 0

            for rank, s in enumerate(retrieved, 1):
                match = (
                    any(ef.lower() in s.file_path.lower() for ef in expected_files) or
                    any(es.lower() == s.symbol_name.lower() for es in expected_symbols)
                )
                if match:
                    hits += 1
                    if first_hit_rank == 0:
                        first_hit_rank = rank

            # Recall@K (did we find at least one expected snippet?)
            case_recall = 1.0 if hits > 0 else 0.0
            total_recall += case_recall

            # Precision@K
            case_precision = hits / max(len(retrieved), 1)
            total_precision += case_precision

            # MRR
            mrr = 1.0 / first_hit_rank if first_hit_rank > 0 else 0.0
            total_mrr += mrr

        n = len(benchmark_cases)
        return {
            f"recall_at_{k}": round(total_recall / n, 4),
            f"precision_at_{k}": round(total_precision / n, 4),
            "mean_reciprocal_rank": round(total_mrr / n, 4)
        }


context_retriever = ContextRetriever()
