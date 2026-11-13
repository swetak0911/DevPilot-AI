"""
Deep Learning Configuration and Hyperparameters for CodeBERT Defect Classification.
"""
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DLConfig:
    # Model Architecture
    model_name_or_path: str = "microsoft/codebert-base"
    num_classes: int = 2
    hidden_size: int = 768
    classifier_dropout: float = 0.1
    max_seq_length: int = 256

    # Training Hyperparameters
    batch_size: int = 16
    learning_rate: float = 2e-5
    weight_decay: float = 0.01
    adam_epsilon: float = 1e-8
    num_train_epochs: int = 5
    warmup_ratio: float = 0.1
    max_grad_norm: float = 1.0
    seed: int = 42

    # Inference & Decision Thresholds
    defect_threshold: float = 0.50
    high_risk_threshold: float = 0.75

    # Directory Paths
    base_dir: str = os.path.dirname(os.path.abspath(__file__))
    data_dir: str = os.path.join(base_dir, "data")
    checkpoint_dir: str = os.path.join(base_dir, "checkpoints")
    best_model_path: str = os.path.join(checkpoint_dir, "best_model.pt")

    # Hardware Acceleration
    device: str = "cpu"

    def __post_init__(self):
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        try:
            import torch
            if torch.cuda.is_available():
                self.device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"
        except ImportError:
            self.device = "cpu"


dl_config = DLConfig()
