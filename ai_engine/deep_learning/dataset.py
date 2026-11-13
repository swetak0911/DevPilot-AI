"""
CodeXGLUE Defect Detection Dataset Loader & PyTorch Dataset Interface.
Loads JSONL records, performs tokenization, sequence truncation, attention mask construction,
and PyTorch tensor batching.
"""
import os
import json
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

from ai_engine.deep_learning.config import dl_config


@dataclass
class DefectSample:
    idx: int
    func: str
    target: int  # 0: Clean, 1: Defective / Bug-prone


class CodeTokenizer:
    """
    Tokenizer abstraction supporting HuggingFace CodeBERT tokenizer
    with a fallback subword tokenizer to allow zero-dependency operation.
    """

    def __init__(self, max_length: int = 256):
        self.max_length = max_length
        self._hf_tokenizer = None
        try:
            from transformers import AutoTokenizer
            self._hf_tokenizer = AutoTokenizer.from_pretrained(dl_config.model_name_or_path)
        except Exception:
            self._hf_tokenizer = None

    def encode(self, code_text: str) -> Dict[str, List[int]]:
        """Encodes code text into input_ids and attention_mask."""
        if self._hf_tokenizer:
            encoded = self._hf_tokenizer(
                code_text,
                padding="max_length",
                truncation=True,
                max_length=self.max_length,
                return_tensors=None
            )
            return {
                "input_ids": encoded["input_ids"],
                "attention_mask": encoded["attention_mask"]
            }

        # Deterministic fallback tokenizer
        tokens = re.findall(r"[A-Za-z0-9_]+|[^\s\w]", code_text)
        # Vocabulary mapping with hashing
        vocab_size = 50265  # RoBERTa / CodeBERT vocabulary size
        input_ids = [0]  # <s> (CLS token)

        for tok in tokens[:self.max_length - 2]:
            tok_id = (hash(tok) % (vocab_size - 10)) + 10
            input_ids.append(tok_id)

        input_ids.append(2)  # </s> (SEP token)
        seq_len = len(input_ids)

        # Pad to max_length
        attention_mask = [1] * seq_len + [0] * (self.max_length - seq_len)
        input_ids = input_ids + [1] * (self.max_length - seq_len)  # 1 is <pad> in RoBERTa

        return {
            "input_ids": input_ids[:self.max_length],
            "attention_mask": attention_mask[:self.max_length]
        }


def load_jsonl_samples(file_path: str) -> List[DefectSample]:
    """Reads a CodeXGLUE defect detection JSONL file."""
    if not os.path.exists(file_path):
        return []

    samples = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            samples.append(DefectSample(
                idx=data.get("idx", len(samples)),
                func=data.get("func", ""),
                target=int(data.get("target", 0))
            ))
    return samples


def get_dataset_splits(data_dir: Optional[str] = None) -> Dict[str, List[DefectSample]]:
    """Loads train, valid, and test splits from the data directory."""
    d = data_dir or dl_config.data_dir
    return {
        "train": load_jsonl_samples(os.path.join(d, "train.jsonl")),
        "valid": load_jsonl_samples(os.path.join(d, "valid.jsonl")),
        "test": load_jsonl_samples(os.path.join(d, "test.jsonl"))
    }


# PyTorch Dataset Interface (graceful if torch is installed)
try:
    import torch
    from torch.utils.data import Dataset

    class CodeXGlueDefectDataset(Dataset):
        """PyTorch Dataset for CodeBERT Defect Detection."""

        def __init__(self, samples: List[DefectSample], tokenizer: CodeTokenizer):
            self.samples = samples
            self.tokenizer = tokenizer

        def __len__(self) -> int:
            return len(self.samples)

        def __getitem__(self, idx: int) -> Dict[str, Any]:
            sample = self.samples[idx]
            encoded = self.tokenizer.encode(sample.func)
            return {
                "idx": sample.idx,
                "input_ids": torch.tensor(encoded["input_ids"], dtype=torch.long),
                "attention_mask": torch.tensor(encoded["attention_mask"], dtype=torch.long),
                "labels": torch.tensor(sample.target, dtype=torch.long)
            }

except ImportError:
    class CodeXGlueDefectDataset:  # type: ignore
        """Fallback representation when PyTorch is not yet installed."""
        def __init__(self, samples: List[DefectSample], tokenizer: CodeTokenizer):
            self.samples = samples
            self.tokenizer = tokenizer
        def __len__(self) -> int:
            return len(self.samples)
