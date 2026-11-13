"""
DevPilot AI - Deployment Risk Telemetry & Data Collector
Collects, extracts, and generates code churn, testing ratio, author experience,
and workflow complexity telemetry for training deployment risk classifiers.
"""
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple, Optional
import random
import math
import os


@dataclass
class DeploymentDataPoint:
    commit_sha: str
    lines_added: int
    lines_deleted: int
    total_churn: int
    files_changed_count: int
    test_files_count: int
    test_files_ratio: float
    config_files_modified: int
    dependency_files_modified: int
    author_prior_success_rate: float
    time_of_day_utc: int
    is_weekend: int
    workflow_jobs_count: int
    has_docker_step: int
    historical_failure_rate: float
    failed: int  # 1 = Deployment Failed, 0 = Deployment Succeeded

    @property
    def failed_deployment(self) -> int:
        return self.failed

    def to_feature_vector(self) -> List[float]:
        return [
            float(self.lines_added),
            float(self.lines_deleted),
            float(self.total_churn),
            float(self.files_changed_count),
            float(self.test_files_count),
            float(self.test_files_ratio),
            float(self.config_files_modified),
            float(self.dependency_files_modified),
            float(self.author_prior_success_rate),
            float(self.time_of_day_utc),
            float(self.is_weekend),
            float(self.workflow_jobs_count),
            float(self.has_docker_step),
            float(self.historical_failure_rate)
        ]


class DeploymentDataCollector:
    """Extracts and builds training datasets from continuous deployment telemetry."""

    FEATURE_NAMES = [
        "lines_added",
        "lines_deleted",
        "total_churn",
        "files_changed_count",
        "test_files_count",
        "test_files_ratio",
        "config_files_modified",
        "dependency_files_modified",
        "author_prior_success_rate",
        "time_of_day_utc",
        "is_weekend",
        "workflow_jobs_count",
        "has_docker_step",
        "historical_failure_rate"
    ]

    def generate_synthetic_dataset(
        self,
        n_samples: int = 500,
        seed: int = 42
    ) -> List[DeploymentDataPoint]:
        """
        Generates realistic, telemetry-correlated deployment data points.
        Failure probabilities reflect real-world empirical DevOps risk patterns:
        - Massive code churn without accompanying tests
        - Unpinned dependency manifest updates
        - Friday evening / weekend deployments
        - High historical branch failure rates
        """
        rng = random.Random(seed)
        dataset: List[DeploymentDataPoint] = []

        for i in range(n_samples):
            sha = f"c{rng.getrandbits(32):08x}"
            is_weekend = 1 if rng.random() < 0.20 else 0
            time_of_day = rng.randint(0, 23)

            # Code churn characteristics
            files_count = max(1, int(rng.expovariate(1.0 / 8.0)))
            files_count = min(files_count, 60)

            # Test files ratio
            has_tests = rng.random() > 0.35
            test_files = max(0, int(files_count * rng.uniform(0.1, 0.6))) if has_tests else 0
            test_ratio = round(test_files / files_count, 3)

            lines_added = int(rng.expovariate(1.0 / 120.0)) + 5
            lines_deleted = int(rng.expovariate(1.0 / 60.0))
            total_churn = lines_added + lines_deleted

            config_files = 1 if rng.random() < 0.25 else 0
            dep_files = 1 if rng.random() < 0.18 else 0

            author_success = round(rng.betavariate(8, 2), 3)  # Centered around 0.80
            jobs_count = rng.choice([2, 3, 4, 5])
            has_docker = 1 if rng.random() < 0.65 else 0
            branch_fail_rate = round(rng.betavariate(2, 6), 3)  # Centered around 0.25

            # Latent failure logit
            # High churn (+), low tests (-), dep changes (+), weekend (+), low author success (-)
            churn_risk = min(total_churn / 300.0, 3.0)
            test_buffer = test_ratio * 3.5
            dep_risk = 1.8 if dep_files and test_files == 0 else (0.6 if dep_files else 0.0)
            weekend_risk = 1.0 if is_weekend else 0.0
            author_penalty = (1.0 - author_success) * 3.0
            history_risk = branch_fail_rate * 3.2

            raw_logit = -2.2 + churn_risk - test_buffer + dep_risk + weekend_risk + author_penalty + history_risk
            latent_score = raw_logit + rng.gauss(0, 0.45)

            # Ground-truth failure label
            failed = 1 if latent_score >= 0.0 else 0

            point = DeploymentDataPoint(
                commit_sha=sha,
                lines_added=lines_added,
                lines_deleted=lines_deleted,
                total_churn=total_churn,
                files_changed_count=files_count,
                test_files_count=test_files,
                test_files_ratio=test_ratio,
                config_files_modified=config_files,
                dependency_files_modified=dep_files,
                author_prior_success_rate=author_success,
                time_of_day_utc=time_of_day,
                is_weekend=is_weekend,
                workflow_jobs_count=jobs_count,
                has_docker_step=has_docker,
                historical_failure_rate=branch_fail_rate,
                failed=failed
            )
            dataset.append(point)

        return dataset

    def to_feature_matrix(
        self,
        data_points: List[DeploymentDataPoint]
    ) -> Tuple[List[List[float]], List[int]]:
        """Converts data points to numerical feature matrix X and target vector y."""
        X = [p.to_feature_vector() for p in data_points]
        y = [p.failed for p in data_points]
        return X, y


deployment_data_collector = DeploymentDataCollector()
