"""
Deep Learning Module for CodeBERT Defect Classification and Vulnerability Intelligence.
"""
from ai_engine.deep_learning.config import DLConfig
from ai_engine.deep_learning.inference import DefectInferenceEngine, defect_inference_engine

__all__ = ["DLConfig", "DefectInferenceEngine", "defect_inference_engine"]
