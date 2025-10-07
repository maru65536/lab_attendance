from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient):
    response = client.get('/api/kbd_ir/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'
