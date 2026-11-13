"""Repository Management and Search Tests."""


def test_list_repositories(client):
    response = client.get("/api/repositories")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["name"] == "DevPilot-AI"


def test_connect_repository(client):
    payload = {
        "github_repo_url": "https://github.com/swetak0911/DevPilot-AI"
    }
    response = client.post("/api/repositories/connect", json=payload)
    assert response.status_code in (200, 201)
    data = response.json()
    assert data["name"] == "DevPilot-AI"


def test_repository_file_tree(client):
    repos = client.get("/api/repositories").json()
    repo_id = repos[0]["id"]

    response = client.get(f"/api/repositories/{repo_id}/tree")
    assert response.status_code == 200
    tree = response.json()
    assert len(tree) >= 1
    assert any(node["name"] == "backend" for node in tree)


def test_code_search(client):
    repos = client.get("/api/repositories").json()
    repo_id = repos[0]["id"]

    response = client.get(f"/api/repositories/{repo_id}/search?q=create_access_token")
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert results[0]["similarity_score"] > 0
