import pytest
from uuid import uuid4
from fastapi import status
from sqlmodel import Session, select
from unittest.mock import patch, MagicMock
from datetime import timedelta

from auth.models import User
from auth.schemas import UserCreate, UserUpdate


class TestAuthAuthentication:
    """Test authentication endpoints"""

    @pytest.mark.auth
    def test_login_success(self, client, db_session):
        """Test successful login"""
        # Create a test user
        user = User(
            id=str(uuid4()),
            username="testuser",
            email="test@example.com",
            hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4tbQJ5J5e",  # "password"
            is_active=True,
            is_superuser=False,
        )
        db_session.add(user)
        db_session.commit()

        # Mock the authenticate_user function
        with patch("auth.service.authenticate_user") as mock_auth:
            mock_auth.return_value = user

            response = client.post(
                "/auth/token",
                data={
                    "username": "testuser",
                    "password": "password"
                }
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["message"] == "Login successful"

            # Check that cookie was set
            cookies = response.cookies
            assert "access_token" in cookies

    @pytest.mark.auth
    def test_login_invalid_credentials(self, client, db_session):
        """Test login with invalid credentials"""
        with patch("auth.service.authenticate_user") as mock_auth:
            mock_auth.return_value = None

            response = client.post(
                "/auth/token",
                data={
                    "username": "wronguser",
                    "password": "wrongpassword"
                }
            )

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert response.json()["detail"] == "Incorrect username or password"

    @pytest.mark.auth
    def test_login_missing_credentials(self, client):
        """Test login with missing credentials"""
        response = client.post("/auth/token")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.auth
    def test_logout_success(self, client, mock_current_user):
        """Test successful logout"""
        response = client.post("/auth/logout")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Logout successful"

        # Check that cookie was cleared
        cookies = response.cookies
        assert "access_token" in cookies
        assert cookies["access_token"].value == ""

    @pytest.mark.auth
    def test_logout_without_authentication(self, client):
        """Test logout without authentication"""
        response = client.post("/auth/logout")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthUserManagement:
    """Test user management endpoints"""

    @pytest.mark.auth
    @pytest.mark.crud
    def test_create_user_success(self, client, db_session):
        """Test creating a user successfully"""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "newpassword123"
        }

        with patch("auth.service.create_user") as mock_create:
            mock_user = User(
                id=str(uuid4()),
                username="newuser",
                email="newuser@example.com",
                hashed_password="hashed_password",
                is_active=True,
                is_superuser=False,
            )
            mock_create.return_value = mock_user

            response = client.post("/auth/users/", json=user_data)
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["username"] == "newuser"
            assert data["email"] == "newuser@example.com"

    @pytest.mark.auth
    def test_create_user_duplicate_username(self, client, db_session):
        """Test creating a user with duplicate username"""
        user_data = {
            "username": "existinguser",
            "email": "newuser@example.com",
            "password": "newpassword123"
        }

        with patch("auth.service.create_user") as mock_create:
            mock_create.side_effect = ValueError("Username already exists")

            response = client.post("/auth/users/", json=user_data)
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.auth
    def test_create_user_invalid_data(self, client):
        """Test creating a user with invalid data"""
        user_data = {
            "username": "",  # Invalid empty username
            "email": "invalid-email",  # Invalid email
            "password": "123"  # Too short password
        }

        response = client.post("/auth/users/", json=user_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.auth
    @pytest.mark.crud
    def test_get_current_user_success(self, client, db_session, mock_current_user):
        """Test getting current user information"""
        with patch("auth.service.get_user_by_username") as mock_get_user:
            mock_get_user.return_value = mock_current_user

            response = client.get("/auth/users/me/")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"

    @pytest.mark.auth
    def test_get_current_user_not_found(self, client, db_session, mock_current_user):
        """Test getting current user when user doesn't exist in database"""
        with patch("auth.service.get_user_by_username") as mock_get_user:
            mock_get_user.return_value = None

            response = client.get("/auth/users/me/")
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.json()["detail"] == "User not found"

    @pytest.mark.auth
    def test_get_current_user_without_authentication(self, client):
        """Test getting current user without authentication"""
        response = client.get("/auth/users/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.auth
    @pytest.mark.crud
    def test_get_users_success(self, client, db_session, mock_current_user):
        """Test getting all users with pagination"""
        with patch("auth.service.get_users") as mock_get_users:
            mock_users = [
                User(
                    id=str(uuid4()),
                    username="user1",
                    email="user1@example.com",
                    hashed_password="hashed_password",
                    is_active=True,
                    is_superuser=False,
                ),
                User(
                    id=str(uuid4()),
                    username="user2",
                    email="user2@example.com",
                    hashed_password="hashed_password",
                    is_active=True,
                    is_superuser=False,
                )
            ]
            mock_get_users.return_value = mock_users

            response = client.get("/auth/users/?skip=0&limit=10")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["users"]) == 2
            assert data["total"] == 2

    @pytest.mark.auth
    def test_get_users_without_authentication(self, client):
        """Test getting users without authentication"""
        response = client.get("/auth/users/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.auth
    @pytest.mark.crud
    def test_get_user_by_id_success(self, client, db_session, mock_current_user):
        """Test getting a user by ID"""
        user_id = str(uuid4())
        with patch("auth.service.get_user_by_id") as mock_get_user:
            mock_user = User(
                id=user_id,
                username="testuser",
                email="test@example.com",
                hashed_password="hashed_password",
                is_active=True,
                is_superuser=False,
            )
            mock_get_user.return_value = mock_user

            response = client.get(f"/auth/users/{user_id}")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == user_id
            assert data["username"] == "testuser"

    @pytest.mark.auth
    def test_get_user_by_id_not_found(self, client, db_session, mock_current_user):
        """Test getting a user by ID that doesn't exist"""
        user_id = str(uuid4())
        with patch("auth.service.get_user_by_id") as mock_get_user:
            mock_get_user.return_value = None

            response = client.get(f"/auth/users/{user_id}")
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.json()["detail"] == "User not found"

    @pytest.mark.auth
    @pytest.mark.crud
    def test_get_user_by_username_success(self, client, db_session, mock_current_user):
        """Test getting a user by username"""
        with patch("auth.service.get_user_by_username") as mock_get_user:
            mock_user = User(
                id=str(uuid4()),
                username="testuser",
                email="test@example.com",
                hashed_password="hashed_password",
                is_active=True,
                is_superuser=False,
            )
            mock_get_user.return_value = mock_user

            response = client.get("/auth/users/username/testuser")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["username"] == "testuser"

    @pytest.mark.auth
    def test_get_user_by_username_not_found(self, client, db_session, mock_current_user):
        """Test getting a user by username that doesn't exist"""
        with patch("auth.service.get_user_by_username") as mock_get_user:
            mock_get_user.return_value = None

            response = client.get("/auth/users/username/nonexistent")
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.json()["detail"] == "User not found"

    @pytest.mark.auth
    @pytest.mark.crud
    def test_update_user_success(self, client, db_session, mock_current_user):
        """Test updating a user successfully"""
        user_id = str(uuid4())
        update_data = {
            "email": "updated@example.com",
            "is_active": False
        }

        with patch("auth.service.update_user") as mock_update:
            mock_user = User(
                id=user_id,
                username="testuser",
                email="updated@example.com",
                hashed_password="hashed_password",
                is_active=False,
                is_superuser=False,
            )
            mock_update.return_value = mock_user

            response = client.put(f"/auth/users/{user_id}", json=update_data)
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["email"] == "updated@example.com"
            assert data["is_active"] is False

    @pytest.mark.auth
    def test_update_user_not_found(self, client, db_session, mock_current_user):
        """Test updating a user that doesn't exist"""
        user_id = str(uuid4())
        update_data = {"email": "updated@example.com"}

        with patch("auth.service.update_user") as mock_update:
            mock_update.return_value = None

            response = client.put(f"/auth/users/{user_id}", json=update_data)
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.json()["detail"] == "User not found"

    @pytest.mark.auth
    def test_update_user_invalid_data(self, client, mock_current_user):
        """Test updating a user with invalid data"""
        user_id = str(uuid4())
        update_data = {"email": "invalid-email"}

        response = client.put(f"/auth/users/{user_id}", json=update_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.auth
    @pytest.mark.crud
    def test_delete_user_success(self, client, db_session, mock_current_user):
        """Test deleting a user successfully"""
        user_id = str(uuid4())

        with patch("auth.service.delete_user") as mock_delete:
            mock_delete.return_value = True

            response = client.delete(f"/auth/users/{user_id}")
            assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.auth
    def test_delete_user_not_found(self, client, db_session, mock_current_user):
        """Test deleting a user that doesn't exist"""
        user_id = str(uuid4())

        with patch("auth.service.delete_user") as mock_delete:
            mock_delete.return_value = False

            response = client.delete(f"/auth/users/{user_id}")
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.json()["detail"] == "User not found"


class TestAuthEdgeCases:
    """Test authentication edge cases and error handling"""

    @pytest.mark.auth
    def test_login_service_error(self, client, db_session):
        """Test login when authentication service fails"""
        with patch("auth.service.authenticate_user") as mock_auth:
            mock_auth.side_effect = Exception("Authentication service error")

            response = client.post(
                "/auth/token",
                data={
                    "username": "testuser",
                    "password": "password"
                }
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.auth
    def test_create_user_service_error(self, client, db_session):
        """Test creating user when service fails"""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "newpassword123"
        }

        with patch("auth.service.create_user") as mock_create:
            mock_create.side_effect = Exception("User service error")

            response = client.post("/auth/users/", json=user_data)
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.auth
    def test_get_users_service_error(self, client, db_session, mock_current_user):
        """Test getting users when service fails"""
        with patch("auth.service.get_users") as mock_get_users:
            mock_get_users.side_effect = Exception("User service error")

            response = client.get("/auth/users/")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.auth
    def test_update_user_service_error(self, client, db_session, mock_current_user):
        """Test updating user when service fails"""
        user_id = str(uuid4())
        update_data = {"email": "updated@example.com"}

        with patch("auth.service.update_user") as mock_update:
            mock_update.side_effect = Exception("User service error")

            response = client.put(f"/auth/users/{user_id}", json=update_data)
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.auth
    def test_delete_user_service_error(self, client, db_session, mock_current_user):
        """Test deleting user when service fails"""
        user_id = str(uuid4())

        with patch("auth.service.delete_user") as mock_delete:
            mock_delete.side_effect = Exception("User service error")

            response = client.delete(f"/auth/users/{user_id}")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.auth
    def test_invalid_token_format(self, client):
        """Test accessing protected endpoints with invalid token format"""
        headers = {"Authorization": "Bearer invalid_token_format"}
        response = client.get("/auth/users/me/", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.auth
    def test_expired_token(self, client):
        """Test accessing protected endpoints with expired token"""
        # This would require mocking the JWT token validation
        # For now, we'll test the basic structure
        headers = {"Authorization": "Bearer expired_token"}
        response = client.get("/auth/users/me/", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED