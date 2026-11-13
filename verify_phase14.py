"""
========================================================================
 DevPilot AI - Phase 14 Deployment Risk Prediction Verification Suite
========================================================================
Statically and dynamically verifies telemetry feature collection,
supervised classification model training (ROC-AUC >= 0.85, Precision/
Recall/F1 >= 0.80), weight persistence, real-time inference, localized
SHAP factor attributions, actionable mitigations, and REST APIs.
========================================================================
"""
import sys
import os
import json
import traceback
from typing import Dict, Any, List

# Add workspace and backend to sys.path
root_path = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(root_path, "backend")
if root_path not in sys.path:
    sys.path.insert(0, root_path)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db, SessionLocal
from ml.deployment_risk.data_collector import deployment_data_collector, DeploymentDataPoint
from ml.deployment_risk.model_trainer import deployment_model_trainer, ModelMetrics
from ml.deployment_risk.risk_predictor import deployment_risk_predictor, RiskPredictionResult
from app.services.ml_risk_service import ml_risk_service
from app.schemas.ml import DeploymentRiskRequest, DeploymentRiskResponse, DeploymentRiskMetricsResponse


def run_phase14_verification() -> bool:
    print("=" * 72)
    print(" DevPilot AI - Phase 14 Deployment Risk Prediction Suite")
    print("=" * 72)

    init_db()
    client = TestClient(app)

    # -------------------------------------------------------------------------
    # 1. Telemetry Data Collector & Feature Extraction
    # -------------------------------------------------------------------------
    print("\n[CHECK 1] Telemetry Data Collector & Feature Matrix...")
    try:
        dataset = deployment_data_collector.generate_synthetic_dataset(n_samples=500, seed=42)
        assert len(dataset) == 500, f"Expected 500 samples, got {len(dataset)}"
        first = dataset[0]
        assert hasattr(first, "lines_added") and hasattr(first, "total_churn"), "Missing churn attributes"
        assert hasattr(first, "test_files_ratio") and hasattr(first, "is_weekend"), "Missing ratio/timing attributes"
        assert hasattr(first, "historical_failure_rate") and hasattr(first, "failed"), "Missing failure attributes"

        X, y = deployment_data_collector.to_feature_matrix(dataset)
        assert len(X) == 500 and len(y) == 500, f"Mismatch in X ({len(X)}) or y ({len(y)}) lengths"
        assert len(X[0]) == 14, f"Expected 14 features, got {len(X[0])}"
        print(f" [PASS] 1. Data Collector & Feature Matrix: OK (Generated {len(dataset)} samples across 14 engineered features)")
    except Exception as exc:
        print(f" [FAIL] 1. Data Collector: {exc}\n{traceback.format_exc()}")
        return False

    # -------------------------------------------------------------------------
    # 2. Supervised Model Training & Evaluation Metrics (ROC-AUC >= 0.85)
    # -------------------------------------------------------------------------
    print("\n[CHECK 2] Supervised Model Training & ROC-AUC Validation...")
    try:
        metrics: ModelMetrics = deployment_model_trainer.train(seed=42)
        assert metrics.roc_auc >= 0.85, f"ROC-AUC {metrics.roc_auc} < 0.85"
        assert metrics.precision >= 0.80, f"Precision {metrics.precision} < 0.80"
        assert metrics.recall >= 0.80, f"Recall {metrics.recall} < 0.80"
        assert metrics.f1_score >= 0.80, f"F1-score {metrics.f1_score} < 0.80"
        assert metrics.accuracy >= 0.80, f"Accuracy {metrics.accuracy} < 0.80"
        assert len(metrics.confusion_matrix) == 2 and len(metrics.confusion_matrix[0]) == 2
        print(
            f" [PASS] 2. Model Training & Validation: OK "
            f"(ROC-AUC: {metrics.roc_auc:.3f} >= 0.85, Precision: {metrics.precision:.1%}, "
            f"Recall: {metrics.recall:.1%}, F1: {metrics.f1_score:.3f}, Acc: {metrics.accuracy:.1%})"
        )
    except Exception as exc:
        print(f" [FAIL] 2. Model Training: {exc}\n{traceback.format_exc()}")
        return False

    # -------------------------------------------------------------------------
    # 3. Model Weight Persistence & Disk Reload
    # -------------------------------------------------------------------------
    print("\n[CHECK 3] Model Weight Persistence & Serialization...")
    try:
        assert os.path.exists(deployment_model_trainer.MODEL_PATH), "Model JSON file missing on disk"
        reloaded = deployment_model_trainer.load_model()
        assert reloaded is True, "Failed to load model from disk"
        assert len(deployment_model_trainer.weights) == 14
        assert deployment_model_trainer.metrics is not None
        assert deployment_model_trainer.metrics.roc_auc >= 0.85
        print(f" [PASS] 3. Weight Persistence & Disk Reload: OK (Saved to '{os.path.basename(deployment_model_trainer.MODEL_PATH)}', reloaded 14 weights)")
    except Exception as exc:
        print(f" [FAIL] 3. Persistence & Reload: {exc}\n{traceback.format_exc()}")
        return False

    # -------------------------------------------------------------------------
    # 4. Real-Time Risk Inference & Level Categorization
    # -------------------------------------------------------------------------
    print("\n[CHECK 4] Real-Time Risk Inference & Categorization...")
    try:
        # Minimal low-risk commit
        low_res = deployment_risk_predictor.predict(
            lines_added=15,
            lines_deleted=4,
            files_changed_count=2,
            test_files_count=1,
            config_files_modified=0,
            dependency_files_modified=0,
            author_prior_success_rate=0.98,
            time_of_day_utc=10,
            is_weekend=0,
            historical_failure_rate=0.04
        )
        assert low_res.risk_score < 0.35, f"Expected low risk, got {low_res.risk_score}"
        assert low_res.risk_level in ("LOW", "MEDIUM")

        # Major high-risk release
        high_res = deployment_risk_predictor.predict(
            lines_added=1200,
            lines_deleted=450,
            files_changed_count=32,
            test_files_count=0,
            config_files_modified=3,
            dependency_files_modified=4,
            author_prior_success_rate=0.55,
            time_of_day_utc=23,
            is_weekend=1,
            historical_failure_rate=0.48
        )
        assert high_res.risk_score >= 0.50, f"Expected high risk, got {high_res.risk_score}"
        assert high_res.risk_level in ("HIGH", "CRITICAL")
        assert high_res.risk_score > low_res.risk_score

        print(
            f" [PASS] 4. Real-Time Risk Inference: OK "
            f"(Low-risk commit: {low_res.risk_score:.1%} [{low_res.risk_level}] vs "
            f"High-risk commit: {high_res.risk_score:.1%} [{high_res.risk_level}])"
        )
    except Exception as exc:
        print(f" [FAIL] 4. Risk Inference: {exc}\n{traceback.format_exc()}")
        return False

    # -------------------------------------------------------------------------
    # 5. Localized Factor Attribution (SHAP-Style Linear Decomposition)
    # -------------------------------------------------------------------------
    print("\n[CHECK 5] Localized Factor Attribution (SHAP)...")
    try:
        factors = high_res.top_contributing_factors
        assert len(factors) >= 3, "Expected at least 3 contributing factors"
        for factor in factors:
            assert factor.impact_direction in ("INCREASES_RISK", "REDUCES_RISK")
            assert factor.impact_weight > 0.0
            assert len(factor.description) > 0
            assert factor.display_name != ""

        top_fac = factors[0]
        print(
            f" [PASS] 5. Localized Factor Attribution: OK "
            f"(Top factor: '{top_fac.display_name}' [{top_fac.impact_direction}, {top_fac.impact_weight}% weight])"
        )
    except Exception as exc:
        print(f" [FAIL] 5. Factor Attribution: {exc}\n{traceback.format_exc()}")
        return False

    # -------------------------------------------------------------------------
    # 6. Actionable Mitigation Recommendations
    # -------------------------------------------------------------------------
    print("\n[CHECK 6] Actionable Mitigation Recommendations...")
    try:
        recs = high_res.recommended_mitigations
        assert len(recs) >= 3, f"Expected >= 3 recommendations for high-risk commit, got {len(recs)}"
        joined = " ".join(recs).lower()
        assert "churn" in joined or "peer review" in joined
        assert "test" in joined
        assert "dependency" in joined or "audit" in joined

        print(f" [PASS] 6. Actionable Mitigation Engine: OK (Generated {len(recs)} targeted mitigations: '{recs[0][:48]}...')")
    except Exception as exc:
        print(f" [FAIL] 6. Mitigations: {exc}\n{traceback.format_exc()}")
        return False

    # -------------------------------------------------------------------------
    # 7. End-to-End REST APIs
    # -------------------------------------------------------------------------
    print("\n[CHECK 7] End-to-End REST APIs...")
    try:
        # POST /api/ml/deployment-risk (and /api/v1/ml/deployment-risk)
        payload = {
            "repository_id": "phase14-verification-repo",
            "files_changed": 14,
            "lines_added": 380,
            "lines_deleted": 95,
            "dependencies_changed": 2,
            "historical_failure_rate": 0.18
        }
        r_pred = client.post("/api/ml/deployment-risk", json=payload)
        if r_pred.status_code == 404:
            r_pred = client.post("/api/v1/ml/deployment-risk", json=payload)

        assert r_pred.status_code == 200, f"POST /deployment-risk returned {r_pred.status_code}: {r_pred.text}"
        data_pred = r_pred.json()
        assert "risk_score" in data_pred
        assert "contributing_factors" in data_pred
        assert "recommendations" in data_pred
        assert data_pred["model_auc"] >= 0.85

        # GET /api/ml/deployment-risk/metrics
        r_met = client.get("/api/ml/deployment-risk/metrics")
        if r_met.status_code == 404:
            r_met = client.get("/api/v1/ml/deployment-risk/metrics")
        assert r_met.status_code == 200, f"GET /deployment-risk/metrics returned {r_met.status_code}"
        data_met = r_met.json()
        assert data_met["roc_auc"] >= 0.85
        assert data_met["precision"] >= 0.80
        assert "confusion_matrix" in data_met

        # GET /api/ml/deployment-risk/feature-importance
        r_feat = client.get("/api/ml/deployment-risk/feature-importance")
        if r_feat.status_code == 404:
            r_feat = client.get("/api/v1/ml/deployment-risk/feature-importance")
        assert r_feat.status_code == 200, f"GET /deployment-risk/feature-importance returned {r_feat.status_code}"
        data_feat = r_feat.json()
        assert len(data_feat["feature_importances"]) == 14

        # POST /api/ml/deployment-risk/train
        r_trn = client.post("/api/ml/deployment-risk/train?n_samples=400")
        if r_trn.status_code == 404:
            r_trn = client.post("/api/v1/ml/deployment-risk/train?n_samples=400")
        assert r_trn.status_code == 200, f"POST /deployment-risk/train returned {r_trn.status_code}"
        data_trn = r_trn.json()
        assert data_trn["status"] == "SUCCESS"
        assert data_trn["roc_auc"] >= 0.85

        print(f" [PASS] 7. End-to-End REST APIs: OK (POST /deployment-risk, GET /metrics, GET /feature-importance, POST /train all 200 OK)")
    except Exception as exc:
        print(f" [FAIL] 7. REST APIs: {exc}\n{traceback.format_exc()}")
        return False

    print("\n" + "=" * 72)
    print(" [SUCCESS] Phase 14 Deployment Risk Prediction Engine Verified 100%!")
    print("=" * 72)
    return True


if __name__ == "__main__":
    success = run_phase14_verification()
    sys.exit(0 if success else 1)
