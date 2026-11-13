"""Health and Root Endpoint Tests."""


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "DevPilot AI"
    assert data["status"] == "OPERATIONAL"
    assert "health" in data


def test_health_check_endpoint(client):
    response = client.get("/api/monitoring/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["services"]["api_server"] == "ONLINE"
    assert data["services"]["database"] == "CONNECTED"
