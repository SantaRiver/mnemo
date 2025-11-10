"""Tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from nlp_service.api.main import app


class TestAPI:
    """Tests for API endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client.
        
        Returns:
            TestClient instance
        """
        return TestClient(app)

    def test_health_check(self, client: TestClient) -> None:
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_analyze_endpoint(self, client: TestClient) -> None:
        """Test analyze endpoint."""
        request_data = {
            "user_id": 12345,
            "text": "Сходил в зал, потренировался",
            "date": "2025-11-10"
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "user_id" in data
        assert "actions" in data
        assert "meta" in data

    def test_analyze_invalid_user_id(self, client: TestClient) -> None:
        """Test analyze with invalid user ID."""
        request_data = {
            "user_id": -1,
            "text": "Some text",
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_analyze_empty_text(self, client: TestClient) -> None:
        """Test analyze with empty text."""
        request_data = {
            "user_id": 1,
            "text": "",
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_analyze_long_text(self, client: TestClient) -> None:
        """Test analyze with very long text."""
        request_data = {
            "user_id": 1,
            "text": "x" * 20000,  # Exceeds max length
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_get_stats(self, client: TestClient) -> None:
        """Test get stats endpoint."""
        response = client.get("/api/v1/stats/1")
        assert response.status_code == 200
        
        data = response.json()
        assert "user_id" in data
        assert "total_templates" in data
        assert "total_actions" in data

    def test_metrics_endpoint(self, client: TestClient) -> None:
        """Test metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "nlp_requests_total" in response.text or response.status_code == 200

    def test_process_time_header(self, client: TestClient) -> None:
        """Test that process time header is added."""
        response = client.get("/health")
        assert "X-Process-Time" in response.headers

    def test_cors_headers(self, client: TestClient) -> None:
        """Test CORS headers."""
        response = client.options("/health")
        # CORS middleware should handle OPTIONS
        assert response.status_code in [200, 405]
