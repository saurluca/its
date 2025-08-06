from typing import List
from uuid import UUID
import dspy
import time
from tqdm import tqdm
import random

from constants import REQUIRED_ANSWER_OPTIONS
from documents.models import Chunk
from tasks.models import Task, TaskType, AnswerOption


class QuestionMultipleChoice(dspy.Signature):
    """Generate a single multiple choice question, answer options, and correct answer indices from a text chunk."""

    text: str = dspy.InputField(description="The text to generate a question from.")

    question: str = dspy.OutputField(
        description="A single multiple choice question generated from the key points. It should foster a deep understanding of the material. The question should be short and concise."
    )
    answer: list[str] = dspy.OutputField(
        description="A list of 4 answer options for each question. Exactly one answer option is correct. The correct answer should always be in the first position. Do not enumerate the answer options, no numbering or alphabet."
    )


class QuestionOpen(dspy.Signature):
    """Generate a single open question from a text chunk and an ideal answer."""

    text: str = dspy.InputField(description="The text to generate a question from.")

    question: str = dspy.OutputField(
        description="""
        A single question generated from the text, that is answerable in 1 to 3 sentences, based on the provided text.
        The question should be relevant to the text and require a deep understanding of the material to answer.
        The question should be short and concise.
        """
    )
    answer: str = dspy.OutputField(
        description="The ideal, correct answer to the question. The user's answer will be compared to this answer."
    )


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
        description="Short and concise explanation of what the correct answer is and why it is correct. The feedback should be based on the student's answer."
    )


def _get_question_generator(question_type: str):
    """Get the appropriate question generator based on question type."""
    if question_type == "multiple_choice":
        return dspy.ChainOfThought(QuestionMultipleChoice)
    elif question_type == "open":
        return dspy.ChainOfThought(QuestionOpen)
    else:
        raise ValueError(f"Invalid question type: {question_type}")


def _generate_single_question(chunk: Chunk, question_generator, question_type: str):
    """Generate a single question from a chunk."""
    try:
        qg_response = question_generator(text=chunk.chunk_text)

        # Validate multiple choice questions have the correct number of answer options
        if (
            question_type == "multiple_choice"
            and len(qg_response.answer) != REQUIRED_ANSWER_OPTIONS
        ):
            return None

        return qg_response
    except Exception as e:
        print(f"Error generating question for chunk {chunk.chunk_id}: {e}")
        return None


def _create_task_from_response(
    qg_response, question_type: str, document_id: UUID, chunk_id: UUID
) -> Task:
    """Create a Task object from a question generation response."""
    task = Task(
        type=TaskType.MULTIPLE_CHOICE
        if question_type == "multiple_choice"
        else TaskType.FREE_TEXT,
        question=qg_response.question,
        chunk_id=chunk_id,
    )

    # Create answer options for multiple choice questions
    if question_type == "multiple_choice":
        for i, answer in enumerate(qg_response.answer):
            answer_option = AnswerOption(
                answer=answer,
                is_correct=(i == 0),  # First answer is correct
                task=task,
            )
            task.answer_options.append(answer_option)
    # For free text questions, create a single answer option with the ideal answer
    elif question_type == "open":
        answer_option = AnswerOption(
            answer=qg_response.answer,
            is_correct=True,  # The ideal answer is always correct
            task=task,
        )
        task.answer_options.append(answer_option)

    return task


def generate_questions(
    document_id: str,
    chunks: List[dict],
    num_questions: int = 3,
    question_type: str = "multiple_choice",
) -> List[Task]:
    """
    Generate questions from document chunks

    Args:
        document_id: Document ID
        chunks: List of document chunks
        num_questions: Number of questions to generate
        question_type: Type of question to generate

    Returns:
        List of Task objects
    """
    question_generator = _get_question_generator(question_type)

    print(
        f"Generating {num_questions} questions for document {document_id} with {len(chunks)} chunks"
    )

    tasks = []
    start_time = time.time()

    # Randomly select num_questions chunks with replacement
    selected_chunks = [random.choice(chunks) for _ in range(num_questions)]

    for chunk in tqdm(selected_chunks):
        qg_response = _generate_single_question(
            chunk, question_generator, question_type
        )

        if qg_response is not None:
            task = _create_task_from_response(
                qg_response, question_type, document_id, chunk.id
            )
            tasks.append(task)

    end_time = time.time()
    print(f"Generated {len(tasks)} tasks in {end_time - start_time} seconds")

    if not tasks:
        raise Exception("No questions could be generated from the provided chunks")

    return tasks


def evaluate_student_answer(
    question: str, answer_options: List[str], student_answer: str, correct_answer: str
) -> str:
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
