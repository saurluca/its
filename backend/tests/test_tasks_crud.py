import pytest
import uuid
from fastapi import status
from sqlmodel import Session, select

from tasks.models import Task, TaskCreate, TaskUpdate, AnswerOption
from documents.models import Document, Chunk


class TestTasksCRUD:
    """Test CRUD operations for tasks endpoints"""

    @pytest.mark.crud
    def test_get_tasks_empty(self, client):
        """Test getting tasks when none exist"""
        response = client.get("/tasks/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @pytest.mark.crud
    def test_get_tasks_with_data(self, client, db_session, sample_chunk_data):
        """Test getting tasks when tasks exist"""
        # Create a document and chunk first
        document = Document(
            id=uuid.uuid4(),
            title="Test Document",
            source_file="test.txt",
            content="Test content",
        )
        db_session.add(document)
        db_session.commit()

        chunk = Chunk(
            id=uuid.uuid4(),
            chunk_text="Test chunk text",
            chunk_index=0,
            chunk_length=15,
            document_id=document.id,
        )
        db_session.add(chunk)
        db_session.commit()

        # Create a task
        task = Task(
            id=uuid.uuid4(),
            type="multiple_choice",
            question="What is this?",
            chunk_id=chunk.id,
        )
        db_session.add(task)
        db_session.commit()

        response = client.get("/tasks/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["question"] == "What is this?"

    @pytest.mark.crud
    def test_get_task_by_id_success(self, client, db_session, sample_chunk_data):
        """Test getting a specific task by ID"""
        # Create a document and chunk first
        document = Document(
            id=uuid.uuid4(),
            title="Test Document",
            source_file="test.txt",
            content="Test content",
        )
        db_session.add(document)
        db_session.commit()

        chunk = Chunk(
            id=uuid.uuid4(),
            chunk_text="Test chunk text",
            chunk_index=0,
            chunk_length=15,
            document_id=document.id,
        )
        db_session.add(chunk)
        db_session.commit()

        # Create a task
        task = Task(
            id=uuid.uuid4(),
            type="multiple_choice",
            question="What is this?",
            chunk_id=chunk.id,
        )
        db_session.add(task)
        db_session.commit()

        response = client.get(f"/tasks/{task.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(task.id)
        assert data["question"] == "What is this?"

    @pytest.mark.crud
    def test_get_task_by_id_not_found(self, client):
        """Test getting a task that doesn't exist"""
        fake_id = uuid.uuid4()
        response = client.get(f"/tasks/{fake_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Task not found"

    @pytest.mark.crud
    def test_create_task_success(self, client, db_session):
        """Test creating a task successfully"""
        # Create a document and chunk first
        document = Document(
            id=uuid.uuid4(),
            title="Test Document",
            source_file="test.txt",
            content="Test content",
        )
        db_session.add(document)
        db_session.commit()

        chunk = Chunk(
            id=uuid.uuid4(),
            chunk_text="Test chunk text",
            chunk_index=0,
            chunk_length=15,
            document_id=document.id,
        )
        db_session.add(chunk)
        db_session.commit()

        task_data = {
            "type": "multiple_choice",
            "question": "What is the main topic?",
            "chunk_id": str(chunk.id),
            "answer_options": [
                {"answer": "Option A", "is_correct": True},
                {"answer": "Option B", "is_correct": False},
            ],
        }

        response = client.post("/tasks/", json=task_data)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["question"] == "What is the main topic?"
        assert data["type"] == "multiple_choice"
        assert len(data["answer_options"]) == 2

    @pytest.mark.crud
    def test_create_task_chunk_not_found(self, client):
        """Test creating a task with non-existent chunk"""
        task_data = {
            "type": "multiple_choice",
            "question": "What is the main topic?",
            "chunk_id": str(uuid.uuid4()),
            "answer_options": [{"answer": "Option A", "is_correct": True}],
        }

        response = client.post("/tasks/", json=task_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Chunk not found"

    @pytest.mark.crud
    def test_update_task_success(self, client, db_session):
        """Test updating a task successfully"""
        # Create a document and chunk first
        document = Document(
            id=uuid.uuid4(),
            title="Test Document",
            source_file="test.txt",
            content="Test content",
        )
        db_session.add(document)
        db_session.commit()

        chunk = Chunk(
            id=uuid.uuid4(),
            chunk_text="Test chunk text",
            chunk_index=0,
            chunk_length=15,
            document_id=document.id,
        )
        db_session.add(chunk)
        db_session.commit()

        # Create a task
        task = Task(
            id=uuid.uuid4(),
            type="multiple_choice",
            question="Original question",
            chunk_id=chunk.id,
        )
        db_session.add(task)
        db_session.commit()

        update_data = {
            "question": "Updated question",
            "answer_options": [
                {"answer": "New Option A", "is_correct": True},
                {"answer": "New Option B", "is_correct": False},
            ],
        }

        response = client.put(f"/tasks/{task.id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["question"] == "Updated question"
        assert len(data["answer_options"]) == 2

    @pytest.mark.crud
    def test_update_task_not_found(self, client):
        """Test updating a task that doesn't exist"""
        fake_id = uuid.uuid4()
        update_data = {"question": "Updated question"}

        response = client.put(f"/tasks/{fake_id}", json=update_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Task not found"

    @pytest.mark.crud
    def test_delete_task_success(self, client, db_session):
        """Test deleting a task successfully"""
        # Create a document and chunk first
        document = Document(
            id=uuid.uuid4(),
            title="Test Document",
            source_file="test.txt",
            content="Test content",
        )
        db_session.add(document)
        db_session.commit()

        chunk = Chunk(
            id=uuid.uuid4(),
            chunk_text="Test chunk text",
            chunk_index=0,
            chunk_length=15,
            document_id=document.id,
        )
        db_session.add(chunk)
        db_session.commit()

        # Create a task
        task = Task(
            id=uuid.uuid4(),
            type="multiple_choice",
            question="Test question",
            chunk_id=chunk.id,
        )
        db_session.add(task)
        db_session.commit()

        response = client.delete(f"/tasks/{task.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["ok"] is True

        # Verify task is deleted
        response = client.get(f"/tasks/{task.id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.crud
    def test_delete_task_not_found(self, client):
        """Test deleting a task that doesn't exist"""
        fake_id = uuid.uuid4()
        response = client.delete(f"/tasks/{fake_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Task not found"


class TestAnswerOptionsCRUD:
    """Test CRUD operations for answer options endpoints"""

    @pytest.mark.crud
    def test_create_answer_option_success(self, client, db_session):
        """Test creating an answer option successfully"""
        # Create a document and chunk first
        document = Document(
            id=uuid.uuid4(),
            title="Test Document",
            source_file="test.txt",
            content="Test content",
        )
        db_session.add(document)
        db_session.commit()

        chunk = Chunk(
            id=uuid.uuid4(),
            chunk_text="Test chunk text",
            chunk_index=0,
            chunk_length=15,
            document_id=document.id,
        )
        db_session.add(chunk)
        db_session.commit()

        # Create a task
        task = Task(
            id=uuid.uuid4(),
            type="multiple_choice",
            question="Test question",
            chunk_id=chunk.id,
        )
        db_session.add(task)
        db_session.commit()

        answer_option_data = {"answer": "New answer option", "is_correct": True}

        response = client.post(
            f"/tasks/{task.id}/answer-options", json=answer_option_data
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["answer"] == "New answer option"
        assert data["is_correct"] is True
        assert data["task_id"] == str(task.id)

    @pytest.mark.crud
    def test_create_answer_option_task_not_found(self, client):
        """Test creating an answer option for non-existent task"""
        fake_task_id = uuid.uuid4()
        answer_option_data = {"answer": "New answer option", "is_correct": True}

        response = client.post(
            f"/tasks/{fake_task_id}/answer-options", json=answer_option_data
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Task not found"

    @pytest.mark.crud
    def test_get_answer_options_success(self, client, db_session):
        """Test getting answer options for a task"""
        # Create a document and chunk first
        document = Document(
            id=uuid.uuid4(),
            title="Test Document",
            source_file="test.txt",
            content="Test content",
        )
        db_session.add(document)
        db_session.commit()

        chunk = Chunk(
            id=uuid.uuid4(),
            chunk_text="Test chunk text",
            chunk_index=0,
            chunk_length=15,
            document_id=document.id,
        )
        db_session.add(chunk)
        db_session.commit()

        # Create a task
        task = Task(
            id=uuid.uuid4(),
            type="multiple_choice",
            question="Test question",
            chunk_id=chunk.id,
        )
        db_session.add(task)
        db_session.commit()

        # Create answer options
        option1 = AnswerOption(
            id=uuid.uuid4(), answer="Option A", is_correct=True, task_id=task.id
        )
        option2 = AnswerOption(
            id=uuid.uuid4(), answer="Option B", is_correct=False, task_id=task.id
        )
        db_session.add(option1)
        db_session.add(option2)
        db_session.commit()

        response = client.get(f"/tasks/{task.id}/answer-options")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert any(opt["answer"] == "Option A" for opt in data)
        assert any(opt["answer"] == "Option B" for opt in data)

    @pytest.mark.crud
    def test_get_answer_options_task_not_found(self, client):
        """Test getting answer options for non-existent task"""
        fake_task_id = uuid.uuid4()
        response = client.get(f"/tasks/{fake_task_id}/answer-options")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Task not found"

    @pytest.mark.crud
    def test_update_answer_option_success(self, client, db_session):
        """Test updating an answer option successfully"""
        # Create a document and chunk first
        document = Document(
            id=uuid.uuid4(),
            title="Test Document",
            source_file="test.txt",
            content="Test content",
        )
        db_session.add(document)
        db_session.commit()

        chunk = Chunk(
            id=uuid.uuid4(),
            chunk_text="Test chunk text",
            chunk_index=0,
            chunk_length=15,
            document_id=document.id,
        )
        db_session.add(chunk)
        db_session.commit()

        # Create a task
        task = Task(
            id=uuid.uuid4(),
            type="multiple_choice",
            question="Test question",
            chunk_id=chunk.id,
        )
        db_session.add(task)
        db_session.commit()

        # Create an answer option
        option = AnswerOption(
            id=uuid.uuid4(), answer="Original answer", is_correct=False, task_id=task.id
        )
        db_session.add(option)
        db_session.commit()

        update_data = {"answer": "Updated answer", "is_correct": True}

        response = client.put(
            f"/tasks/{task.id}/answer-options/{option.id}", json=update_data
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["answer"] == "Updated answer"
        assert data["is_correct"] is True

    @pytest.mark.crud
    def test_update_answer_option_not_found(self, client):
        """Test updating an answer option that doesn't exist"""
        fake_task_id = uuid.uuid4()
        fake_option_id = uuid.uuid4()
        update_data = {"answer": "Updated answer", "is_correct": True}

        response = client.put(
            f"/tasks/{fake_task_id}/answer-options/{fake_option_id}", json=update_data
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Answer option not found"

    @pytest.mark.crud
    def test_delete_answer_option_success(self, client, db_session):
        """Test deleting an answer option successfully"""
        # Create a document and chunk first
        document = Document(
            id=uuid.uuid4(),
            title="Test Document",
            source_file="test.txt",
            content="Test content",
        )
        db_session.add(document)
        db_session.commit()

        chunk = Chunk(
            id=uuid.uuid4(),
            chunk_text="Test chunk text",
            chunk_index=0,
            chunk_length=15,
            document_id=document.id,
        )
        db_session.add(chunk)
        db_session.commit()

        # Create a task
        task = Task(
            id=uuid.uuid4(),
            type="multiple_choice",
            question="Test question",
            chunk_id=chunk.id,
        )
        db_session.add(task)
        db_session.commit()

        # Create an answer option
        option = AnswerOption(
            id=uuid.uuid4(), answer="Test answer", is_correct=True, task_id=task.id
        )
        db_session.add(option)
        db_session.commit()

        response = client.delete(f"/tasks/{task.id}/answer-options/{option.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["ok"] is True

    @pytest.mark.crud
    def test_delete_answer_option_not_found(self, client):
        """Test deleting an answer option that doesn't exist"""
        fake_task_id = uuid.uuid4()
        fake_option_id = uuid.uuid4()

        response = client.delete(
            f"/tasks/{fake_task_id}/answer-options/{fake_option_id}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Answer option not found"
