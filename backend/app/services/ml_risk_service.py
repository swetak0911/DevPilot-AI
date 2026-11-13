"""
DevPilot AI - Machine Learning Risk Service
Orchestrates real-time deployment risk inference, model retraining,
and performance metric retrieval for DevOps pipelines.
"""
from typing import Optional, Dict, Any, List
import logging
from sqlalchemy.orm import Session

from ml.deployment_risk.data_collector import deployment_data_collector
from ml.deployment_risk.risk_predictor import deployment_risk_predictor, RiskPredictionResult
from ml.deployment_risk.model_trainer import deployment_model_trainer, ModelMetrics
from app.models.cicd import WorkflowRun
from app.schemas.ml import (
    DeploymentRiskRequest,
    DeploymentRiskResponse,
    DeploymentRiskMetricsResponse
)

logger = logging.getLogger(__name__)


class MLRiskService:
    """Service layer bridging repository telemetry and ML risk prediction models."""

    def predict_risk(
        self,
        payload: DeploymentRiskRequest,
        db: Optional[Session] = None
    ) -> DeploymentRiskResponse:
        """Infers deployment failure risk with contributing factors and mitigations."""
        # Query historical branch failure rate from DB if available
        hist_fail = payload.historical_failure_rate
        if db and hist_fail == 0.0 and payload.repository_id:
            past_runs = db.query(WorkflowRun).filter(WorkflowRun.repository_id == payload.repository_id).all()
            if past_runs:
                failed_runs = sum(1 for r in past_runs if r.conclusion == "failure")
                hist_fail = round(failed_runs / len(past_runs), 3)

        result: RiskPredictionResult = deployment_risk_predictor.predict(
            lines_added=payload.lines_added,
            lines_deleted=payload.lines_deleted,
            files_changed_count=payload.files_changed,
            test_files_count=max(0, int(payload.files_changed * 0.25)),
            config_files_modified=1 if payload.files_changed > 10 else 0,
            dependency_files_modified=payload.dependencies_changed,
            author_prior_success_rate=0.85,
            time_of_day_utc=14,
            is_weekend=0,
            workflow_jobs_count=3,
            has_docker_step=1,
            historical_failure_rate=hist_fail
        )

        factors = [
            {
                "feature": f.display_name,
                "direction": f.impact_direction,
                "weight_percentage": f.impact_weight,
                "description": f.description
            } for f in result.top_contributing_factors
        ]

        return DeploymentRiskResponse(
            risk_score=result.risk_score,
            risk_level=result.risk_level,
            contributing_factors=factors,
            explanation=f"Deployment failure probability estimated at {result.risk_score:.1%} ({result.risk_level} risk level).",
            model_version=result.model_version,
            recommendations=result.recommended_mitigations,
            model_auc=result.model_auc
        )

    def train_model(self, n_samples: int = 600, seed: int = 42) -> ModelMetrics:
        """Triggers model training on telemetry and returns validation performance metrics."""
        dataset = deployment_data_collector.generate_synthetic_dataset(n_samples=n_samples, seed=seed)
        return deployment_model_trainer.train(dataset=dataset, seed=seed)

    def get_metrics(self) -> DeploymentRiskMetricsResponse:
        """Returns current model test evaluation metrics (ROC-AUC, Precision, Recall, F1)."""
        if not deployment_model_trainer.metrics:
            deployment_model_trainer.train()

        m = deployment_model_trainer.metrics
        return DeploymentRiskMetricsResponse(
            roc_auc=m.roc_auc,
            precision=m.precision,
            recall=m.recall,
            f1_score=m.f1_score,
            accuracy=m.accuracy,
            confusion_matrix=m.confusion_matrix,
            feature_importances=m.feature_importances,
            model_type=m.model_type
        )


ml_risk_service = MLRiskService()
