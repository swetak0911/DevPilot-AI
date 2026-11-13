"""
DevPilot AI - Phase 14 Deployment Failure Risk Prediction Engine Tests
Validates telemetry feature extraction, supervised ML model training, ROC-AUC >= 0.85,
real-time inference, localized SHAP factor attribution, actionable mitigations,
and REST API endpoints.
"""
import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import init_db, SessionLocal
from ml.deployment_risk.data_collector import deployment_data_collector, DeploymentDataPoint
from ml.deployment_risk.model_trainer import deployment_model_trainer, ModelMetrics
from ml.deployment_risk.risk_predictor import deployment_risk_predictor, RiskPredictionResult
from app.services.ml_risk_service import ml_risk_service
from app.schemas.ml import DeploymentRiskRequest, DeploymentRiskResponse, DeploymentRiskMetricsResponse


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def db():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_data_collector_telemetry():
    """Verifies synthetic dataset generation and feature matrix conversion."""
    dataset = deployment_data_collector.generate_synthetic_dataset(n_samples=300, seed=123)
    assert len(dataset) == 300
    sample = dataset[0]
    assert isinstance(sample, DeploymentDataPoint)
    assert sample.lines_added >= 0
    assert sample.lines_deleted >= 0
    assert sample.total_churn == sample.lines_added + sample.lines_deleted
    assert 0.0 <= sample.test_files_ratio <= 1.0
    assert sample.is_weekend in (0, 1)
    assert sample.failed_deployment in (0, 1)

    X, y = deployment_data_collector.to_feature_matrix(dataset)
    assert len(X) == 300
    assert len(y) == 300
    assert len(X[0]) == len(deployment_data_collector.FEATURE_NAMES)
    assert len(deployment_data_collector.FEATURE_NAMES) == 14


def test_model_trainer_performance():
    """Verifies supervised classification model achieves target ROC-AUC >= 0.85 and balanced metrics."""
    metrics: ModelMetrics = deployment_model_trainer.train(seed=42)
    assert isinstance(metrics, ModelMetrics)
    assert metrics.roc_auc >= 0.85, f"ROC-AUC {metrics.roc_auc} below required threshold 0.85"
    assert metrics.precision >= 0.80, f"Precision {metrics.precision} below required threshold 0.80"
    assert metrics.recall >= 0.80, f"Recall {metrics.recall} below required threshold 0.80"
    assert metrics.f1_score >= 0.80, f"F1-Score {metrics.f1_score} below required threshold 0.80"
    assert metrics.accuracy >= 0.80

    # Validate confusion matrix
    cm = metrics.confusion_matrix
    assert len(cm) == 2 and len(cm[0]) == 2
    tn, fp = cm[0]
    fn, tp = cm[1]
    assert tn + fp + fn + tp == metrics.total_test_samples

    # Validate feature importances
    assert len(metrics.feature_importances) == 14
    total_importance = sum(metrics.feature_importances.values())
    assert 0.99 <= total_importance <= 1.01


def test_model_persistence_and_reload():
    """Verifies model weights and metadata are persisted to disk and accurately reloaded."""
    assert os.path.exists(deployment_model_trainer.MODEL_PATH)
    loaded = deployment_model_trainer.load_model()
    assert loaded is True
    assert len(deployment_model_trainer.weights) == 14
    assert deployment_model_trainer.metrics is not None
    assert deployment_model_trainer.metrics.roc_auc >= 0.85


def test_realtime_risk_inference_low_vs_high():
    """Verifies risk score inference differentiates between low-risk and high-risk commits."""
    # Low-risk commit: minimal churn, high test ratio, no dependency changes, reliable author
    res_low: RiskPredictionResult = deployment_risk_predictor.predict(
        lines_added=25,
        lines_deleted=8,
        files_changed_count=3,
        test_files_count=2,
        config_files_modified=0,
        dependency_files_modified=0,
        author_prior_success_rate=0.98,
        time_of_day_utc=11,
        is_weekend=0,
        historical_failure_rate=0.03
    )
    assert res_low.risk_score < 0.35
    assert res_low.risk_level in ("LOW", "MEDIUM")

    # High-risk commit: large churn, zero tests, multiple dependencies, weekend, high failure history
    res_high: RiskPredictionResult = deployment_risk_predictor.predict(
        lines_added=950,
        lines_deleted=380,
        files_changed_count=28,
        test_files_count=0,
        config_files_modified=2,
        dependency_files_modified=4,
        author_prior_success_rate=0.60,
        time_of_day_utc=22,
        is_weekend=1,
        historical_failure_rate=0.45
    )
    assert res_high.risk_score >= 0.50
    assert res_high.risk_level in ("HIGH", "CRITICAL")
    assert res_high.risk_score > res_low.risk_score


