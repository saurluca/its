from typing import List
from uuid import UUID
import dspy
import time
from tqdm import tqdm
import random
from fastapi import HTTPException

from constants import REQUIRED_ANSWER_OPTIONS
from documents.models import Chunk
from tasks.models import (
    Task,
    TaskType,
    AnswerOption,
    TaskReadTeacher,
    TeacherResponseMultipleChoice,
    TeacherResponseFreeText,
)


class QuestionMultipleChoice(dspy.Signature):
    """Generate a single multiple choice question, answer options, and correct answer indices from a text chunk."""

    text: str = dspy.InputField(description="The text to generate a question from.")

    question: str = dspy.OutputField(
        description="A single multiple choice question generated from the key points. It should foster a deep understanding of the material. The question should be short and concise."
    )
    answer: list[str] = dspy.OutputField(
        description="A list of 4 answer options for each question. Exactly one answer option is correct. The correct answer should always be in the first position. Do not enumerate the answer options, no numbering or alphabet."
    )


class QuestionFreeText(dspy.Signature):
    """Generate a single free text question from a text chunk and an ideal answer."""

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


class QuestionFreeTextBinary(dspy.Signature):
    """You are grading 20 year old students' responses to short answer-questions about the {text} below.

    Students have been asked this question:  {question}

    A correct answer to this question is: {correct_answer}

    Your task is to decide if the student’s answer is correct or wrong.

    A student answer is wrong if it misses a key part of the correct answer.

    If the student response is correct, you will respond OUTPUT = 1.
    If the student response is wrong, you will respond OUTPUT = 0.."""

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


class TeacherFreeText(dspy.Signature):
    """Evaluate the student's answer and provide feedback that is tightly aligned with the assigned score.

    Use ONLY the provided chunk and ideal answer as the source of truth. Do not use outside knowledge.
    For free-text questions, the ideal answer is the correct entry in task_teacher.answer_options (created during question generation).

    Scoring rubric (0–10):
    - 9–10 (Excellent): Fully correct, comprehensive, grounded in the chunk; no inaccuracies; clear and concise.
    - 7–8 (Good): Mostly correct and grounded; minor omissions or slight imprecision; no major errors.
    - 5–6 (Partial): Partially correct; misses important points or includes vague phrasing; may have minor inaccuracies.
    - 3–4 (Poor): Mostly incorrect or incomplete; mentions a relevant fragment but lacks grounding or includes notable errors.
    - 1–2 (Very poor): Off-topic or largely incorrect; little to no grounding; serious errors.
    - 0 (No answer): Empty, "I don't know", or contradicts the chunk/ideal answer.

    Scoring procedure internally (must follow):
    1) Extract 2–4 key points from the ideal answer and the chunk.
    2) Compare the student's answer against each key point, citing brief evidence from the chunk when possible.
    3) Assign sub-scores and sum to an integer 0–10:
       - Coverage (0–4): How many key points are correctly addressed?
       - Correctness & grounding (0–4): Are statements accurate and supported by the chunk?
       - Clarity (0–2): Is the answer clear, direct, and free of fluff?
    4) Clamp the total to [0, 10]. This total is the final score.

    Feedback format(must use this structure):
    <mistakes, improvements, evaluation: concise, actionable tips>
    Final score: N/10

    Few-shot guidance (style, not content):
    - High-scoring example (9–10): Feedback cites all key points covered and explains why they are correct and grounded; improvements are minor. Final score matches the analysis.
    - Mid-scoring example (5–6): Feedback notes some correct elements but highlights missing key points and minor inaccuracies; specific improvement tips; final score reflects partial coverage.
    - Low-scoring example (0–2): Feedback states the answer is off-topic or incorrect, explains the mismatch with the chunk, and gives concrete guidance on what to include; final score near 0–2.

    The feedback must end with "Final score: N/10" where N equals the integer in the score field.
    """

    task_teacher: TaskReadTeacher = dspy.InputField(
        description="Includes the question, answer options, and the chunk of text related to the question. Source of truth for the question and answer options."
    )

    student_answer: str = dspy.InputField(
        description="The student's answer to the question."
    )

    feedback: str = dspy.OutputField(
        description=(
            "Provide structured feedback on Mistakes and improvements and end with Final score: N/10. The reasoning must reference the rubric, "
            "compare the student's answer to each key point, and be concise and specific."
        )
    )

    score: int = dspy.OutputField(
        description=(
            "An integer in [0, 10] computed exactly as described in the rubric (Coverage 0–4 + Correctness & grounding 0–4 + Clarity 0–2). "
            "This number MUST match the N in the feedback line 'Final score: N/10'."
        )
    )


