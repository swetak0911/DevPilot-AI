"""
Phase 4 Semantic Code Search & RAG Test Suite
Tests code chunking, dense vector embeddings, cosine similarity,
keyword/semantic/hybrid search, and token-budgeted context retrieval with Recall@K evaluation.
"""
import pytest
from app.services.code_chunker import code_chunker
from app.services.embeddings import embedding_service, EMBEDDING_DIM
from app.services.search import search_service
from app.services.retriever import context_retriever
from app.models.repository import Repository, RepositoryFile, CodeChunk
from app.core.database import SessionLocal


def test_code_chunker_ast_and_sliding_window():
    """Verifies that code chunker respects symbol boundaries and handles windowing."""
    sample_code = '''
def handle_authentication(username: str, secret: str) -> bool:
    """Verifies user credentials."""
    if not username:
        return False
    return secret == "secure"

class TokenManager:
    """Manages JWT sessions."""
    def issue(self, subject: str) -> str:
        return f"token_for_{subject}"
'''
    chunks = code_chunker.chunk_file("auth_module.py", sample_code)
    assert len(chunks) >= 3  # handle_authentication, TokenManager, issue
    names = [c.symbol_name for c in chunks]
    assert "handle_authentication" in names
    assert "TokenManager" in names
    assert "issue" in names

    # Verify chunk metadata and formatting
    auth_chunk = next(c for c in chunks if c.symbol_name == "handle_authentication")
    assert auth_chunk.start_line > 0
    assert auth_chunk.end_line >= auth_chunk.start_line
    assert "### Source: auth_module.py" in auth_chunk.formatted_context
    assert auth_chunk.token_count > 0


def test_embeddings_generation_and_normalization():
    """Verifies dense vector embedding dimensions, deterministic values, and unit L2 normalization."""
    text1 = "def authenticate_user(username: str, password_hash: str):"
    text2 = "def create_access_token(claims: dict, expires_in: int):"
    
    vec1 = embedding_service.generate_embedding(text1)
    vec2 = embedding_service.generate_embedding(text2)

    assert len(vec1) == EMBEDDING_DIM
    assert len(vec2) == EMBEDDING_DIM

    # Verify unit L2 norm: sum of squares ≈ 1.0
    norm1 = sum(x * x for x in vec1)
    norm2 = sum(x * x for x in vec2)
    assert pytest.approx(norm1, abs=0.01) == 1.0
    assert pytest.approx(norm2, abs=0.01) == 1.0

    # Determinism check
    vec1_again = embedding_service.generate_embedding(text1)
    assert vec1 == vec1_again


def test_cosine_similarity():
    """Verifies cosine similarity properties between identical, related, and divergent snippets."""
    vec1 = embedding_service.generate_embedding("def verify_jwt_token(token: str):")
    vec1_dup = embedding_service.generate_embedding("def verify_jwt_token(token: str):")
    vec_related = embedding_service.generate_embedding("def validate_authentication_bearer(auth_header: str):")
    vec_unrelated = embedding_service.generate_embedding("docker compose up --build postgres database")

    sim_identical = embedding_service.cosine_similarity(vec1, vec1_dup)
    assert pytest.approx(sim_identical, abs=0.001) == 1.0

    sim_related = embedding_service.cosine_similarity(vec1, vec_related)
    sim_unrelated = embedding_service.cosine_similarity(vec1, vec_unrelated)

    # Related security functions should have positive cosine similarity
    assert sim_related > 0.0
    assert sim_identical >= sim_related


