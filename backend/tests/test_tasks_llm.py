import pytest
import uuid
from fastapi import status
from sqlmodel import Session, select
from unittest.mock import patch, MagicMock

from tasks.models import Task, AnswerOption
from documents.models import Document, Chunk


class TestTasksLLM:
    """Test LLM-dependent operations for tasks endpoints"""

    @pytest.mark.llm
    @pytest.mark.slow
    def test_generate_tasks_from_document_success(
        self, client, db_session, mock_llm_service
    ):
        """Test generating tasks from document successfully"""
        # Create a document
        document = Document(
            id=uuid.uuid4(),
            title="Test Document",
            source_file="test.txt",
            content="Test content",
        )
        db_session.add(document)
        db_session.commit()

        # Create chunks for the document
        chunk1 = Chunk(
            id=uuid.uuid4(),
            chunk_text="This is the first chunk of text for testing.",
            chunk_index=0,
            chunk_length=44,
            document_id=document.id,
        )
        chunk2 = Chunk(
            id=uuid.uuid4(),
            chunk_text="This is the second chunk of text for testing.",
            chunk_index=1,
            chunk_length=45,
            document_id=document.id,
        )
        db_session.add(chunk1)
        db_session.add(chunk2)
        db_session.commit()

        # Mock the generate_questions function to return test tasks
        mock_tasks = [
            Task(
                id=uuid.uuid4(),
                type="multiple_choice",
                question="What is the main topic of the first chunk?",
                chunk_id=chunk1.id,
            ),
            Task(
                id=uuid.uuid4(),
                type="multiple_choice",
                question="What is the main topic of the second chunk?",
                chunk_id=chunk2.id,
            ),
        ]
        mock_llm_service["generate_questions"].return_value = mock_tasks

        response = client.post(f"/tasks/generate/{document.id}?num_tasks=2")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["question"] == "What is the main topic of the first chunk?"
        assert data[1]["question"] == "What is the main topic of the second chunk?"

        # Verify the mock was called correctly
        mock_llm_service["generate_questions"].assert_called_once()

    @pytest.mark.llm
    def test_generate_tasks_from_document_no_chunks(self, client, db_session):
        """Test generating tasks from document with no chunks"""
        # Create a document without chunks
        document = Document(
            id=uuid.uuid4(),
            title="Test Document",
            source_file="test.txt",
            content="Test content",
        )
        db_session.add(document)
        db_session.commit()

        response = client.post(f"/tasks/generate/{document.id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "No chunks found"

    @pytest.mark.llm
    def test_generate_tasks_from_document_invalid_doc_id(self, client):
        """Test generating tasks with invalid document ID"""
        fake_doc_id = uuid.uuid4()  # Use a valid UUID format that doesn't exist
        response = client.post(f"/tasks/generate/{fake_doc_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "No chunks found"

    @pytest.mark.llm
    @pytest.mark.slow
    def test_generate_tasks_with_custom_num_tasks(
        self, client, db_session, mock_llm_service
    ):
        """Test generating tasks with custom number of tasks"""
        # Create a document
        document = Document(
            id=uuid.uuid4(),
            title="Test Document",
            source_file="test.txt",
            content="Test content",
        )
        db_session.add(document)
        db_session.commit()

        # Create chunks for the document
        chunk = Chunk(
            id=uuid.uuid4(),
            chunk_text="This is a test chunk for generating tasks.",
            chunk_index=0,
            chunk_length=42,
            document_id=document.id,
        )
        db_session.add(chunk)
        db_session.commit()

        # Mock the generate_questions function
        mock_tasks = [
            Task(
                id=uuid.uuid4(),
                type="multiple_choice",
                question=f"Test question {i}",
                chunk_id=chunk.id,
            )
            for i in range(5)
        ]
        mock_llm_service["generate_questions"].return_value = mock_tasks

        response = client.post(f"/tasks/generate/{document.id}?num_tasks=5")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 5

        # Verify the mock was called with correct parameters
        mock_llm_service["generate_questions"].assert_called_once()

    @pytest.mark.llm
    @pytest.mark.slow
    def test_evaluate_answer_success(self, client, db_session, mock_llm_service):
        """Test evaluating a student answer successfully"""
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
            question="What is the main topic?",
            chunk_id=chunk.id,
        )
        db_session.add(task)
        db_session.commit()

        # Create answer options
        option1 = AnswerOption(
            id=uuid.uuid4(), answer="Correct answer", is_correct=True, task_id=task.id
        )
        option2 = AnswerOption(
            id=uuid.uuid4(), answer="Wrong answer", is_correct=False, task_id=task.id
        )
        db_session.add(option1)
        db_session.add(option2)
        db_session.commit()

        # Mock the evaluate_student_answer function
        mock_llm_service[
            "evaluate_student_answer"
        ].return_value = "Excellent answer! You are correct."

        response = client.post(
            f"/tasks/evaluate_answer/{task.id}?student_answer=Correct answer"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "feedback" in data
        assert data["feedback"] == "Excellent answer! You are correct."

        # Verify the mock was called with correct parameters
        mock_llm_service["evaluate_student_answer"].assert_called_once()

    @pytest.mark.llm
    def test_evaluate_answer_task_not_found(self, client):
        """Test evaluating answer for non-existent task"""
        fake_task_id = uuid.uuid4()
        response = client.post(
            f"/tasks/evaluate_answer/{fake_task_id}?student_answer=Some answer"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Task not found"

    @pytest.mark.llm
    def test_evaluate_answer_missing_student_answer(self, client, db_session):
        """Test evaluating answer with missing student answer"""
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
            question="What is the main topic?",
            chunk_id=chunk.id,
        )
        db_session.add(task)
        db_session.commit()

        # Create answer options
        option = AnswerOption(
            id=uuid.uuid4(), answer="Correct answer", is_correct=True, task_id=task.id
        )
        db_session.add(option)
        db_session.commit()

        response = client.post(f"/tasks/evaluate_answer/{task.id}")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.llm
    @pytest.mark.slow
    def test_evaluate_answer_with_multiple_options(
        self, client, db_session, mock_llm_service
    ):
        """Test evaluating answer with multiple answer options"""
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
            question="What is the main topic?",
            chunk_id=chunk.id,
        )
        db_session.add(task)
        db_session.commit()

        # Create multiple answer options
        options = [
            AnswerOption(
                id=uuid.uuid4(), answer="Option A", is_correct=False, task_id=task.id
            ),
            AnswerOption(
                id=uuid.uuid4(), answer="Option B", is_correct=True, task_id=task.id
            ),
            AnswerOption(
                id=uuid.uuid4(), answer="Option C", is_correct=False, task_id=task.id
            ),
        ]
        for option in options:
            db_session.add(option)
        db_session.commit()

        # Mock the evaluate_student_answer function
        mock_llm_service[
            "evaluate_student_answer"
        ].return_value = "Good attempt, but not quite right."

        response = client.post(
            f"/tasks/evaluate_answer/{task.id}?student_answer=Option A"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "feedback" in data
        assert data["feedback"] == "Good attempt, but not quite right."

    @pytest.mark.llm
    @pytest.mark.slow
    def test_evaluate_answer_empty_student_answer(
        self, client, db_session, mock_llm_service
    ):
        """Test evaluating answer with empty student answer"""
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
            question="What is the main topic?",
            chunk_id=chunk.id,
        )
        db_session.add(task)
        db_session.commit()

        # Create answer options
        option = AnswerOption(
            id=uuid.uuid4(), answer="Correct answer", is_correct=True, task_id=task.id
        )
        db_session.add(option)
        db_session.commit()

        # Mock the evaluate_student_answer function
        mock_llm_service[
            "evaluate_student_answer"
        ].return_value = "Please provide an answer."

        response = client.post(f"/tasks/evaluate_answer/{task.id}?student_answer=")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "feedback" in data
        assert data["feedback"] == "Please provide an answer."

    @pytest.mark.llm
    @pytest.mark.slow
    def test_evaluate_answer_llm_service_error(
        self, client, db_session, mock_llm_service
    ):
        """Test evaluating answer when LLM service fails"""
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
            question="What is the main topic?",
            chunk_id=chunk.id,
        )
        db_session.add(task)
        db_session.commit()

        # Create answer options
        option = AnswerOption(
            id=uuid.uuid4(), answer="Correct answer", is_correct=True, task_id=task.id
        )
        db_session.add(option)
        db_session.commit()

        # Mock the evaluate_student_answer function to raise an exception
        mock_llm_service["evaluate_student_answer"].side_effect = Exception(
            "LLM service error"
        )

        response = client.post(
            f"/tasks/evaluate_answer/{task.id}?student_answer=Some answer"
        )
        # The endpoint should handle the error gracefully
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
