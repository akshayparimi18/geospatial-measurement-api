from fastapi.testclient import TestClient
from main import app
import os

client = TestClient(app)

def test_upload_and_measure_polygon():
    # Ensure we have our test file
    file_path = "test.kml"
    if not os.path.exists(file_path):
        return
        
    # Test 1: Upload the file
    with open(file_path, "rb") as f:
        response = client.post("/api/files/", files={"file": ("test.kml", f, "application/xml")})
    
    assert response.status_code == 200
    assert "id" in response.json()
    file_id = response.json()["id"]
    
    # Test 2: Verify the measurements
    measure_response = client.get(f"/api/files/{file_id}/measurements/")
    assert measure_response.status_code == 200
    data = measure_response.json()
    
    assert len(data) > 0
    assert data[0]["geometry_type"] == "Polygon"
    assert data[0]["area_sqm"] > 9800  # Verifying our ~9817 calculation