def test_keyword_and_semantic_and_hybrid_search(db_session):
    """Verifies BM25 keyword matching, vector semantic retrieval, and hybrid fusion."""
    # Create test repository and chunks
    repo = Repository(
        name="test-rag-repo",
        full_name="org/test-rag-repo",
        html_url="https://github.com/org/test-rag-repo",
        clone_url="https://github.com/org/test-rag-repo.git",
        default_branch="main"
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)

    test_file = RepositoryFile(
        repository_id=repo.id,
        file_path="src/security.py",
        file_name="security.py",
        extension=".py",
        language="Python",
        size_bytes=500,
        line_count=30,
        ast_metadata={}
    )
    db_session.add(test_file)
    db_session.commit()
    db_session.refresh(test_file)

    c1_content = "def verify_password(plain_password: str, hashed_password: str) -> bool:\n    return pwd_context.verify(plain_password, hashed_password)"
    c2_content = "def create_access_token(data: dict) -> str:\n    return jwt.encode(data, SECRET_KEY, algorithm='HS256')"
    c3_content = "def calculate_statistics(metrics: list) -> float:\n    return sum(metrics) / max(len(metrics), 1)"

    chunk1 = CodeChunk(
        repository_id=repo.id,
        file_id=test_file.id,
        chunk_type="function",
        symbol_name="verify_password",
        start_line=1,
        end_line=5,
        content=c1_content,
        token_count=25,
        embedding=embedding_service.generate_embedding(f"verify_password {c1_content}"),
        embedding_model=embedding_service.model_name
    )
    chunk2 = CodeChunk(
        repository_id=repo.id,
        file_id=test_file.id,
        chunk_type="function",
        symbol_name="create_access_token",
        start_line=7,
        end_line=15,
        content=c2_content,
        token_count=35,
        embedding=embedding_service.generate_embedding(f"create_access_token {c2_content}"),
        embedding_model=embedding_service.model_name
    )
    chunk3 = CodeChunk(
        repository_id=repo.id,
        file_id=test_file.id,
        chunk_type="function",
        symbol_name="calculate_statistics",
        start_line=17,
        end_line=25,
        content=c3_content,
        token_count=20,
        embedding=embedding_service.generate_embedding(f"calculate_statistics {c3_content}"),
        embedding_model=embedding_service.model_name
    )
    db_session.add_all([chunk1, chunk2, chunk3])
    db_session.commit()

    # 1. Keyword Search
    kw_results = search_service.keyword_search(db_session, repo.id, "verify_password")
    assert len(kw_results) >= 1
    assert kw_results[0].symbol_name == "verify_password"

    # 2. Semantic Search
    sem_results = search_service.semantic_search(db_session, repo.id, "jwt authentication token creation", limit=2)
    assert len(sem_results) >= 1
    # create_access_token should be top result for jwt token creation
    assert sem_results[0].symbol_name == "create_access_token"

    # 3. Hybrid Search
    hybrid_results = search_service.hybrid_search(db_session, repo.id, "verify password", limit=2)
    assert len(hybrid_results) >= 1
    assert hybrid_results[0].symbol_name == "verify_password"
    assert hybrid_results[0].search_strategy == "hybrid"


def test_retriever_context_budget_and_evaluator(db_session):
    """Verifies token-budgeted prompt construction and Recall@K / MRR evaluation."""
    repo = Repository(
        name="test-eval-repo",
        full_name="org/test-eval-repo",
        html_url="https://github.com/org/test-eval-repo",
        clone_url="https://github.com/org/test-eval-repo.git",
        default_branch="main"
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)

    test_file = RepositoryFile(
        repository_id=repo.id,
        file_path="core/auth.py",
        file_name="auth.py",
        extension=".py",
        language="Python",
        size_bytes=300,
        line_count=20,
        ast_metadata={}
    )
    db_session.add(test_file)
    db_session.commit()
    db_session.refresh(test_file)

    chunk = CodeChunk(
        repository_id=repo.id,
        file_id=test_file.id,
        chunk_type="function",
        symbol_name="generate_jwt_token",
        start_line=1,
        end_line=10,
        content="def generate_jwt_token(user_id: str) -> str:\n    return 'secret-jwt-token'",
        token_count=20,
        embedding=embedding_service.generate_embedding("generate_jwt_token def generate_jwt_token(user_id: str) -> str: return 'secret-jwt-token'"),
        embedding_model=embedding_service.model_name
    )
    db_session.add(chunk)
    db_session.commit()

    # Test token budgeting
    retrieval_res = context_retriever.retrieve_context(
        db=db_session,
        repository_id=repo.id,
        query="generate jwt token",
        top_k=3
    )
    assert retrieval_res.total_retrieved >= 1
    assert retrieval_res.total_tokens > 0
    assert "### Symbol: generate_jwt_token" in retrieval_res.llm_context_prompt
    assert "core/auth.py" in retrieval_res.llm_context_prompt

    # Test Recall@K and MRR benchmark evaluation
    benchmarks = [
        {
            "query": "generate jwt token",
            "expected_files": ["auth.py"],
            "expected_symbols": ["generate_jwt_token"]
        }
    ]
    metrics = context_retriever.evaluate_retrieval(
        db=db_session,
        repository_id=repo.id,
        benchmark_cases=benchmarks,
        k=5
    )
    assert metrics["recall_at_5"] == 1.0
    assert metrics["mean_reciprocal_rank"] == 1.0
