import dspy
import time
from tqdm import tqdm
import random
from typing import List, Tuple

from utils import save_key_points_to_db, get_document_content_from_db
from constants import DEFAULT_NUM_QUESTIONS, REQUIRED_ANSWER_OPTIONS
from exceptions import QuestionGenerationError


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
    student_answer: int = dspy.InputField(
        description="The student's answer to the question."
    )

    # output fields
    feedback: str = dspy.OutputField(
        description="Short feedback on the student's answer. The correct answer is always the first option. If the student's answer is incorrect, provide a hint to the correct answer."
    )


# Question generation services
def generate_questions(
    document_id: str, chunks: List[dict], num_questions: int = DEFAULT_NUM_QUESTIONS
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
        raise QuestionGenerationError(
            "No questions could be generated from the provided chunks"
        )

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
            raise QuestionGenerationError(
                "No valid questions could be generated in batch mode"
            )

        return questions, answer_options
    except Exception as e:
        raise QuestionGenerationError(f"Batch question generation failed: {e}")


# Summarization service
def summarise_document(doc_id: str) -> str:
    """
    Summarize a document and save key points to database

    Args:
        doc_id: Document ID

    Returns:
        Key points summary
    """
    document = get_document_content_from_db(doc_id)

    summarizer = dspy.ChainOfThought("document -> key_points")

    response = summarizer(document=document)

    save_key_points_to_db(doc_id, response.key_points)

    return response.key_points


# Teacher evaluation service
def evaluate_student_answer(
    question: str, answer_options: List[str], student_answer: int
) -> str:
    """
    Evaluate a student's answer and provide feedback

    Args:
        question: The question text
        answer_options: List of answer options
        student_answer: Student's selected answer index

    Returns:
        Feedback text
    """
    if student_answer < 0 or student_answer >= len(answer_options):
        return "Invalid answer selection. Please choose a valid option."

    teacher = dspy.ChainOfThought(Teacher)

    try:
        response = teacher(
            question=question,
            answer_options=answer_options,
            student_answer=student_answer,
        )
        return response.feedback
    except Exception as e:
        return f"Error evaluating answer: {e}"
