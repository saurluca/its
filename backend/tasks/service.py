from typing import List
from uuid import UUID
import dspy
import time
from tqdm import tqdm
import random
from fastapi import HTTPException
from datetime import datetime, timezone

from constants import (
    REQUIRED_ANSWER_OPTIONS,
    TASKS_PER_SESSION,
    SM2_PARTIAL_CREDIT,
    SM2_NEW_TASK_BOOST,
    SM2_RECENCY_WEIGHT,
)
from documents.models import Chunk
from tasks.models import (
    Task,
    TaskType,
    AnswerOption,
    TaskReadTeacher,
    TeacherResponseMultipleChoice,
    TeacherResponseFreeText,
    TaskUserLink,
)


class TaskMultipleChoice(dspy.Signature):
    """Generate a single multiple choice question, with 4 answer options, and exactly one correct answer which is in the first position.
    Generate the question based on the provided text.
    The question should be short and concise.
    The question should be relevant to the text and require understanding of the material.
    Do not enumerate the answer options, no numbering or alphabet.
    The student does not see the text chunk.
    There should be exactly one correct answer.
    The text is an excerpt from a lecture.
    """

    text: str = dspy.InputField(description="The text to generate a question from.")

    question: str = dspy.OutputField(
        description="A single multiple choice question generated from the key points. It should foster a deep understanding of the material. The question should be short and concise."
    )

    answer: list[str] = dspy.OutputField(
        description="A list of 4 answer options for each question. Exactly one answer option is correct. The correct answer should always be in the first position. Do not enumerate the answer options, no numbering or alphabet."
    )


class TaskFreeText(dspy.Signature):
    """Generate a single free text question from a text chunk and an ideal answer.
    The question should be short and concise.
    The question should be answerable in 1 to 3 sentences.
    The question should be relevant to the text and require understanding of the material.
    Keep close to the text, do not make up information.
    The student does not see the text chunk.
    The text is an excerpt from a lecture.
    Also provide a correct answer to the question.
    Keep this answer short and concise, containing the key points relevant to answer the question.
    The user's answer will be compared to this answer.
    """

    text: str = dspy.InputField(description="The text to generate a question from.")

    question: str = dspy.OutputField(
        description="A single question generated from the text"
    )
    answer: str = dspy.OutputField(
        description="The ideal, correct answer to the question. Concise and contains the key points relevant to answer the question."
    )


class TeacherFreeText2Way(dspy.Signature):
    """You are grading a student's response to a short answer-question about the text {chunk} below.

    Students have been asked this question:  {question}

    A correct answer to this question is: {correct_answer}

    Your task is to decide if the student’s answer is correct or wrong.

    A student answer is wrong if it misses a key part of the correct answer.
    Ignore Grammar and Spelling mistakes, only evaluate the content.

    If the student response is correct, you will respond with score = 0.
    If the student response is wrong, you will respond with score = 1.
    """

    chunk: str = dspy.InputField(
        description="The chunk of text related to the question."
    )

    question: str = dspy.InputField(description="The question asked to the student.")

    correct_answer: str = dspy.InputField(
        description="The correct answer to the question."
    )

    student_answer: str = dspy.InputField(
        description="The student's answer to the question."
    )

    score: int = dspy.OutputField(
        description="0 if the content of the student's answer is correct, 1 if it is wrong."
    )


class TeacherFreeText4Way(dspy.Signature):
    """You are a teacher for undergraduate students.
    Your job is to evaluate the student's answers to a short answer-question about the text {chunk} below and provide short and concise feedback.

    Students have been asked this question:  {question}

    A correct answer to this question is: {correct_answer}

    Your task is to decide if the student’s answer is correct, partially correct but incomplete, irrelevant or contradictory.
    Answer based on the chunk and the provided correct answer only.

    Correct: The student's answer is correct and includes the key points from the correct answer.
    If the student response is correct, you will respond with score = 0

    Partially correct but incomplete: The student's answer correct, but does not include the key points from the correct answer.
    If the student response is partially correct but incomplete, you will respond with score = 1

    Contradictory: The student's answer contradicts the chunk and the correct answer. It is not related to the question.
    If the student response is contradictory, you will respond with score = 2

    Irrelevant: The student's answer is irrelevant to the question.
    If the student response is irrelevant, you will respond with score = 3

    The feedback should be short and concise, 1 to 2 sentences.
    The feedback should explain the reasoning behind the score, e.g. what is missing, what is wrong, what is right in the student's answer.
    The feedback should be based on the student's answer and the chunk.
    """

    chunk: str = dspy.InputField(
        description="The chunk of text related to the question."
    )

    question: str = dspy.InputField(description="The question asked to the student.")

    correct_answer: str = dspy.InputField(
        description="The correct answer to the question."
    )

    student_answer: str = dspy.InputField(
        description="The student's answer to the question."
    )

    score: int = dspy.OutputField(
        description="0 if the content of the student's answer is correct, 1 if it is partially correct but incomplete, 2 if it is contradictory, 3 if it is irrelevant."
    )

    feedback: str = dspy.OutputField(
        description="Short and concise feedback for the student based on their answer."
    )


