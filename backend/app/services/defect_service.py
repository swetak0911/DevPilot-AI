"""
Defect Intelligence Service
Bridges backend REST endpoints to the CodeBERT Deep Learning subsystem.
Handles function defect predictions, repository-wide defect hotspot audits,
and model evaluation metric reporting.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from ai_engine.deep_learning.inference import defect_inference_engine, DefectPredictionResult
from ai_engine.deep_learning.checkpoint import checkpoint_manager
from ai_engine.deep_learning.dataset import get_dataset_splits
from ai_engine.deep_learning.evaluate import evaluate_dataset_samples
from app.models.repository import Repository, CodeChunk, RepositoryFile
from app.schemas.ml import DefectPredictionResponse
import logging

logger = logging.getLogger(__name__)


class DefectIntelligenceService:
    """Service layer for deep learning defect classification."""

    @staticmethod
    def predict_defect(code_snippet: str, language: str = "python") -> DefectPredictionResponse:
        """Runs CodeBERT defect inference on a given code snippet."""
        res: DefectPredictionResult = defect_inference_engine.predict_defect(code_snippet, language)
        return DefectPredictionResponse(
            has_defect=res.has_defect,
            defect_probability=res.defect_probability,
            confidence_score=res.confidence_score,
            detected_anti_patterns=res.detected_anti_patterns,
            explanation=res.explanation
        )

    @staticmethod
    def scan_repository_chunks(db: Session, repository_id: str, limit: int = 100) -> Dict[str, Any]:
        """
        Scans all indexed repository functions and classes to identify defect hotspots.
        """
        repo = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repo:
            raise ValueError(f"Repository {repository_id} not found")

        chunks = db.query(CodeChunk).filter(CodeChunk.repository_id == repository_id).limit(limit).all()
        if not chunks:
            return {
                "repository_id": repository_id,
                "status": "NO_CHUNKS",
                "message": "Repository has not been indexed yet. Run AST indexing first.",
                "total_chunks_scanned": 0,
                "defects_detected": 0,
                "hotspots": []
            }

        hotspots = []
        clean_count = 0
        defect_count = 0
        total_prob = 0.0

        for chunk in chunks:
            pred = defect_inference_engine.predict_defect(chunk.content)
            total_prob += pred.defect_probability

            if pred.has_defect:
                defect_count += 1
                hotspots.append({
                    "chunk_id": chunk.id,
                    "file_path": chunk.file.file_path if chunk.file else "unknown",
                    "symbol_name": chunk.symbol_name,
                    "chunk_type": chunk.chunk_type,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "defect_probability": pred.defect_probability,
                    "severity": pred.severity,
                    "detected_anti_patterns": pred.detected_anti_patterns,
                    "explanation": pred.explanation
                })
            else:
                clean_count += 1

        # Sort hotspots by defect probability descending
        hotspots.sort(key=lambda x: x["defect_probability"], reverse=True)
        avg_prob = round(total_prob / max(len(chunks), 1), 4)

        return {
            "repository_id": repository_id,
            "repository_name": repo.name,
            "total_chunks_scanned": len(chunks),
            "defects_detected": defect_count,
            "clean_chunks": clean_count,
            "average_defect_probability": avg_prob,
            "defect_rate": round(defect_count / max(len(chunks), 1), 4),
            "hotspots": hotspots[:25]
        }

    @staticmethod
    def get_model_evaluation_metrics() -> Dict[str, Any]:
        """Returns the CodeBERT model architecture and validation performance metrics."""
        metadata = checkpoint_manager.get_metadata()
        splits = get_dataset_splits()
        test_samples = splits.get("test", [])

        # If test samples exist, run live test evaluation
        if test_samples:
            live_metrics = evaluate_dataset_samples(
                inference_fn=lambda code: defect_inference_engine.predict_defect(code).defect_probability,
                samples=test_samples
            )
            return {
                "model_name": metadata.get("model_name", "microsoft/codebert-base"),
                "status": "EVALUATED",
                "test_split_metrics": live_metrics,
                "validation_benchmark_metrics": metadata.get("metrics", {}),
                "num_classes": 2,
                "task": "binary_defect_classification"
            }

        return {
            "model_name": metadata.get("model_name", "microsoft/codebert-base"),
            "status": "READY",
            "validation_benchmark_metrics": metadata.get("metrics", {}),
            "num_classes": 2,
            "task": "binary_defect_classification"
        }


defect_service = DefectIntelligenceService()
