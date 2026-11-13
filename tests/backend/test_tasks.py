"""Autonomous Task Lifecycle Tests."""


def test_create_and_manage_task(client):
    repos = client.get("/api/repositories").json()
    repo_id = repos[0]["id"]

    # Create task
    task_payload = {
        "repository_id": repo_id,
        "title": "Fix token validation boundary condition",
        "instruction": "Inspect auth module, fix validation bug, execute pytest suite, and prepare PR.",
        "task_type": "BUG_FIX"
    }
    response = client.post("/api/tasks", json=task_payload)
    assert response.status_code == 201
    task = response.json()
    assert task["status"] == "PENDING"
    task_id = task["id"]

    # Start task
    start_res = client.post(f"/api/tasks/{task_id}/start")
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "RUNNING"

    # Get logs
    logs_res = client.get(f"/api/tasks/{task_id}/logs")
    assert logs_res.status_code == 200
    assert len(logs_res.json()["logs"]) >= 1

    # Get diff
    diff_res = client.get(f"/api/tasks/{task_id}/diff")
    assert diff_res.status_code == 200
    assert diff_res.json()["has_patches"] is True

    # Approve task
    appr_res = client.post(f"/api/tasks/{task_id}/approve", json={"approved": True})
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "COMPLETED"

    # Create PR
    pr_res = client.post(f"/api/tasks/{task_id}/create-pr")
    assert pr_res.status_code == 200
    assert "pr_url" in pr_res.json()
