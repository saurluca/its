import dspy
from db_utils import save_questions_to_db, get_key_points_from_db


# TODO: validate and verify results: 1 answer correct, 3 wrong, answer is correct, results relevant
# TODO: also return the keypoint the answer was based on? For explainability, or for teacher.
# TODO: experiment wiht more nested data structure so answer / questions togeher. maybe easier for model to produce.

# IDEAS:
# split key points into list to generate question based on single key points instead of all at once.


class Question(dspy.Signature):
    """Generate multiple choice questions, answer options, and correct answer indices from key points."""

    key_points: str = dspy.InputField(description="The key points of the document.")

    questions: list[str] = dspy.OutputField(
        description="A list of multiple choice questions generated from the key points. The questions should be short and concise."
    )
    answer_options: list[list[str]] = dspy.OutputField(
        description="A list of 4 answer options for each question. Exactly one answer option is correct. The correct answer should always be in the first position."
    )


class QuestionSingle(dspy.Signature):
    """Generate a single multiple choice question, answer options, and correct answer indices from key points."""

    key_points: str = dspy.InputField(description="The key points of the document.")

    question: str = dspy.OutputField(
        description="A single multiple choice question generated from the key points. The question should be short and concise."
    )
    answer_options: list[str] = dspy.OutputField(
        description="A list of 4 answer options for each question. Exactly one answer option is correct. The correct answer should always be in the first position."
    )


def validate_question_single(qg_response):
    assert len(qg_response.answer_options) == 4, (
        f"Answer options for question has {len(qg_response.answer_options)} choices, "
        "but should have exactly 4 choices."
    )


def generate_question_single(key_points, num_questions):
    question_generator = dspy.ChainOfThought(QuestionSingle, n=num_questions)
    qg_response = question_generator(key_points=key_points)

    validate_question_single(qg_response)

    return qg_response


def generate_questions(doc_id):
    key_points = get_key_points_from_db(doc_id)

    question_generator = dspy.ChainOfThought(Question)

    qg_response = question_generator(key_points=key_points)

    # Validate the generated data structure
    num_questions = len(qg_response.questions)
    num_answer_options = len(qg_response.answer_options)

    # Check that all lists have the same length
    if not (num_questions == num_answer_options):
        raise ValueError(
            f"Mismatch in data lengths: {num_questions} questions, "
            f"{num_answer_options} answer options. "
            "All should be equal."
        )

    # Check that each answer option has exactly 4 choices
    for i, options in enumerate(qg_response.answer_options):
        if len(options) != 4:
            raise ValueError(
                f"Answer options for question {i + 1} has {len(options)} choices, "
                "but should have exactly 4 choices."
            )

    # Save generated questions to the database
    save_questions_to_db(
        doc_id,
        qg_response.questions,
        qg_response.answer_options,
    )

    return qg_response
