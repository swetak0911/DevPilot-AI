"""
Search Service
Executes Keyword (BM25-style), Dense Semantic (Vector Similarity),
and Hybrid (Reciprocal Rank Fusion / Weighted Linear) code retrieval.
"""
import re
import math
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.models.repository import CodeChunk, RepositoryFile
from app.services.embeddings import embedding_service


@dataclass
class SearchResultItem:
    chunk_id: str
    file_path: str
    symbol_name: str
    chunk_type: str
    start_line: int
    end_line: int
    content: str
    similarity_score: float
    search_strategy: str


class SearchService:
    def __init__(self, dense_weight: float = 0.6, sparse_weight: float = 0.4):
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight

    def search(
        self,
        db: Session,
        repository_id: str,
        query: str,
        search_type: str = "hybrid",
        limit: int = 10,
        min_score: float = 0.1
    ) -> List[SearchResultItem]:
        """
        Dispatches search across keyword, semantic, or hybrid strategies.
        """
        if search_type == "keyword":
            return self.keyword_search(db, repository_id, query, limit=limit)
        elif search_type == "semantic":
            return self.semantic_search(db, repository_id, query, limit=limit, min_score=min_score)
        else:
            return self.hybrid_search(db, repository_id, query, limit=limit, min_score=min_score)

    def keyword_search(
        self,
        db: Session,
        repository_id: str,
        query: str,
        limit: int = 10
    ) -> List[SearchResultItem]:
        """BM25-inspired keyword matching across symbol names, content, and file paths."""
        query_terms = [t.lower() for t in re.findall(r"[A-Za-z0-9_]+", query) if len(t) > 1]
        if not query_terms:
            return []

        # Retrieve chunks for repository
        chunks = db.query(CodeChunk).filter(CodeChunk.repository_id == repository_id).all()
        scored_results = []

        for chunk in chunks:
            text = (f"{chunk.symbol_name or ''} {chunk.content}").lower()
            score = 0.0

            # Symbol match has high weight
            sym_lower = (chunk.symbol_name or "").lower()
            for term in query_terms:
                if term == sym_lower:
                    score += 3.0
                elif term in sym_lower:
                    score += 1.5

                # Term frequency in content
                count = text.count(term)
                if count > 0:
                    score += 1.0 + math.log(count)

            if score > 0.0:
                # Normalize score between 0 and 1
                norm_score = round(min(score / (len(query_terms) * 3.5), 1.0), 4)
                file_path = chunk.file.file_path if chunk.file else "unknown"
                scored_results.append((
                    norm_score,
                    SearchResultItem(
                        chunk_id=chunk.id,
                        file_path=file_path,
                        symbol_name=chunk.symbol_name or "block",
                        chunk_type=chunk.chunk_type,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        content=chunk.content,
                        similarity_score=norm_score,
                        search_strategy="keyword"
                    )
                ))

        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored_results[:limit]]

    def semantic_search(
        self,
        db: Session,
        repository_id: str,
        query: str,
        limit: int = 10,
        min_score: float = 0.0
    ) -> List[SearchResultItem]:
        """Calculates cosine similarity between query embedding and stored chunk embeddings."""
        query_vec = embedding_service.generate_embedding(query)
        chunks = db.query(CodeChunk).filter(CodeChunk.repository_id == repository_id).all()
        scored_results = []

        for chunk in chunks:
            # If chunk does not have cached embedding, generate and save it
            chunk_vec = chunk.embedding
            if not chunk_vec:
                text_to_embed = f"{chunk.symbol_name or ''} {chunk.content}"
                chunk_vec = embedding_service.generate_embedding(text_to_embed)
                chunk.embedding = chunk_vec
                chunk.embedding_model = embedding_service.model_name

            score = embedding_service.cosine_similarity(query_vec, chunk_vec)
            if score >= min_score:
                file_path = chunk.file.file_path if chunk.file else "unknown"
                scored_results.append((
                    score,
                    SearchResultItem(
                        chunk_id=chunk.id,
                        file_path=file_path,
                        symbol_name=chunk.symbol_name or "block",
                        chunk_type=chunk.chunk_type,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        content=chunk.content,
                        similarity_score=score,
                        search_strategy="semantic"
                    )
                ))

        # Commit generated embeddings to DB
        db.commit()
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored_results[:limit]]

    def hybrid_search(
        self,
        db: Session,
        repository_id: str,
        query: str,
        limit: int = 10,
        min_score: float = 0.0
    ) -> List[SearchResultItem]:
        """
        Combines Dense Semantic Search and Keyword Search scores using weighted fusion.
        Score = 0.6 * SemanticScore + 0.4 * KeywordScore
        """
        keyword_results = {r.chunk_id: r for r in self.keyword_search(db, repository_id, query, limit=limit * 2)}
        semantic_results = {r.chunk_id: r for r in self.semantic_search(db, repository_id, query, limit=limit * 2, min_score=min_score)}

        all_chunk_ids = set(keyword_results.keys()) | set(semantic_results.keys())
        combined: List[SearchResultItem] = []

        for cid in all_chunk_ids:
            k_item = keyword_results.get(cid)
            s_item = semantic_results.get(cid)

            k_score = k_item.similarity_score if k_item else 0.0
            s_score = s_item.similarity_score if s_item else 0.0

            hybrid_score = round(
                (self.dense_weight * s_score) + (self.sparse_weight * k_score), 4
            )

            base_item = s_item or k_item
            combined.append(
                SearchResultItem(
                    chunk_id=base_item.chunk_id,
                    file_path=base_item.file_path,
                    symbol_name=base_item.symbol_name,
                    chunk_type=base_item.chunk_type,
                    start_line=base_item.start_line,
                    end_line=base_item.end_line,
                    content=base_item.content,
                    similarity_score=hybrid_score,
                    search_strategy="hybrid"
                )
            )

        combined.sort(key=lambda x: x.similarity_score, reverse=True)
        return combined[:limit]


search_service = SearchService()
