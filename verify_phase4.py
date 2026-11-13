"""
DevPilot AI - Phase 4 Verification Suite
Tests Semantic Code Search, Dense Vector Embeddings, Cosine Similarity,
BM25 Keyword Matching, Hybrid Rank Fusion, and Token-Budgeted LLM Context Retrieval with Recall@K.
Run directly using: python verify_phase4.py
"""
import sys
import os
import math

# Add backend directory to path
backend_path = os.path.join(os.path.dirname(__file__), "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

def run_phase4_verification():
    print("=" * 72)
    print(" DevPilot AI - Phase 4 Semantic Code Search & RAG Suite")
    print("=" * 72)

    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import init_db, SessionLocal
    from app.services.code_chunker import code_chunker
    from app.services.embeddings import embedding_service, EMBEDDING_DIM
    from app.services.search import search_service
    from app.services.retriever import context_retriever
    from app.models.repository import Repository, RepositoryFile, CodeChunk

    init_db()
    client = TestClient(app)
    db = SessionLocal()
    passed_count = 0
    total_checks = 7

    try:
        # Check 1: AST Boundary-Aware Code Chunker
        try:
            sample_code = (
                "def authenticate_client(api_key: str) -> bool:\n"
                "    '''Validates API access key.'''\n"
                "    return len(api_key) == 32\n\n"
                "class SessionValidator:\n"
                "    def validate(self, session_id: str) -> bool:\n"
                "        return bool(session_id)\n"
            )
            chunks = code_chunker.chunk_file("auth_check.py", sample_code)
            assert len(chunks) >= 2, f"Expected >= 2 chunks, got {len(chunks)}"
            sym_names = [c.symbol_name for c in chunks]
            assert "authenticate_client" in sym_names, "Missing authenticate_client chunk"
            assert "SessionValidator" in sym_names or "validate" in sym_names
            auth_c = next(c for c in chunks if c.symbol_name == "authenticate_client")
            assert auth_c.token_count > 0
            assert "### Source: auth_check.py" in auth_c.formatted_context
            print(f" [PASS] 1. Code Chunker (AST Boundaries & Line Preservation): OK ({len(chunks)} chunks)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 1. Code Chunker: {e}")

        # Check 2: Dense Vector Embedding Generator & L2 Normalization
        try:
            query = "jwt token signature verification"
            vec = embedding_service.generate_embedding(query)
            assert len(vec) == EMBEDDING_DIM, f"Expected {EMBEDDING_DIM} dims, got {len(vec)}"
            l2_norm = math.sqrt(sum(x * x for x in vec))
            assert abs(l2_norm - 1.0) < 0.05, f"Vector not normalized: norm={l2_norm}"
            # Check non-trivial values
            non_zeros = [x for x in vec if abs(x) > 1e-5]
            assert len(non_zeros) > 10, "Vector is nearly all zeros"
            print(f" [PASS] 2. Vector Embeddings ({EMBEDDING_DIM}-dim Dense, L2 Norm=1.0): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 2. Vector Embeddings: {e}")

        # Check 3: Cosine Similarity Properties & Semantic Discriminator
        try:
            v_auth1 = embedding_service.generate_embedding("def verify_jwt_token(token: str) -> bool:")
            v_auth2 = embedding_service.generate_embedding("def verify_jwt_token(token: str) -> bool:")
            v_related = embedding_service.generate_embedding("def authenticate_credentials(bearer_token: str):")
            v_divergent = embedding_service.generate_embedding("k8s deployment replica count horizontal pod autoscaler")

            sim_identical = embedding_service.cosine_similarity(v_auth1, v_auth2)
            assert abs(sim_identical - 1.0) < 0.001, f"Identical vectors similarity != 1.0: {sim_identical}"

            sim_rel = embedding_service.cosine_similarity(v_auth1, v_related)
            sim_div = embedding_service.cosine_similarity(v_auth1, v_divergent)
            assert sim_rel > 0.0, f"Related vectors should have positive similarity, got {sim_rel}"
            assert sim_identical >= sim_rel, "Self-similarity should be maximal"
            print(f" [PASS] 3. Cosine Similarity & Semantic Alignment (Identical=1.0, Related={sim_rel:.2f}): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 3. Cosine Similarity: {e}")

        # Setup Seed Data for Search & Retrieval Checks
        test_repo = db.query(Repository).filter(Repository.name == "rag-verify-repo").first()
        if not test_repo:
            test_repo = Repository(
                name="rag-verify-repo",
                full_name="devpilot/rag-verify-repo",
                html_url="https://github.com/devpilot/rag-verify-repo",
                clone_url="https://github.com/devpilot/rag-verify-repo.git",
                default_branch="main"
            )
            db.add(test_repo)
            db.commit()
            db.refresh(test_repo)

        # Clear previous chunks for a clean verification run
        db.query(CodeChunk).filter(CodeChunk.repository_id == test_repo.id).delete()
        db.query(RepositoryFile).filter(RepositoryFile.repository_id == test_repo.id).delete()
        db.commit()

        file1 = RepositoryFile(
            repository_id=test_repo.id,
            file_path="backend/security/auth.py",
            file_name="auth.py",
            extension=".py",
            language="Python",
            size_bytes=450,
            line_count=25,
            ast_metadata={}
        )
        file2 = RepositoryFile(
            repository_id=test_repo.id,
            file_path="backend/services/docker_deploy.py",
            file_name="docker_deploy.py",
            extension=".py",
            language="Python",
            size_bytes=600,
            line_count=35,
            ast_metadata={}
        )
        db.add_all([file1, file2])
        db.commit()
        db.refresh(file1)
        db.refresh(file2)

        c1_code = "def create_access_token(data: dict, expires_delta: int) -> str:\n    return jwt.encode(data, SECRET_KEY, algorithm='HS256')"
        c2_code = "def verify_password_hash(plain_password: str, hashed_pwd: str) -> bool:\n    return pwd_context.verify(plain_password, hashed_pwd)"
        c3_code = "def build_docker_container(image_tag: str, dockerfile_path: str):\n    return docker_client.images.build(path=dockerfile_path, tag=image_tag)"

        chunk1 = CodeChunk(
            repository_id=test_repo.id,
            file_id=file1.id,
            chunk_type="function",
            symbol_name="create_access_token",
            start_line=1,
            end_line=5,
            content=c1_code,
            token_count=30,
            embedding=embedding_service.generate_embedding(f"create_access_token {c1_code}"),
            embedding_model=embedding_service.model_name
        )
        chunk2 = CodeChunk(
            repository_id=test_repo.id,
            file_id=file1.id,
            chunk_type="function",
            symbol_name="verify_password_hash",
            start_line=7,
            end_line=12,
            content=c2_code,
            token_count=28,
            embedding=embedding_service.generate_embedding(f"verify_password_hash {c2_code}"),
            embedding_model=embedding_service.model_name
        )
        chunk3 = CodeChunk(
            repository_id=test_repo.id,
            file_id=file2.id,
            chunk_type="function",
            symbol_name="build_docker_container",
            start_line=1,
            end_line=6,
            content=c3_code,
            token_count=26,
            embedding=embedding_service.generate_embedding(f"build_docker_container {c3_code}"),
            embedding_model=embedding_service.model_name
        )
        db.add_all([chunk1, chunk2, chunk3])
        db.commit()

        # Check 4: BM25 Sparse Keyword Search
        try:
            kw_res = search_service.keyword_search(db, test_repo.id, "verify_password_hash", limit=5)
            assert len(kw_res) >= 1, "Keyword search returned no results"
            assert kw_res[0].symbol_name == "verify_password_hash"
            assert kw_res[0].similarity_score > 0.5
            print(f" [PASS] 4. BM25 Keyword Search (Exact Symbol Match & Score Weighting): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 4. BM25 Keyword Search: {e}")

        # Check 5: Dense Semantic Vector Search
        try:
            sem_res = search_service.semantic_search(db, test_repo.id, "jwt authentication token generation", limit=3)
            assert len(sem_res) >= 1, "Semantic search returned no results"
            # create_access_token should be the top match
            assert sem_res[0].symbol_name == "create_access_token", f"Expected create_access_token, got {sem_res[0].symbol_name}"
            assert sem_res[0].similarity_score > 0.0
            print(f" [PASS] 5. Dense Semantic Vector Search (Concept Discovery): OK (Top match: {sem_res[0].symbol_name})")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 5. Dense Semantic Vector Search: {e}")

        # Check 6: Hybrid Search (Weighted Rank Fusion) & Search API
        try:
            # Query via FastAPI client
            api_res = client.get(f"/api/repositories/{test_repo.id}/search?q=create_access_token&search_type=hybrid&limit=5")
            assert api_res.status_code == 200, f"Search API failed: {api_res.text}"
            hits = api_res.json()
            assert len(hits) >= 1, "API returned empty search list"
            top_hit = hits[0]
            assert top_hit["symbol_name"] == "create_access_token"
            assert top_hit["search_strategy"] == "hybrid"
            assert top_hit["similarity_score"] > 0.0
            print(f" [PASS] 6. Hybrid Weighted Rank Fusion Search API (/api/repositories/:id/search): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 6. Hybrid Search API: {e}")

        # Check 7: Token-Budgeted LLM Context Retrieval & Recall@5 / MRR Evaluator
        try:
            # Test /retrieve endpoint
            ret_payload = {
                "query": "how is access token generated and signed?",
                "top_k": 3,
                "search_type": "hybrid"
            }
            ret_res = client.post(f"/api/repositories/{test_repo.id}/retrieve", json=ret_payload)
            assert ret_res.status_code == 200, f"Retrieve API failed: {ret_res.text}"
            ret_data = ret_res.json()
            assert ret_data["total_retrieved"] >= 1
            assert ret_data["total_tokens"] > 0
            assert "### [Snippet 1]" in ret_data["llm_context_prompt"]
            assert "create_access_token" in ret_data["llm_context_prompt"]

            # Test /evaluate-retrieval benchmark endpoint
            eval_payload = {
                "benchmark_cases": [
                    {
                        "query": "create access token",
                        "expected_files": ["auth.py"],
                        "expected_symbols": ["create_access_token"]
                    },
                    {
                        "query": "build docker container",
                        "expected_files": ["docker_deploy.py"],
                        "expected_symbols": ["build_docker_container"]
                    }
                ],
                "k": 5
            }
            eval_res = client.post(f"/api/repositories/{test_repo.id}/evaluate-retrieval", json=eval_payload)
            assert eval_res.status_code == 200, f"Evaluate API failed: {eval_res.text}"
            metrics = eval_res.json()["metrics"]
            assert metrics["recall_at_5"] == 1.0, f"Expected Recall@5 == 1.0, got {metrics['recall_at_5']}"
            assert metrics["mean_reciprocal_rank"] == 1.0, f"Expected MRR == 1.0, got {metrics['mean_reciprocal_rank']}"
            print(f" [PASS] 7. Token-Budgeted LLM Context & Evaluator (Recall@5={metrics['recall_at_5']:.2f}, MRR={metrics['mean_reciprocal_rank']:.2f}): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 7. Context Retriever & Evaluator: {e}")

    finally:
        db.close()

    print("=" * 72)
    print(f" Phase 4 Verification Score: {passed_count}/{total_checks} ({(passed_count/total_checks)*100:.1f}%)")
    print("=" * 72)

    return passed_count == total_checks

if __name__ == "__main__":
    success = run_phase4_verification()
    sys.exit(0 if success else 1)
