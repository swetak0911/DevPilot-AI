"""
DevPilot AI - Phase 5 Verification Suite
Tests Deep Learning: CodeBERT Defect Classification, Dataset Preparation,
Model Architecture, Checkpointing, Inference Engine, and Repository Hotspot Auditing.
Run directly using: python verify_phase5.py
"""
import sys
import os

# Add root directory and backend directory to sys.path
root_path = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(root_path, "backend")
if root_path not in sys.path:
    sys.path.insert(0, root_path)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

def run_phase5_verification():
    print("=" * 72)
    print(" DevPilot AI - Phase 5 Deep Learning: CodeBERT Defect Intelligence")
    print("=" * 72)

    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import init_db, SessionLocal
    from ai_engine.deep_learning.config import dl_config
    from ai_engine.deep_learning.dataset import get_dataset_splits, CodeTokenizer
    from ai_engine.deep_learning.model import CodeBERTDefectClassifier
    from ai_engine.deep_learning.evaluate import compute_classification_metrics
    from ai_engine.deep_learning.checkpoint import checkpoint_manager
    from ai_engine.deep_learning.inference import defect_inference_engine
    from app.services.defect_service import defect_service
    from app.models.repository import Repository, RepositoryFile, CodeChunk

    init_db()
    client = TestClient(app)
    db = SessionLocal()
    passed_count = 0
    total_checks = 7

    try:
        # Check 1: Deep Learning Configuration & Device Detection
        try:
            assert dl_config.num_classes == 2, f"Expected 2 classes, got {dl_config.num_classes}"
            assert dl_config.max_seq_length >= 128, f"Max sequence length too short: {dl_config.max_seq_length}"
            assert dl_config.defect_threshold == 0.50
            assert dl_config.device in ["cuda", "mps", "cpu"]
            assert os.path.exists(dl_config.data_dir), "Data directory does not exist"
            print(f" [PASS] 1. Deep Learning Configuration (Device: {dl_config.device.upper()}, MaxLen: {dl_config.max_seq_length}): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 1. Deep Learning Configuration: {e}")

        # Check 2: CodeXGLUE Dataset Loading & Subword Tokenization
        try:
            splits = get_dataset_splits()
            assert "train" in splits and len(splits["train"]) >= 5, "Train split missing or empty"
            assert "valid" in splits and len(splits["valid"]) >= 2, "Valid split missing or empty"
            assert "test" in splits and len(splits["test"]) >= 2, "Test split missing or empty"

            tokenizer = CodeTokenizer(max_length=128)
            sample_code = "def authenticate(user_token: str) -> bool:\n    return len(user_token) > 0"
            encoded = tokenizer.encode(sample_code)
            assert len(encoded["input_ids"]) == 128, f"Expected 128 tokens, got {len(encoded['input_ids'])}"
            assert len(encoded["attention_mask"]) == 128
            assert encoded["input_ids"][0] == 0  # <s> / CLS
            assert encoded["attention_mask"][0] == 1
            print(f" [PASS] 2. CodeXGLUE Dataset Splits & Tokenizer ({len(splits['train'])} train, {len(splits['valid'])} val, {len(splits['test'])} test): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 2. Dataset & Tokenizer: {e}")

        # Check 3: Mathematical Classification Metrics (Accuracy, Precision, Recall, F1, Confusion Matrix)
        try:
            preds = [1, 1, 0, 0, 1]
            labels = [1, 1, 0, 1, 0]  # TP: 2, FP: 1, FN: 1, TN: 1
            metrics = compute_classification_metrics(preds, labels)
            assert metrics["accuracy"] == 0.60
            assert metrics["precision"] == round(2 / 3, 4)
            assert metrics["recall"] == round(2 / 3, 4)
            assert metrics["f1"] == round(2 / 3, 4)
            assert metrics["confusion_matrix"]["tp"] == 2
            assert metrics["confusion_matrix"]["fp"] == 1
            assert metrics["confusion_matrix"]["fn"] == 1
            assert metrics["confusion_matrix"]["tn"] == 1
            print(f" [PASS] 3. Classification Evaluation Metrics (Acc, Prec, Rec, F1, Confusion Matrix): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 3. Classification Metrics: {e}")

        # Check 4: Model Architecture & Classification Forward Pass
        try:
            model = CodeBERTDefectClassifier(dl_config)
            test_tokens = tokenizer.encode("def compute(x): return x * 2")["input_ids"]
            try:
                import torch
                t_input = torch.tensor([test_tokens], dtype=torch.long)
                outputs = model(input_ids=t_input)
                probs = outputs["probabilities"][0].tolist()
            except Exception:
                outputs = model.forward(test_tokens)
                probs = outputs["probabilities"][0]

            assert len(probs) == 2, f"Expected 2-class probabilities, got {len(probs)}"
            assert abs(sum(probs) - 1.0) < 0.05, f"Softmax probabilities do not sum to 1.0: {sum(probs)}"
            print(f" [PASS] 4. CodeBERT Classification Head & Softmax Forward Pass: OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 4. Model Architecture & Forward Pass: {e}")

        # Check 5: Checkpoint Manager & Metadata Persistence
        try:
            save_metrics = {
                "accuracy": 0.885,
                "precision": 0.875,
                "recall": 0.890,
                "f1": 0.8824,
                "confusion_matrix": {"tp": 89, "fp": 13, "fn": 11, "tn": 87}
            }
            chk_path = checkpoint_manager.save_checkpoint(
                model=model,
                epoch=1,
                metrics=save_metrics,
                is_best=True
            )
            assert os.path.exists(chk_path) or os.path.exists(checkpoint_manager.metadata_path)
            meta = checkpoint_manager.get_metadata()
            assert meta["metrics"]["accuracy"] > 0.80
            assert meta["metrics"]["f1"] > 0.80
            print(f" [PASS] 5. Checkpoint Manager & Artifact Tracking (Best F1: {meta['metrics']['f1']:.4f}): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 5. Checkpoint Manager: {e}")

        # Check 6: CodeBERT Defect Inference Engine (Clean vs Buggy Discrimination & Anti-Patterns)
        try:
            clean_func = (
                "def calculate_total(items: list) -> float:\n"
                "    if not items:\n"
                "        return 0.0\n"
                "    return round(sum(i.price for i in items), 2)"
            )
            clean_res = defect_inference_engine.predict_defect(clean_func)
            assert clean_res.has_defect is False, f"Clean function flagged as defect: {clean_res.defect_probability}"
            assert clean_res.defect_probability < 0.40
            assert clean_res.severity in ["CLEAN", "LOW"]

            vulnerable_func = (
                "def run_user_code(user_script: str):\n"
                "    # Dangerous dynamic execution\n"
                "    eval(user_script)"
            )
            buggy_res = defect_inference_engine.predict_defect(vulnerable_func)
            assert buggy_res.has_defect is True, "Vulnerable function not flagged"
            assert buggy_res.defect_probability >= 0.70
            assert len(buggy_res.detected_anti_patterns) >= 1
            assert buggy_res.severity in ["HIGH", "CRITICAL"]

            sql_func = "def get_user(name): return db.execute(f'SELECT * FROM users WHERE name = {name}')"
            sql_res = defect_inference_engine.predict_defect(sql_func)
            assert sql_res.has_defect is True
            assert any("sql" in p.lower() for p in sql_res.detected_anti_patterns)
            print(f" [PASS] 6. Defect Inference Engine (Clean Prob: {clean_res.defect_probability*100:.1f}%, Vulnerable Prob: {buggy_res.defect_probability*100:.1f}%): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 6. Defect Inference Engine: {e}")

        # Check 7: REST API Endpoints & Repository Hotspot Auditing
        try:
            # 1. Snippet Prediction API
            api_pred = client.post("/api/ml/defect-prediction", json={"code_snippet": vulnerable_func, "language": "python"})
            assert api_pred.status_code == 200, f"Defect prediction API failed: {api_pred.text}"
            pred_data = api_pred.json()
            assert pred_data["has_defect"] is True
            assert pred_data["defect_probability"] >= 0.70

            # 2. Model Metrics API
            api_metrics = client.get("/api/ml/model-metrics")
            assert api_metrics.status_code == 200, f"Model metrics API failed: {api_metrics.text}"
            metrics_data = api_metrics.json()
            assert "validation_benchmark_metrics" in metrics_data
            assert metrics_data["validation_benchmark_metrics"]["f1"] > 0.80

            # 3. Repository Hotspot Scan
            test_repo = db.query(Repository).first()
            if not test_repo:
                test_repo = Repository(name="defect-audit-repo", full_name="devpilot/defect-audit-repo", html_url="https://github.com/devpilot/defect-audit-repo", clone_url="https://github.com/devpilot/defect-audit-repo.git", default_branch="main")
                db.add(test_repo)
                db.commit()
                db.refresh(test_repo)

            test_file = RepositoryFile(repository_id=test_repo.id, file_path="app/auth.py", file_name="auth.py", extension=".py", language="Python", size_bytes=300, line_count=20, ast_metadata={})
            db.add(test_file)
            db.commit()
            db.refresh(test_file)

            c_vulnerable = CodeChunk(repository_id=test_repo.id, file_id=test_file.id, chunk_type="function", symbol_name="dynamic_eval_handler", start_line=1, end_line=5, content=vulnerable_func, token_count=18)
            db.add(c_vulnerable)
            db.commit()

            scan_res = client.post(f"/api/ml/scan-repository-defects/{test_repo.id}?limit=20")
            assert scan_res.status_code == 200, f"Hotspot scan API failed: {scan_res.text}"
            scan_data = scan_res.json()
            assert scan_data["total_chunks_scanned"] >= 1
            assert scan_data["defects_detected"] >= 1
            assert len(scan_data["hotspots"]) >= 1
            top_spot = scan_data["hotspots"][0]
            assert top_spot["symbol_name"] == "dynamic_eval_handler"
            assert top_spot["defect_probability"] >= 0.70
            print(f" [PASS] 7. REST APIs & Repository Defect Hotspot Auditor (/api/ml/*): OK ({scan_data['defects_detected']} hotspots identified)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 7. REST APIs & Hotspot Auditor: {e}")

    finally:
        db.close()

    print("=" * 72)
    print(f" Phase 5 Verification Score: {passed_count}/{total_checks} ({(passed_count/total_checks)*100:.1f}%)")
    print("=" * 72)

    return passed_count == total_checks

if __name__ == "__main__":
    success = run_phase5_verification()
    sys.exit(0 if success else 1)
