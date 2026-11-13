"""
Model Evaluation Metrics for CodeBERT Defect Classification.
Computes Accuracy, Precision, Recall, F1-score, Specificity, Confusion Matrix, and ROC stats.
"""
from typing import List, Dict, Any, Optional, Tuple


def compute_classification_metrics(
    predictions: List[int],
    labels: List[int],
    probabilities: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Computes rigorous classification metrics from binary predictions and ground truth labels.
    """
    if not predictions or not labels or len(predictions) != len(labels):
        return {
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "confusion_matrix": {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
        }

    tp = 0
    fp = 0
    fn = 0
    tn = 0

    for pred, label in zip(predictions, labels):
        if pred == 1 and label == 1:
            tp += 1
        elif pred == 1 and label == 0:
            fp += 1
        elif pred == 0 and label == 1:
            fn += 1
        else:
            tn += 1

    total = tp + fp + fn + tn
    accuracy = round((tp + tn) / total, 4) if total > 0 else 0.0
    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    specificity = round(tn / (tn + fp), 4) if (tn + fp) > 0 else 0.0

    if precision + recall > 0:
        f1 = round(2 * (precision * recall) / (precision + recall), 4)
    else:
        f1 = 0.0

    balanced_accuracy = round((recall + specificity) / 2, 4)

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "specificity": specificity,
        "balanced_accuracy": balanced_accuracy,
        "total_samples": total,
        "confusion_matrix": {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn
        }
    }


def evaluate_dataset_samples(
    inference_fn,
    samples: List[Any],
    threshold: float = 0.50
) -> Dict[str, Any]:
    """
    Evaluates an inference function against a list of DefectSample objects.
    """
    preds = []
    labels = []
    probs = []

    for sample in samples:
        prob = inference_fn(sample.func)
        pred = 1 if prob >= threshold else 0
        preds.append(pred)
        labels.append(sample.target)
        probs.append(prob)

    metrics = compute_classification_metrics(preds, labels, probs)
    return metrics
