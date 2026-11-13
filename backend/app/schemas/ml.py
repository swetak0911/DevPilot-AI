"""Machine Learning & Predictive Intelligence Schemas."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class DefectPredictionRequest(BaseModel):
    code_snippet: str
    language: str = "python"


class DefectPredictionResponse(BaseModel):
    has_defect: bool
    defect_probability: float
    confidence_score: float
    detected_anti_patterns: List[str] = []
    explanation: str


class DeploymentRiskRequest(BaseModel):
    repository_id: str
    commit_sha: Optional[str] = None
    files_changed: int
    lines_added: int
    lines_deleted: int
    dependencies_changed: int = 0
    historical_failure_rate: float = 0.0


class DeploymentRiskResponse(BaseModel):
    risk_score: float  # 0.0 to 1.0
    risk_level: str    # LOW, MEDIUM, HIGH, CRITICAL
    contributing_factors: List[Dict[str, Any]] = []
    explanation: str
    model_version: str = "calibrated_logistic_v1"
    recommendations: List[str] = []
    model_auc: float = 0.88


class DeploymentRiskMetricsResponse(BaseModel):
    roc_auc: float
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    confusion_matrix: List[List[int]]
    feature_importances: Dict[str, float]
    model_type: str
