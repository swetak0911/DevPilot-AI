"""
Phase 5 Deep Learning: CodeBERT Defect Classification Test Suite
Tests dataset preparation, CodeBERT tokenization, model forward pass,
classification evaluation metrics, checkpoint management, and defect inference.
"""
import pytest
from ai_engine.deep_learning.config import dl_config
from ai_engine.deep_learning.dataset import get_dataset_splits, CodeTokenizer, DefectSample
from ai_engine.deep_learning.model import CodeBERTDefectClassifier
from ai_engine.deep_learning.evaluate import compute_classification_metrics, evaluate_dataset_samples
from ai_engine.deep_learning.checkpoint import checkpoint_manager
from ai_engine.deep_learning.inference import defect_inference_engine
from app.services.defect_service import defect_service
from app.models.repository import Repository, RepositoryFile, CodeChunk


def test_dl_config_initialization():
    """Verifies hyperparameters and device detection in deep learning config."""
    assert dl_config.num_classes == 2
    assert dl_config.max_seq_length > 0
    assert dl_config.defect_threshold == 0.50
    assert dl_config.learning_rate > 0
    assert dl_config.device in ["cuda", "mps", "cpu"]


def test_dataset_splits_and_tokenization():
    """Verifies CodeXGLUE dataset loading, tokenization, and padding."""
    splits = get_dataset_splits()
    assert "train" in splits
    assert "valid" in splits
    assert "test" in splits

    assert len(splits["train"]) >= 5
    assert len(splits["valid"]) >= 2
    assert len(splits["test"]) >= 2

    # Check sample structure
    sample = splits["train"][0]
    assert isinstance(sample.idx, int)
    assert isinstance(sample.func, str)
    assert sample.target in [0, 1]

    # Test tokenizer
    tokenizer = CodeTokenizer(max_length=128)
    encoded = tokenizer.encode(sample.func)
    assert "input_ids" in encoded
    assert "attention_mask" in encoded
    assert len(encoded["input_ids"]) == 128
    assert len(encoded["attention_mask"]) == 128
    # <s> / CLS at index 0
    assert encoded["input_ids"][0] == 0
    assert encoded["attention_mask"][0] == 1


def test_classification_metrics_math():
    """Verifies Accuracy, Precision, Recall, and F1 score computation."""
    # Perfect predictions
    preds = [1, 1, 0, 0]
    labels = [1, 1, 0, 0]
    res = compute_classification_metrics(preds, labels)
    assert res["accuracy"] == 1.0
    assert res["precision"] == 1.0
    assert res["recall"] == 1.0
    assert res["f1"] == 1.0
    assert res["confusion_matrix"]["tp"] == 2
    assert res["confusion_matrix"]["tn"] == 2

    # Partial predictions
    # TP: 1, FP: 1, FN: 1, TN: 1
    p2 = [1, 1, 0, 0]
    l2 = [1, 0, 1, 0]
    res2 = compute_classification_metrics(p2, l2)
    assert res2["accuracy"] == 0.5
    assert res2["precision"] == 0.5
    assert res2["recall"] == 0.5
    assert res2["f1"] == 0.5


def test_checkpoint_manager_and_metadata():
    """Verifies checkpoint saving, metadata JSON, and metric persistence."""
    metrics = {"accuracy": 0.89, "f1": 0.88, "precision": 0.87, "recall": 0.89}
    meta = checkpoint_manager.get_metadata()
    assert "metrics" in meta or "model_name" in meta


def test_defect_inference_engine_predictions():
    """Verifies defect inference on clean functions versus vulnerable / buggy code."""
    clean_code = (
        "def compute_total(items: list) -> float:\n"
        "    if not items:\n"
        "        return 0.0\n"
        "    return sum(x.price for x in items)\n"
    )
    clean_res = defect_inference_engine.predict_defect(clean_code)
    assert clean_res.has_defect is False
    assert clean_res.defect_probability < 0.40
    assert clean_res.severity in ["CLEAN", "LOW"]

    vulnerable_eval = "def run_input(cmd): eval(cmd)"
    eval_res = defect_inference_engine.predict_defect(vulnerable_eval)
    assert eval_res.has_defect is True
    assert eval_res.defect_probability >= 0.70
    assert any("eval" in p.lower() for p in eval_res.detected_anti_patterns)
    assert eval_res.severity in ["HIGH", "CRITICAL"]

    vulnerable_sql = "def find_user(name): return db.query(f'SELECT * FROM users WHERE name = {name}')"
    sql_res = defect_inference_engine.predict_defect(vulnerable_sql)
    assert sql_res.has_defect is True
    assert sql_res.defect_probability >= 0.65
    assert any("sql" in p.lower() for p in sql_res.detected_anti_patterns)


def test_defect_service_repository_chunk_scanning(db_session):
    """Verifies batch scanning of repository code chunks for defect hotspots."""
    repo = Repository(
        name="defect-test-repo",
        full_name="devpilot/defect-test-repo",
        html_url="https://github.com/devpilot/defect-test-repo",
        clone_url="https://github.com/devpilot/defect-test-repo.git",
        default_branch="main"
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)

    file_item = RepositoryFile(
        repository_id=repo.id,
        file_path="src/vulnerable_script.py",
        file_name="vulnerable_script.py",
        extension=".py",
        language="Python",
        size_bytes=350,
        line_count=20,
        ast_metadata={}
    )
    db_session.add(file_item)
    db_session.commit()
    db_session.refresh(file_item)

    c1 = CodeChunk(
        repository_id=repo.id,
        file_id=file_item.id,
        chunk_type="function",
        symbol_name="clean_adder",
        start_line=1,
        end_line=4,
        content="def clean_adder(a: int, b: int) -> int:\n    return a + b",
        token_count=15
    )
    c2 = CodeChunk(
        repository_id=repo.id,
        file_id=file_item.id,
        chunk_type="function",
        symbol_name="dynamic_runner",
        start_line=6,
        end_line=10,
        content="def dynamic_runner(payload: str):\n    exec(payload)",
        token_count=18
    )
    db_session.add_all([c1, c2])
    db_session.commit()

    scan_res = defect_service.scan_repository_chunks(db_session, repo.id)
    assert scan_res["total_chunks_scanned"] == 2
    assert scan_res["defects_detected"] >= 1
    assert len(scan_res["hotspots"]) >= 1
    top_hotspot = scan_res["hotspots"][0]
    assert top_hotspot["symbol_name"] == "dynamic_runner"
    assert top_hotspot["defect_probability"] >= 0.70
