import pytest
from fastapi import status


class TestBasicSetup:
    """Basic tests to verify the test setup is working correctly"""

    def test_health_check(self, client):
        """Test that the application is running and responding"""
        response = client.get("/")
        # The root endpoint might not exist, but we should get some response
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_database_connection(self, db_session):
        """Test that database connection is working"""
        # Try to execute a simple query
        from sqlalchemy import text

        result = db_session.execute(text("SELECT 1"))
        assert result is not None

    def test_client_setup(self, client):
        """Test that the test client is properly configured"""
        # Test that we can make a request
        response = client.get("/tasks/")
        assert response.status_code == status.HTTP_200_OK

    def test_mock_user_fixture(self, mock_user):
        """Test that the mock user fixture works"""
        assert mock_user.email == "test@example.com"

    def test_mock_llm_service_fixture(self, mock_llm_service):
        """Test that the mock LLM service fixture works"""
        assert "generate_tasks" in mock_llm_service
        assert "evaluate_student_answer" in mock_llm_service
        assert "generate_document_title" in mock_llm_service

    def test_temp_file_fixture(self, temp_file):
        """Test that the temp file fixture works"""
        import os

        assert os.path.exists(temp_file)
        with open(temp_file, "r") as f:
            content = f.read()
        assert "test document content" in content.lower()


class TestPytestMarkers:
    """Test that pytest markers are working correctly"""

    @pytest.mark.crud
    def test_crud_marker(self):
        """Test that CRUD marker works"""
        assert True

    @pytest.mark.llm
    def test_llm_marker(self):
        """Test that LLM marker works"""
        assert True

    @pytest.mark.auth
    def test_auth_marker(self):
        """Test that auth marker works"""
        assert True

    @pytest.mark.slow
    def test_slow_marker(self):
        """Test that slow marker works"""
        assert True

    @pytest.mark.unit
    def test_unit_marker(self):
        """Test that unit marker works"""
        assert True

    @pytest.mark.integration
    def test_integration_marker(self):
        """Test that integration marker works"""
        assert True
