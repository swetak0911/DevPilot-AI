"""
DevPilot AI - Machine Learning Deployment Failure Risk Prediction Subsystem
Extracts commit telemetry, trains risk prediction models (ROC-AUC >= 0.85),
and infers real-time failure probabilities with localized factor explanations.
"""
from ml.deployment_risk.data_collector import deployment_data_collector, DeploymentDataPoint
from ml.deployment_risk.model_trainer import deployment_model_trainer, ModelMetrics
from ml.deployment_risk.risk_predictor import deployment_risk_predictor, RiskPredictionResult

__all__ = [
    "deployment_data_collector",
    "DeploymentDataPoint",
    "deployment_model_trainer",
    "ModelMetrics",
    "deployment_risk_predictor",
    "RiskPredictionResult",
]