class TeacherMultipleChoice(dspy.Signature):
    """You are a teacher for undergraduate students. Your job is to evaluate the student's answers to a Multiple Choice question
    based on the chunk of text, which is an excerpt from the lecture, and the question.

    Evaluate the student's answer, and provide feedback.
    """

    chunk: str = dspy.InputField(
        description="The chunk of text related to the question."
    )
    question: str = dspy.InputField(description="The question asked to the student.")

    correct_answer: str = dspy.InputField(
        description="The correct answer to the question."
    )

    student_answer: str = dspy.InputField(
        description="The student's answer to the question. One of multiple predefined answer options."
    )

    feedback: str = dspy.OutputField(
        description="Short and concise feedback for the student based on their answer, if it is correct or incorrect, based on the chunk and the answer options."
        "If it is incorrect, provide a short explanation of what the correct answer is and why it is correct. The feedback should be based on the student's answer and the chunk."
    )


def _get_task_generator(task_type: str):
    """Get the appropriate task generator based on task type."""
    if task_type == "multiple_choice":
        return dspy.ChainOfThought(TaskMultipleChoice)
    elif task_type == "free_text":
        return dspy.ChainOfThought(TaskFreeText)
    else:
        raise ValueError(f"Invalid task type: {task_type}")


def _generate_single_task(chunk: Chunk, task_generator, task_type: str, lm: dspy.LM):
    """Generate a single task from a chunk."""
    try:
        qg_response = task_generator(text=chunk.chunk_text, lm=lm)

        # Validate multiple choice tasks have the correct number of answer options
        if (
            task_type == "multiple_choice"
            and len(qg_response.answer) != REQUIRED_ANSWER_OPTIONS
        ):
            return None

        return qg_response
    except Exception as e:
        print(f"Error generating task for chunk {chunk.id}: {e}")
        return None


def _create_task_from_response(qg_response, task_type: str, chunk_id: UUID) -> Task:
    """Create a Task object from a task generation response."""
    task = Task(
        type=TaskType.MULTIPLE_CHOICE
        if task_type == "multiple_choice"
        else TaskType.FREE_TEXT,
        question=qg_response.question,
        chunk_id=chunk_id,
    )

    # Create answer options for multiple choice questions
    if task_type == "multiple_choice":
        for i, answer in enumerate(qg_response.answer):
            answer_option = AnswerOption(
                answer=answer,
                is_correct=(i == 0),  # First answer is correct
                task=task,
            )
            task.answer_options.append(answer_option)
    # For free text questions, create a single answer option with the ideal answer
    elif task_type == "free_text":
        answer_option = AnswerOption(
            answer=qg_response.answer,
            is_correct=True,  # The ideal answer is always correct
            task=task,
        )
        task.answer_options.append(answer_option)

    return task


def generate_tasks(
    document_id: UUID,
    chunks: List[Chunk],
    lm: dspy.LM,
    num_tasks: int = 3,
    task_type: str = "multiple_choice",
    forbidden_questions: set[str] | None = None,
) -> List[Task]:
    """
    Generate tasks from document chunks

    Args:
        document_id: Document ID
        chunks: List of document chunks
        num_tasks: Number of tasks to generate
        task_type: Type of task to generate

    Returns:
        List of Task objects
    """
    task_generator = _get_task_generator(task_type)

    print(
        f"Generating {num_tasks} tasks for document {document_id} with {len(chunks)} chunks"
    )

    tasks: List[Task] = []
    start_time = time.time()

    # Track questions to avoid duplicates against provided forbidden set and within this batch
    seen_questions: set[str] = (
        set(forbidden_questions) if forbidden_questions else set()
    )

    max_attempts = 4
    attempts = 0
    while len(tasks) < num_tasks and attempts < max_attempts:
        remaining = num_tasks - len(tasks)

        # Select up to len(chunks) chunks without replacement, then the rest with replacement
        if remaining <= len(chunks):
            selected_chunks = random.sample(chunks, remaining)
        else:
            selected_chunks = list(chunks)
            selected_chunks += [
                random.choice(chunks) for _ in range(remaining - len(chunks))
            ]

        for chunk in tqdm(selected_chunks):
            if len(tasks) >= num_tasks:
                break

            qg_response = _generate_single_task(chunk, task_generator, task_type, lm)

            if qg_response is None:
                continue

            question_text = qg_response.question
            if question_text in seen_questions:
                # Duplicate question, skip
                continue

            task = _create_task_from_response(qg_response, task_type, chunk.id)
            tasks.append(task)
            seen_questions.add(question_text)

        attempts += 1

    end_time = time.time()
    print(f"Generated {len(tasks)} unique tasks in {end_time - start_time} seconds")

    if not tasks:
        raise Exception("No tasks could be generated from the provided chunks")

    return tasks


