from typing import List, Tuple, Dict, Any
from uuid import UUID
from sqlmodel import select
from datetime import datetime
import dspy
import time
from tqdm import tqdm
import random
import json
from sqlalchemy import desc

from tasks.models import Task, TaskCreate, TaskUpdate
from exceptions import (
    DocumentNotFoundError,
)
from constants import DEFAULT_NUM_QUESTIONS, REQUIRED_ANSWER_OPTIONS
from utils import get_session


def create_task(task_data: TaskCreate) -> Task:
    """
    Create a new task

    Args:
        task_data: Task creation data

    Returns:
        Created task
    """
    with get_session() as session:
        task = Task.model_validate(task_data.model_dump())
        session.add(task)
        session.commit()
        session.refresh(task)
        return task


def get_task_by_id(task_id: UUID) -> Task:
    """
    Get task by ID

    Args:
        task_id: Task UUID

    Returns:
        Task object

    Raises:
        DocumentNotFoundError: If task not found
    """
    with get_session() as session:
        statement = select(Task).where(Task.id == task_id)
        task = session.exec(statement).first()

        if not task:
            raise DocumentNotFoundError(f"Task not found with id: {task_id}")

        return task


def get_all_tasks(limit: int = 100) -> List[Task]:
    """
    Get all tasks with limit

    Args:
        limit: Maximum number of tasks to return

    Returns:
        List of tasks
    """
    with get_session() as session:
        statement = select(Task).order_by(desc(Task.created_at)).limit(limit)
        tasks = session.exec(statement).all()
        return list(tasks)


def get_tasks_by_course_id(course_id: UUID, limit: int = 100) -> List[Task]:
    """
    Get tasks by course ID

    Args:
        course_id: Course UUID
        limit: Maximum number of tasks to return

    Returns:
        List of tasks for the course
    """
    with get_session() as session:
        statement = (
            select(Task)
            .where(Task.course_id == course_id)
            .order_by(desc(Task.created_at))
            .limit(limit)
        )
        tasks = session.exec(statement).all()
        return list(tasks)


def update_task(task_id: UUID, task_update: TaskUpdate) -> Task:
    """
    Update task by ID

    Args:
        task_id: Task UUID
        task_update: Task update data

    Returns:
        Updated task

    Raises:
        DocumentNotFoundError: If task not found
    """
    with get_session() as session:
        statement = select(Task).where(Task.id == task_id)
        task = session.exec(statement).first()

        if not task:
            raise DocumentNotFoundError(f"Task not found with id: {task_id}")

        # Update fields that are not None
        update_data = task_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)

        task.updated_at = datetime.utcnow()
        session.add(task)
        session.commit()
        session.refresh(task)

        return task


def delete_task(task_id: UUID) -> Task:
    """
    Delete task by ID

    Args:
        task_id: Task UUID

    Returns:
        Deleted task

    Raises:
        DocumentNotFoundError: If task not found
    """
    with get_session() as session:
        statement = select(Task).where(Task.id == task_id)
        task = session.exec(statement).first()

        if not task:
            raise DocumentNotFoundError(f"Task not found with id: {task_id}")

        session.delete(task)
        session.commit()

        return task


# Question generation signatures
class QuestionSingle(dspy.Signature):
    """Generate a single multiple choice question, answer options, and correct answer indices from key points."""

    text: str = dspy.InputField(description="The text to generate a question from.")

    question: str = dspy.OutputField(
        description="A single multiple choice question generated from the key points. It should foster a deep understanding of the material. The question should be short and concise."
    )
    answer_options: list[str] = dspy.OutputField(
        description="A list of 4 answer options for each question. Exactly one answer option is correct. The correct answer should always be in the first position."
    )


class QuestionBatch(dspy.Signature):
    """Generate multiple multiple-choice questions and answer options from a list of key points."""

    texts: list[str] = dspy.InputField(
        description="A list of texts to generate questions from."
    )

    questions: list[str] = dspy.OutputField(
        description="A list of multiple choice questions, one per input text. Each question should be short and concise."
    )
    answer_options: list[list[str]] = dspy.OutputField(
        description="A list of answer options for each question. Each should be a list of 4 options, with the correct answer always in the first position."
    )


# Teacher evaluation signature
class Teacher(dspy.Signature):
    """Evaluate the student's answer, and provide feedback."""

    # input fields
    question: str = dspy.InputField(
        description="The question to be answered and the 4 answer options."
    )
    answer_options: list[str] = dspy.InputField(
        description="The 4 answer options for the question."
    )
    correct_answer: str = dspy.InputField(
        description="The correct answer to the question."
    )
    student_answer: str = dspy.InputField(
        description="The student's answer to the question."
    )

    # output fields
    feedback: str = dspy.OutputField(
        description="Short and concise explanation for the student based on their answer."
    )


