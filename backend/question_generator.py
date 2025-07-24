import dspy
import time
from tqdm import tqdm
import random

# TODO: validate and verify results: 1 answer correct, 3 wrong, answer is correct, results relevant
# TODO: also return the keypoint the answer was based on? For explainability, or for teacher.
# TODO: experiment wiht more nested data structure so answer / questions togeher. maybe easier for model to produce.

# IDEAS:
# split key points into list to generate question based on single key points instead of all at once.


class QuestionSingle(dspy.Signature):
    """Generate a single multiple choice question, answer options, and correct answer indices from key points."""

    text: str = dspy.InputField(description="The text to generate a question from.")

    question: str = dspy.OutputField(
        description="A single multiple choice question generated from the key points. It should foster a deep understanding of the material. The question should be short and concise."
    )
    answer_options: list[str] = dspy.OutputField(
        description="A list of 4 answer options for each question. Exactly one answer option is correct. The correct answer should always be in the first position."
    )


def generate_questions(document_id, chunks, num_questions=10):
    print(f"Generating questions for document {document_id} with {len(chunks)} chunks")
    questions = []
    answer_options = []
    question_generator = dspy.ChainOfThought(QuestionSingle)
    start_time = time.time()

    if num_questions != len(chunks):
        # randomly select num_questions chunks
        chunks = random.sample(chunks, num_questions)

    for chunk in tqdm(chunks):
        qg_response = question_generator(text=chunk["chunk_text"])

        if len(qg_response.answer_options) != 4:
            print(
                f"Skipping chunk {chunk['chunk_index']} because it has {len(qg_response.answer_options)} answer options, but should have exactly 4 choices."
            )
            continue

        questions.append(qg_response.question)
        answer_options.append(qg_response.answer_options)

    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")
    print(
        f"Generated {len(questions)} questions and {len(answer_options)} answer options in {end_time - start_time} seconds"
    )
    return questions, answer_options


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


def generate_questions_batch(document_id, chunks, num_questions=10):
    print(
        f"Batch-generating questions for document {document_id} with {len(chunks)} chunks"
    )
    if num_questions != len(chunks):
        chunks = random.sample(chunks, num_questions)

    chunk_texts = [chunk["chunk_text"] for chunk in chunks]
    question_generator = dspy.ChainOfThought(QuestionBatch)
    start_time = time.time()

    qg_response = question_generator(texts=chunk_texts)

    # Validate output
    questions = []
    answer_options = []
    for i, (q, opts) in enumerate(
        zip(qg_response.questions, qg_response.answer_options)
    ):
        if not isinstance(opts, list) or len(opts) != 4:
            print(
                f"Skipping question {i} because it has {len(opts) if isinstance(opts, list) else 'invalid'} answer options, should have exactly 4."
            )
            continue
        questions.append(q)
        answer_options.append(opts)

    end_time = time.time()
    print(f"Time taken (batch): {end_time - start_time} seconds")
    print(
        f"Generated {len(questions)} questions and {len(answer_options)} answer options in {end_time - start_time} seconds (batch)"
    )
    return questions, answer_options
