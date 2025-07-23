import dspy
from db_utils import save_questions_to_db, get_key_points_from_db


# TODO: verify results: 1 answer correct, 3 wrong, answer is correct, results relevant
# TODO: also return the keypoint the answer was based on? For explainability, or for teacher.
# TODO: experiment wiht more nested data structure so answer / questions togeher. maybe easier for model to produce.

# IDEA
# The correct answer is always in the first position, and the answers are shuffled in the frontend. Thus one less thing to save.


class Question(dspy.Signature):
    """Generate multiple choice questions, answer options, and correct answer indices from key points."""

    key_points: str = dspy.InputField(description="The key points of the document.")

    questions: list[str] = dspy.OutputField(
        description="A list of multiple choice questions generated from the key points."
    )
    answer_options: list[list[str]] = dspy.OutputField(
        description="A list of answer options for each question. Each entry is a list of 4 answer strings. The correct answer should be in a random position in the list."
    )
    correct_answers: list[int] = dspy.OutputField(
        description="A list of integers, each representing the index (0-3) of the correct answer in the answer options for each question."
    )


def generate_questions(doc_id):
    key_points = get_key_points_from_db(doc_id)

    question_generator = dspy.ChainOfThought(Question)

    qg_response = question_generator(key_points=key_points)

    # Validate the generated data structure
    num_questions = len(qg_response.questions)
    num_answer_options = len(qg_response.answer_options)
    num_correct_answers = len(qg_response.correct_answers)

    # Check that all lists have the same length
    if not (num_questions == num_answer_options == num_correct_answers):
        raise ValueError(
            f"Mismatch in data lengths: {num_questions} questions, "
            f"{num_answer_options} answer options, {num_correct_answers} correct answers. "
            "All should be equal."
        )

    # Check that each answer option has exactly 4 choices
    for i, options in enumerate(qg_response.answer_options):
        if len(options) != 4:
            raise ValueError(
                f"Answer options for question {i + 1} has {len(options)} choices, "
                "but should have exactly 4 choices."
            )

    # Check that each correct answer index is valid (0-3)
    for i, correct_idx in enumerate(qg_response.correct_answers):
        if not (0 <= correct_idx <= 3):
            raise ValueError(
                f"Correct answer index for question {i + 1} is {correct_idx}, "
                "but should be between 0 and 3 (inclusive)."
            )

    # Save generated questions to the database
    save_questions_to_db(
        doc_id,
        qg_response.questions,
        qg_response.answer_options,
        qg_response.correct_answers,
    )

    return qg_response
