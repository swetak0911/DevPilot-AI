"""Monitoring and DevOps Endpoint Tests."""


def test_overview_analytics(client):
    response = client.get("/api/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert "connected_repositories" in data
    assert "total_tasks" in data


def test_cicd_generate(client):
    payload = {
        "repository_id": "test-repo",
        "include_linting": True,
        "include_tests": True
    }
    response = client.post("/api/cicd/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "workflow_yaml" in data
    assert "actions/checkout@v4" in data["workflow_yaml"]


def test_docker_generate(client):
    payload = {
        "repository_id": "test-repo",
        "target_port": 8000
    }
    response = client.post("/api/docker/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "FROM python:3.11-slim" in data["dockerfile_content"]


def test_deployment_risk(client):
    payload = {
        "repository_id": "test-repo",
        "files_changed": 4,
        "lines_added": 40,
        "lines_deleted": 5,
        "dependencies_changed": 0,
        "historical_failure_rate": 0.05
    }
    response = client.post("/api/ml/deployment-risk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "risk_score" in data
    assert "risk_level" in data