def evaluate_student_answer(
    task_teacher: TaskReadTeacher,
    student_answer: str,
    task_type: TaskType,
    lm: dspy.LM,
) -> TeacherResponseMultipleChoice | TeacherResponseFreeText:
    if task_type == TaskType.MULTIPLE_CHOICE:
        print("Evaluating multiple choice task")
        teacher = dspy.ChainOfThought(TeacherMultipleChoice)
    elif task_type == TaskType.FREE_TEXT:
        print("Evaluating free text task")
        teacher = dspy.ChainOfThought(TeacherFreeText4Way)

    try:
        # print("task_teacher", task_teacher)
        # print("student_answer", student_answer)
        response = teacher(
            chunk=task_teacher.chunk,
            question=task_teacher.question,
            correct_answer=task_teacher.answer_options[0].answer,
            student_answer=student_answer,
            lm=lm,
        )

        # inspect history and print the last 3 messages
        # print(teacher.history[-1:])

        print("response", response)

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating answer: {e}")


def _compute_task_priority(
    task: Task,
    progress: TaskUserLink | None,
    now: datetime,
) -> float:
    """
    Compute a priority score for a task using simplified SM-2 ideas:
    - Unseen tasks get a large boost so they appear first.
    - Otherwise, higher when last attempt is older and correctness ratio is low.
    """
    if progress is None:
        return SM2_NEW_TASK_BOOST

    total = progress.times_correct + progress.times_incorrect + progress.times_partial
    if total == 0:
        return SM2_NEW_TASK_BOOST

    # Quality as proportion of success with partial weighted
    weighted_correct = (
        progress.times_correct + SM2_PARTIAL_CREDIT * progress.times_partial
    )
    quality = weighted_correct / total  # 0..1

    # Recency in days
    last = progress.updated_at or progress.created_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    days_since = (now - last).total_seconds() / 86400.0

    # Lower quality and older review => higher priority
    priority = (1.0 - quality) * 10.0 + days_since * SM2_RECENCY_WEIGHT
    return priority


def get_study_tasks_for_unit(
    unit_id: UUID,
    user_id: UUID,
    session,
) -> list[Task]:
    """
    Return up to TASKS_PER_SESSION tasks for a unit, ordered by priority.
    New tasks first; then ones with low performance and longest since review.
    """
    # Fetch tasks in unit
    from sqlmodel import select
    from units.models import UnitTaskLink

    db_tasks: list[Task] = session.exec(
        select(Task)
        .join(UnitTaskLink, Task.id == UnitTaskLink.task_id)
        .where(UnitTaskLink.unit_id == unit_id)
    ).all()

    if not db_tasks:
        return []

    # Fetch user progress links for these tasks
    task_ids = [t.id for t in db_tasks]
    progress_rows: list[TaskUserLink] = session.exec(
        select(TaskUserLink).where(
            TaskUserLink.user_id == user_id,
            TaskUserLink.task_id.in_(task_ids),
        )
    ).all()

    progress_by_task = {row.task_id: row for row in progress_rows}
    now = datetime.now(timezone.utc)

    scored = [
        (
            _compute_task_priority(task, progress_by_task.get(task.id), now),
            progress_by_task.get(task.id) is None,  # unseen flag
            task,
        )
        for task in db_tasks
    ]

    # Sort by priority desc (higher first), while keeping unseen before seen as tie-breaker
    # We can sort by (-priority, not unseen) to get desired order
    scored.sort(key=lambda x: (-x[0], not x[1]))

    ordered = [t for _, _, t in scored][:TASKS_PER_SESSION]
    return ordered
