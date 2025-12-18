import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.api.main import app
import io

client = TestClient(app)

@pytest.fixture
def mock_gemini_response():
    with patch("google.generativeai.GenerativeModel") as mock_model_cls:
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "A beautiful design with vibrant colors."
        mock_model.generate_content.return_value = mock_response
        mock_model_cls.return_value = mock_model
        yield mock_model

def test_describe_endpoint(mock_gemini_response):
    # Create a dummy image file
    import base64
    # 1x1 pixel red PNG
    png_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
    file = io.BytesIO(png_data)
    
    response = client.post(
        "/describe",
        files={"file": ("test.png", file, "image/png")}
    )
    
    if response.status_code != 200:
        print(f"Response: {response.text}")
    assert response.status_code == 200
    assert response.json() == {"description": "A beautiful design with vibrant colors."}

def test_describe_endpoint_invalid_file():
    file_content = b"fake text content"
    file = io.BytesIO(file_content)
    
    response = client.post(
        "/describe",
        files={"file": ("test.txt", file, "text/plain")}
    )
    
    assert response.status_code == 400
    assert response.json()["detail"] == "File must be an image"