def test_localized_factor_attribution():
    """Verifies SHAP-style localized factor attributions produce explainable impact weights and directions."""
    res: RiskPredictionResult = deployment_risk_predictor.predict(
        lines_added=600,
        lines_deleted=200,
        files_changed_count=15,
        test_files_count=1,
        dependency_files_modified=2,
        historical_failure_rate=0.30
    )
    assert len(res.top_contributing_factors) >= 3
    for factor in res.top_contributing_factors:
        assert factor.impact_direction in ("INCREASES_RISK", "REDUCES_RISK")
        assert factor.impact_weight > 0.0
        assert len(factor.description) > 0
        assert factor.display_name != ""


def test_actionable_mitigation_recommendations():
    """Verifies actionable mitigations are triggered for risky commit profiles."""
    res: RiskPredictionResult = deployment_risk_predictor.predict(
        lines_added=800,
        lines_deleted=300,
        files_changed_count=20,
        test_files_count=0,
        dependency_files_modified=2,
        is_weekend=1,
        historical_failure_rate=0.35
    )
    recs = res.recommended_mitigations
    assert len(recs) >= 3
    # Check for churn, test coverage, dependency, weekend, or canary recommendations
    joined = " ".join(recs).lower()
    assert "churn" in joined or "peer review" in joined
    assert "test" in joined
    assert "dependency" in joined or "audit" in joined


def test_ml_risk_service(db):
    """Verifies service layer prediction, metric retrieval, and model training."""
    req = DeploymentRiskRequest(
        repository_id="test-repo-p14",
        files_changed=12,
        lines_added=250,
        lines_deleted=80,
        dependencies_changed=1,
        historical_failure_rate=0.15
    )
    resp: DeploymentRiskResponse = ml_risk_service.predict_risk(req, db=db)
    assert 0.0 <= resp.risk_score <= 1.0
    assert resp.risk_level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert len(resp.contributing_factors) >= 1
    assert len(resp.recommendations) >= 1
    assert resp.model_auc >= 0.85

    metrics: DeploymentRiskMetricsResponse = ml_risk_service.get_metrics()
    assert metrics.roc_auc >= 0.85
    assert metrics.f1_score >= 0.80


def test_api_endpoints(client):
    """Verifies FastAPI REST API endpoints for deployment risk estimation, training, and metrics."""
    # 1. POST /api/v1/ml/deployment-risk
    risk_payload = {
        "repository_id": "test-repo-api",
        "files_changed": 10,
        "lines_added": 300,
        "lines_deleted": 70,
        "dependencies_changed": 1,
        "historical_failure_rate": 0.20
    }
    r = client.post("/api/v1/ml/deployment-risk", json=risk_payload)
    assert r.status_code == 200
    data = r.json()
    assert "risk_score" in data
    assert "risk_level" in data
    assert "contributing_factors" in data
    assert "recommendations" in data
    assert data["model_auc"] >= 0.85

    # 2. GET /api/v1/ml/deployment-risk/metrics
    r_metrics = client.get("/api/v1/ml/deployment-risk/metrics")
    assert r_metrics.status_code == 200
    m_data = r_metrics.json()
    assert m_data["roc_auc"] >= 0.85
    assert m_data["precision"] >= 0.80
    assert "confusion_matrix" in m_data
    assert "feature_importances" in m_data

    # 3. GET /api/v1/ml/deployment-risk/feature-importance
    r_feat = client.get("/api/v1/ml/deployment-risk/feature-importance")
    assert r_feat.status_code == 200
    f_data = r_feat.json()
    assert "feature_importances" in f_data
    assert len(f_data["feature_importances"]) == 14

    # 4. POST /api/v1/ml/deployment-risk/train
    r_train = client.post("/api/v1/ml/deployment-risk/train?n_samples=300")
    assert r_train.status_code == 200
    t_data = r_train.json()
    assert t_data["status"] == "SUCCESS"
    assert t_data["roc_auc"] >= 0.85
