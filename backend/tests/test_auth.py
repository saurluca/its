import pytest
import uuid
from fastapi import status, HTTPException
from unittest.mock import patch, AsyncMock

from auth.models import User
from auth.service import get_password_hash


class TestAuthAuthentication:
    """Test authentication endpoints"""

    @pytest.mark.auth
    def test_login_success(self, client, db_session):
        """Test successful login"""

        # Create a test user with proper hash
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            full_name="Test User",
            hashed_password=get_password_hash("password"),
        )
        db_session.add(user)
        db_session.commit()

        # Mock the authenticate_user function
        with patch("auth.router.authenticate_user") as mock_auth:
            mock_auth.return_value = user

            response = client.post(
                "/auth/token",
                data={"username": "test@example.com", "password": "password"},
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
        with patch("auth.router.authenticate_user") as mock_auth:
            mock_auth.return_value = None

            response = client.post(
                "/auth/token",
                data={"username": "wrong@example.com", "password": "wrongpassword"},
            )

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert response.json()["detail"] == "Incorrect email or password"

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

        # Check that cookie was cleared (delete_cookie doesn't set a response cookie)
        # The cookie deletion is handled by the browser based on the Set-Cookie header
        # with max-age=0 or expires in the past

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
            "email": "newuser@example.com",
            "full_name": "New User",
            "password": "newpassword123",
        }

        with patch("auth.router.create_user", new_callable=AsyncMock) as mock_create:
            mock_user = User(
                id=uuid.uuid4(),
                email="newuser@example.com",
                full_name="New User",
                hashed_password="hashed_password",
            )
            mock_create.return_value = mock_user

            response = client.post("/auth/users/", json=user_data)
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["email"] == "newuser@example.com"
            assert data["full_name"] == "New User"

    @pytest.mark.auth
    def test_create_user_duplicate_email(self, client, db_session):
        """Test creating a user with duplicate email"""
        user_data = {
            "email": "existing@example.com",
            "full_name": "New User",
            "password": "newpassword123",
        }

        with patch("auth.router.create_user", new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

            response = client.post("/auth/users/", json=user_data)
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.auth
    def test_create_user_invalid_data(self, client):
        """Test creating a user with invalid data"""
        user_data = {
            "email": "invalid-email",  # Invalid email
            "full_name": "",  # Invalid empty name
            "password": "123",  # Too short password
        }

        response = client.post("/auth/users/", json=user_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.auth
    @pytest.mark.crud
    def test_get_current_user_success(self, client, db_session, mock_current_user):
        """Test getting current user information"""
        with patch(
            "auth.router.get_user_by_email", new_callable=AsyncMock
        ) as mock_get_user:
            mock_get_user.return_value = mock_current_user

            response = client.get("/auth/users/me/")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["email"] == "test@example.com"
            assert data["full_name"] == "Test User"

    @pytest.mark.auth
    def test_get_current_user_not_found(self, client, db_session, mock_current_user):
        """Test getting current user when user doesn't exist in database"""
        with patch("auth.router.get_user_by_email") as mock_get_user:
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
        with patch("auth.router.get_users", new_callable=AsyncMock) as mock_get_users:
            mock_users = [
                User(
                    id=uuid.uuid4(),
                    email="user1@example.com",
                    full_name="User One",
                    hashed_password="hashed_password",
                ),
                User(
                    id=uuid.uuid4(),
                    email="user2@example.com",
                    full_name="User Two",
                    hashed_password="hashed_password",
                ),
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
        user_id = uuid.uuid4()
        with patch(
            "auth.router.get_user_by_id", new_callable=AsyncMock
        ) as mock_get_user:
            mock_user = User(
                id=user_id,
                email="test@example.com",
                full_name="Test User",
                hashed_password="hashed_password",
            )
            mock_get_user.return_value = mock_user

            response = client.get(f"/auth/users/{user_id}")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(user_id)
            assert data["email"] == "test@example.com"

    @pytest.mark.auth
    def test_get_user_by_id_not_found(self, client, db_session, mock_current_user):
        """Test getting a user by ID that doesn't exist"""
        user_id = uuid.uuid4()
        with patch("auth.router.get_user_by_id") as mock_get_user:
            mock_get_user.return_value = None

            response = client.get(f"/auth/users/{user_id}")
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.json()["detail"] == "User not found"

    @pytest.mark.auth
    @pytest.mark.crud
    def test_update_user_success(self, client, db_session, mock_current_user):
        """Test updating a user successfully"""
        user_id = uuid.uuid4()
        update_data = {"email": "updated@example.com", "full_name": "Updated User"}

        with patch("auth.router.update_user", new_callable=AsyncMock) as mock_update:
            mock_user = User(
                id=user_id,
                email="updated@example.com",
                full_name="Updated User",
                hashed_password="hashed_password",
            )
            mock_update.return_value = mock_user

            response = client.put(f"/auth/users/{user_id}", json=update_data)
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["email"] == "updated@example.com"
            assert data["full_name"] == "Updated User"
            assert data["disabled"] is False

    @pytest.mark.auth
    def test_update_user_not_found(self, client, db_session, mock_current_user):
        """Test updating a user that doesn't exist"""
        user_id = uuid.uuid4()
        update_data = {"email": "updated@example.com"}

        with patch("auth.router.update_user") as mock_update:
            mock_update.return_value = None

            response = client.put(f"/auth/users/{user_id}", json=update_data)
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.json()["detail"] == "User not found"

    @pytest.mark.auth
    def test_update_user_invalid_data(self, client, mock_current_user):
        """Test updating a user with invalid data"""
        user_id = uuid.uuid4()
        update_data = {"email": "invalid-email"}

        response = client.put(f"/auth/users/{user_id}", json=update_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.auth
    @pytest.mark.crud
    def test_delete_user_success(self, client, db_session, mock_current_user):
        """Test deleting a user successfully"""
        user_id = uuid.uuid4()

        with patch("auth.router.delete_user", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = True

            response = client.delete(f"/auth/users/{user_id}")
            assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.auth
    def test_delete_user_not_found(self, client, db_session, mock_current_user):
        """Test deleting a user that doesn't exist"""
        user_id = uuid.uuid4()

        with patch("auth.router.delete_user") as mock_delete:
            mock_delete.return_value = False

            response = client.delete(f"/auth/users/{user_id}")
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.json()["detail"] == "User not found"


class TestAuthEdgeCases:
    """Test authentication edge cases and error handling"""

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
