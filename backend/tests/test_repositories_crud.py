import pytest
import uuid
from fastapi import status
from sqlmodel import Session, select
from unittest.mock import patch, MagicMock

from repositories.models import Repository, RepositoryDocumentLink
from documents.models import Document


class TestRepositoriesCRUD:
    """Test CRUD operations for repositories endpoints"""

    @pytest.mark.crud
    def test_get_repositories_empty(self, client):
        """Test getting repositories when none exist"""
        response = client.get("/repositories/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @pytest.mark.crud
    def test_get_repositories_with_data(self, client, db_session):
        """Test getting repositories when repositories exist"""
        # Create repositories
        repo1 = Repository(
            id=uuid.uuid4(),
            name="Test Repository 1"
        )
        repo2 = Repository(
            id=uuid.uuid4(),
            name="Test Repository 2"
        )
        db_session.add(repo1)
        db_session.add(repo2)
        db_session.commit()

        response = client.get("/repositories/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert any(repo["name"] == "Test Repository 1" for repo in data)
        assert any(repo["name"] == "Test Repository 2" for repo in data)

    @pytest.mark.crud
    def test_get_repository_by_id_success(self, client, db_session):
        """Test getting a specific repository by ID"""
        repository = Repository(
            id=uuid.uuid4(),
            name="Test Repository"
        )
        db_session.add(repository)
        db_session.commit()

        response = client.get(f"/repositories/{repository.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(repository.id)
        assert data["name"] == "Test Repository"

    @pytest.mark.crud
    def test_get_repository_by_id_not_found(self, client):
        """Test getting a repository that doesn't exist"""
        fake_id = uuid.uuid4()
        response = client.get(f"/repositories/{fake_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Repository not found"

    @pytest.mark.crud
    def test_create_repository_success(self, client, db_session):
        """Test creating a repository successfully"""
        repository_data = {
            "name": "New Repository"
        }

        response = client.post("/repositories/", json=repository_data)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "New Repository"

    @pytest.mark.crud
    def test_create_repository_invalid_data(self, client):
        """Test creating a repository with invalid data"""
        repository_data = {
            "name": ""  # Invalid empty name
        }

        response = client.post("/repositories/", json=repository_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.crud
    def test_update_repository_success(self, client, db_session):
        """Test updating a repository successfully"""
        repository = Repository(
            id=uuid.uuid4(),
            name="Original Name"
        )
        db_session.add(repository)
        db_session.commit()

        update_data = {
            "name": "Updated Name"
        }

        response = client.put(f"/repositories/{repository.id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"

    @pytest.mark.crud
    def test_update_repository_not_found(self, client):
        """Test updating a repository that doesn't exist"""
        fake_id = uuid.uuid4()
        update_data = {"name": "Updated Name"}

        response = client.put(f"/repositories/{fake_id}", json=update_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Repository not found"

    @pytest.mark.crud
    def test_delete_repository_success(self, client, db_session):
        """Test deleting a repository successfully"""
        repository = Repository(
            id=uuid.uuid4(),
            name="Test Repository"
        )
        db_session.add(repository)
        db_session.commit()

        response = client.delete(f"/repositories/{repository.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["ok"] is True

        # Verify repository is deleted
        response = client.get(f"/repositories/{repository.id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.crud
    def test_delete_repository_not_found(self, client):
        """Test deleting a repository that doesn't exist"""
        fake_id = uuid.uuid4()
        response = client.delete(f"/repositories/{fake_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Repository not found"


class TestRepositoryDocumentLinks:
    """Test repository-document link operations"""

    @pytest.mark.crud
    def test_create_repository_document_link_success(self, client, db_session):
        """Test creating a repository-document link successfully"""
        # Create a repository
        repository = Repository(
            id=uuid.uuid4(),
            name="Test Repository"
        )
        db_session.add(repository)
        db_session.commit()

        # Create a document
        document = Document(
            id=uuid.uuid4(),
            title="Test Document",
            source_file="test.txt",
            content="Test content"
        )
        db_session.add(document)
        db_session.commit()

        link_data = {
            "repository_id": str(repository.id),
            "document_id": str(document.id)
        }

        response = client.post("/repositories/links", json=link_data)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["repository_id"] == str(repository.id)
        assert data["document_id"] == str(document.id)

    @pytest.mark.crud
    def test_create_repository_document_link_repository_not_found(self, client, db_session):
        """Test creating a link with non-existent repository"""
        # Create a document
        document = Document(
            id=uuid.uuid4(),
            title="Test Document",
            source_file="test.txt",
            content="Test content"
        )
        db_session.add(document)
        db_session.commit()

        link_data = {
            "repository_id": str(uuid.uuid4()),  # Non-existent repository
            "document_id": str(document.id)
        }

        response = client.post("/repositories/links", json=link_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Repository not found"

    @pytest.mark.crud
    def test_create_repository_document_link_document_not_found(self, client, db_session):
        """Test creating a link with non-existent document"""
        # Create a repository
        repository = Repository(
            id=uuid.uuid4(),
            name="Test Repository"
        )
        db_session.add(repository)
        db_session.commit()

        link_data = {
            "repository_id": str(repository.id),
            "document_id": str(uuid.uuid4())  # Non-existent document
        }

        response = client.post("/repositories/links", json=link_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Document not found"

    @pytest.mark.crud
    def test_create_repository_document_link_already_exists(self, client, db_session):
        """Test creating a link that already exists"""
        # Create a repository
        repository = Repository(
            id=uuid.uuid4(),
            name="Test Repository"
        )
        db_session.add(repository)
        db_session.commit()

        # Create a document
        document = Document(
            id=uuid.uuid4(),
            title="Test Document",
            source_file="test.txt",
            content="Test content"
        )
        db_session.add(document)
        db_session.commit()

        # Create the link first
        link = RepositoryDocumentLink(
            id=uuid.uuid4(),
            repository_id=repository.id,
            document_id=document.id
        )
        db_session.add(link)
        db_session.commit()

        # Try to create the same link again
        link_data = {
            "repository_id": str(repository.id),
            "document_id": str(document.id)
        }

        response = client.post("/repositories/links", json=link_data)
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["detail"] == "Repository-Document link already exists"

    @pytest.mark.crud
    def test_delete_repository_document_link_success(self, client, db_session):
        """Test deleting a repository-document link successfully"""
        # Create a repository
        repository = Repository(
            id=uuid.uuid4(),
            name="Test Repository"
        )
        db_session.add(repository)
        db_session.commit()

        # Create a document
        document = Document(
            id=uuid.uuid4(),
            title="Test Document",
            source_file="test.txt",
            content="Test content"
        )
        db_session.add(document)
        db_session.commit()

        # Create the link
        link = RepositoryDocumentLink(
            id=uuid.uuid4(),
            repository_id=repository.id,
            document_id=document.id
        )
        db_session.add(link)
        db_session.commit()

        response = client.delete(f"/repositories/links/{repository.id}/{document.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["ok"] is True

    @pytest.mark.crud
    def test_delete_repository_document_link_not_found(self, client):
        """Test deleting a repository-document link that doesn't exist"""
        fake_repo_id = uuid.uuid4()
        fake_doc_id = uuid.uuid4()

        response = client.delete(f"/repositories/links/{fake_repo_id}/{fake_doc_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Repository-Document link not found"

    @pytest.mark.crud
    def test_get_repository_with_documents(self, client, db_session):
        """Test getting a repository with its linked documents"""
        # Create a repository
        repository = Repository(
            id=uuid.uuid4(),
            name="Test Repository"
        )
        db_session.add(repository)
        db_session.commit()

        # Create documents
        doc1 = Document(
            id=uuid.uuid4(),
            title="Document 1",
            source_file="doc1.txt",
            content="Content 1"
        )
        doc2 = Document(
            id=uuid.uuid4(),
            title="Document 2",
            source_file="doc2.txt",
            content="Content 2"
        )
        db_session.add(doc1)
        db_session.add(doc2)
        db_session.commit()

        # Create links
        link1 = RepositoryDocumentLink(
            id=uuid.uuid4(),
            repository_id=repository.id,
            document_id=doc1.id
        )
        link2 = RepositoryDocumentLink(
            id=uuid.uuid4(),
            repository_id=repository.id,
            document_id=doc2.id
        )
        db_session.add(link1)
        db_session.add(link2)
        db_session.commit()

        response = client.get(f"/repositories/{repository.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(repository.id)
        assert data["name"] == "Test Repository"
        assert len(data["document_ids"]) == 2
        assert len(data["document_names"]) == 2
        assert "Document 1" in data["document_names"]
        assert "Document 2" in data["document_names"]


class TestRepositoriesEdgeCases:
    """Test repository edge cases and error handling"""

    @pytest.mark.crud
    def test_create_repository_missing_required_fields(self, client):
        """Test creating a repository with missing required fields"""
        repository_data = {
            "description": "A test repository"
            # Missing name field
        }

        response = client.post("/repositories/", json=repository_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.crud
    def test_update_repository_invalid_data(self, client, db_session):
        """Test updating a repository with invalid data"""
        repository = Repository(
            id=uuid.uuid4(),
            name="Test Repository",
            description="Test description"
        )
        db_session.add(repository)
        db_session.commit()

        update_data = {
            "name": ""  # Invalid empty name
        }

        response = client.put(f"/repositories/{repository.id}", json=update_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.crud
    def test_create_repository_document_link_invalid_ids(self, client):
        """Test creating a link with invalid UUIDs"""
        link_data = {
            "repository_id": "invalid-uuid",
            "document_id": "invalid-uuid"
        }

        response = client.post("/repositories/links", json=link_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.crud
    def test_delete_repository_document_link_invalid_ids(self, client):
        """Test deleting a link with invalid UUIDs"""
        response = client.delete("/repositories/links/invalid-uuid/invalid-uuid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.crud
    def test_repository_cascade_delete_behavior(self, client, db_session):
        """Test that deleting a repository doesn't delete linked documents"""
        # Create a repository
        repository = Repository(
            id=uuid.uuid4(),
            name="Test Repository"
        )
        db_session.add(repository)
        db_session.commit()

        # Create a document
        document = Document(
            id=uuid.uuid4(),
            title="Test Document",
            source_file="test.txt",
            content="Test content"
        )
        db_session.add(document)
        db_session.commit()

        # Create a link
        link = RepositoryDocumentLink(
            id=uuid.uuid4(),
            repository_id=repository.id,
            document_id=document.id
        )
        db_session.add(link)
        db_session.commit()

        # Delete the repository
        response = client.delete(f"/repositories/{repository.id}")
        assert response.status_code == status.HTTP_200_OK

        # Verify the document still exists
        response = client.get(f"/documents/{document.id}")
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.crud
    def test_repository_with_many_documents(self, client, db_session):
        """Test repository with many linked documents"""
        # Create a repository
        repository = Repository(
            id=uuid.uuid4(),
            name="Large Repository"
        )
        db_session.add(repository)
        db_session.commit()

        # Create many documents
        documents = []
        for i in range(10):
            doc = Document(
                id=uuid.uuid4(),
                title=f"Document {i}",
                source_file=f"doc{i}.txt",
                content=f"Content {i}"
            )
            documents.append(doc)
            db_session.add(doc)
        db_session.commit()

        # Create links for all documents
        for doc in documents:
            link = RepositoryDocumentLink(
                id=uuid.uuid4(),
                repository_id=repository.id,
                document_id=doc.id
            )
            db_session.add(link)
        db_session.commit()

        response = client.get(f"/repositories/{repository.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["document_ids"]) == 10
        assert len(data["document_names"]) == 10