class TeacherFreeTextBinary(dspy.Signature):
    """You are grading a student's response to a short answer-question  about the {chunk} below.

    Students have been asked this question:  {question}

    A correct answer to this question is: {correct_answer}

    Your task is to decide if the student’s answer is correct or wrong.

    A student answer is wrong if it misses a key part of the correct answer.
    Ignore Grammar and Spelling mistakes, only evaluate the content.

    If the student response is correct, you will respond with output = 1.
    If the student response is wrong, you will respond with output = 0.
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

    output: int = dspy.OutputField(
        description="1 if the content of the student's answer is correct, 0 if it is wrong."
    )


class TeacherMultipleChoice(dspy.Signature):
    """Evaluate the student's answer, and provide feedback."""

    task_teacher: TaskReadTeacher = dspy.InputField(
        description="Includes the question, answer options, and the chunk of text related to the question."
    )

    student_answer: str = dspy.InputField(
        description="The student's answer to the question."
    )

    feedback: str = dspy.OutputField(
        description="Short and concise feedback for the student based on their answer, if it is correct or incorrect, based on the chunk and the answer options."
        "If it is incorrect, provide a short explanation of what the correct answer is and why it is correct. The feedback should be based on the student's answer and the chunk."
    )


def _get_question_generator(question_type: str):
    """Get the appropriate question generator based on question type."""
    if question_type == "multiple_choice":
        return dspy.ChainOfThought(QuestionMultipleChoice)
    elif question_type == "free_text":
        return dspy.ChainOfThought(QuestionFreeText)
    else:
        raise ValueError(f"Invalid question type: {question_type}")


def _generate_single_question(
    chunk: Chunk, question_generator, question_type: str, lm: dspy.LM
):
    """Generate a single question from a chunk."""
    try:
        qg_response = question_generator(text=chunk.chunk_text, lm=lm)

        # Validate multiple choice questions have the correct number of answer options
        if (
            question_type == "multiple_choice"
            and len(qg_response.answer) != REQUIRED_ANSWER_OPTIONS
        ):
            return None

        return qg_response
    except Exception as e:
        print(f"Error generating question for chunk {chunk.id}: {e}")
        return None


def _create_task_from_response(qg_response, question_type: str, chunk_id: UUID) -> Task:
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
    elif question_type == "free_text":
        answer_option = AnswerOption(
            answer=qg_response.answer,
            is_correct=True,  # The ideal answer is always correct
            task=task,
        )
        task.answer_options.append(answer_option)

    return task


def generate_questions(
    document_id: UUID,
    chunks: List[Chunk],
    lm: dspy.LM,
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
            chunk, question_generator, question_type, lm
        )

        if qg_response is not None:
            task = _create_task_from_response(qg_response, question_type, chunk.id)
            tasks.append(task)

    end_time = time.time()
    print(f"Generated {len(tasks)} tasks in {end_time - start_time} seconds")

    if not tasks:
        raise Exception("No questions could be generated from the provided chunks")

    return tasks


def evaluate_student_answer(
    task_teacher: TaskReadTeacher,
    student_answer: str,
    task_type: TaskType,
    lm: dspy.LM,
) -> TeacherResponseMultipleChoice | TeacherResponseFreeText:
    if task_type == TaskType.MULTIPLE_CHOICE:
        teacher = dspy.ChainOfThought(TeacherMultipleChoice)
    elif task_type == TaskType.FREE_TEXT:
        # teacher = dspy.ChainOfThought(TeacherFreeText)
        teacher = dspy.ChainOfThought(TeacherFreeTextBinary)

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
        response.feedback = "This is a test feedback"

        print("response", response)

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating answer: {e}")