# Question-related service functions
def save_questions_to_db(
    doc_id: str, questions: List[str], answer_options: List[List[str]]
):
    """
    Save a list of questions and their answer options to the database, linked to the given document ID.
    """
    if len(questions) != len(answer_options):
        raise ValueError("questions and answer_options must have the same length")

    document_uuid = UUID(doc_id)

    with get_session() as session:
        for question_text, options in zip(questions, answer_options):
            task_create = TaskCreate(
                question=question_text,
                type="multiple_choice",
                options_json=json.dumps(options),
                correct_answer=options[0],
                document_id=document_uuid,
            )
            task = Task.model_validate(task_create.model_dump())
            session.add(task)
        session.commit()


def get_questions_by_document_id(doc_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all tasks (questions), their IDs, and answer options for a given document ID.
    """
    document_uuid = UUID(doc_id)
    with get_session() as session:
        statement = select(Task).where(Task.document_id == document_uuid)
        tasks = session.exec(statement).all()
        return [
            {
                "id": str(task.id),
                "question": task.question,
                "answer_options": task.get_options_list(),
            }
            for task in tasks
        ]


def get_question_by_id(question_id: UUID) -> Tuple[str, List[str]]:
    """
    Get question and answer options by task ID
    """
    with get_session() as session:
        statement = select(Task).where(Task.id == question_id)
        task = session.exec(statement).first()
        if not task:
            raise Exception(f"No task found with id: {question_id}")
        return task.question, task.get_options_list()


def generate_questions(
    document_id: str, chunks: List[dict], num_questions: int = 0
) -> Tuple[List[str], List[List[str]]]:
    """
    Generate questions from document chunks

    Args:
        document_id: Document ID
        chunks: List of document chunks
        num_questions: Number of questions to generate

    Returns:
        Tuple of (questions, answer_options)
    """
    if num_questions == 0:
        num_questions = len(chunks)

    print(f"Generating questions for document {document_id} with {len(chunks)} chunks")
    questions = []
    answer_options = []
    question_generator = dspy.ChainOfThought(QuestionSingle)
    start_time = time.time()

    if num_questions != len(chunks):
        # randomly select num_questions chunks
        chunks = random.sample(chunks, num_questions)

    for chunk in tqdm(chunks):
        try:
            qg_response = question_generator(text=chunk["chunk_text"])

            if len(qg_response.answer_options) != REQUIRED_ANSWER_OPTIONS:
                print(
                    f"Skipping chunk {chunk['chunk_index']} because it has {len(qg_response.answer_options)} answer options, but should have exactly {REQUIRED_ANSWER_OPTIONS} choices."
                )
                continue

            questions.append(qg_response.question)
            answer_options.append(qg_response.answer_options)
        except Exception as e:
            print(f"Error generating question for chunk {chunk['chunk_index']}: {e}")
            continue

    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")
    print(
        f"Generated {len(questions)} questions and {len(answer_options)} answer options in {end_time - start_time} seconds"
    )

    if not questions:
        raise Exception("No questions could be generated from the provided chunks")

    return questions, answer_options


def generate_questions_batch(
    document_id: str, chunks: List[dict], num_questions: int = DEFAULT_NUM_QUESTIONS
) -> Tuple[List[str], List[List[str]]]:
    """
    Generate questions in batch mode for better performance

    Args:
        document_id: Document ID
        chunks: List of document chunks
        num_questions: Number of questions to generate

    Returns:
        Tuple of (questions, answer_options)
    """
    print(
        f"Batch-generating questions for document {document_id} with {len(chunks)} chunks"
    )
    if num_questions != len(chunks):
        chunks = random.sample(chunks, num_questions)

    chunk_texts = [chunk["chunk_text"] for chunk in chunks]
    question_generator = dspy.ChainOfThought(QuestionBatch)
    start_time = time.time()

    try:
        qg_response = question_generator(texts=chunk_texts)

        # Validate output
        questions = []
        answer_options = []
        for i, (q, opts) in enumerate(
            zip(qg_response.questions, qg_response.answer_options)
        ):
            if not isinstance(opts, list) or len(opts) != REQUIRED_ANSWER_OPTIONS:
                print(
                    f"Skipping question {i} because it has {len(opts) if isinstance(opts, list) else 'invalid'} answer options, should have exactly {REQUIRED_ANSWER_OPTIONS}."
                )
                continue
            questions.append(q)
            answer_options.append(opts)

        end_time = time.time()
        print(f"Time taken (batch): {end_time - start_time} seconds")
        print(
            f"Generated {len(questions)} questions and {len(answer_options)} answer options in {end_time - start_time} seconds (batch)"
        )

        if not questions:
            raise Exception("No valid questions could be generated in batch mode")

        return questions, answer_options
    except Exception as e:
        raise Exception(f"Batch question generation failed: {e}")


def evaluate_student_answer(
    question: str, answer_options: List[str], student_answer: str, correct_answer: str
) -> str:
    """
    Evaluate a student's answer and provide feedback

    Args:
        question: The question text
        answer_options: List of answer options
        student_answer: Student's selected answer

    Returns:
        Feedback text
    """
    teacher = dspy.ChainOfThought(Teacher)

    try:
        response = teacher(
            question=question,
            answer_options=answer_options,
            correct_answer=correct_answer,
            student_answer=student_answer,
        )
        return response.feedback
    except Exception as e:
        return f"Error evaluating answer: {e}"
