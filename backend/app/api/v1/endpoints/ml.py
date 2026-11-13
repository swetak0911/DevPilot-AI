"""Machine Learning & Code Intelligence Inference Endpoints."""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.ml import (
    DefectPredictionRequest,
    DefectPredictionResponse,
    DeploymentRiskRequest,
    DeploymentRiskResponse,
    DeploymentRiskMetricsResponse
)
from app.services.defect_service import defect_service
from app.services.ml_risk_service import ml_risk_service
from ai_engine.deep_learning.train import train_defect_model

router = APIRouter(prefix="/ml", tags=["Deep Learning & Predictive Intelligence"])


@router.post("/defect-prediction", response_model=DefectPredictionResponse)
def predict_code_defect(payload: DefectPredictionRequest):
    """Infers code defect likelihood using CodeBERT fine-tuned model weights and AST anti-pattern analysis."""
    return defect_service.predict_defect(payload.code_snippet, payload.language)


@router.get("/model-metrics")
def get_defect_model_metrics():
    """Retrieves CodeBERT validation & test set performance metrics (Accuracy, Precision, Recall, F1, Confusion Matrix)."""
    return defect_service.get_model_evaluation_metrics()


@router.post("/scan-repository-defects/{repo_id}")
def scan_repository_for_defects(
    repo_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Scans all indexed repository AST chunks and returns ranked defect hotspots."""
    try:
        return defect_service.scan_repository_chunks(db=db, repository_id=repo_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/train-synthetic")
def trigger_synthetic_training(epochs: int = Query(1, ge=1, le=5)):
    """Triggers a local CodeBERT fine-tuning epoch for integration and verification."""
    return train_defect_model(epochs=epochs)



@router.post("/deployment-risk", response_model=DeploymentRiskResponse)
def estimate_deployment_risk(
    payload: DeploymentRiskRequest,
    db: Session = Depends(get_db)
):
    """
    Calculates CI/CD deployment failure risk based on change metrics, test ratios,
    dependency modifications, and historical patterns using a trained ML classifier.
    """
    return ml_risk_service.predict_risk(payload, db=db)


@router.post("/deployment-risk/train")
def train_deployment_risk_model(n_samples: int = Query(600, ge=100, le=2000)):
    """Triggers retraining of the deployment failure risk model on latest pipeline telemetry."""
    metrics = ml_risk_service.train_model(n_samples=n_samples)
    return {
        "status": "SUCCESS",
        "model_type": metrics.model_type,
        "roc_auc": metrics.roc_auc,
        "precision": metrics.precision,
        "recall": metrics.recall,
        "f1_score": metrics.f1_score,
        "accuracy": metrics.accuracy,
        "confusion_matrix": metrics.confusion_matrix,
        "total_training_samples": metrics.total_training_samples,
        "total_test_samples": metrics.total_test_samples
    }


@router.get("/deployment-risk/metrics", response_model=DeploymentRiskMetricsResponse)
def get_deployment_risk_metrics():
    """Retrieves deployment risk model evaluation metrics (ROC-AUC, Precision, Recall, F1, Confusion Matrix)."""
    return ml_risk_service.get_metrics()


@router.get("/deployment-risk/feature-importance")
def get_deployment_risk_feature_importance():
    """Returns global feature importance rankings across all telemetry variables."""
    metrics = ml_risk_service.get_metrics()
    return {
        "feature_importances": metrics.feature_importances,
        "model_type": metrics.model_type
    }
