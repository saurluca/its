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
    
    # Save generated questions to the database
    save_questions_to_db(
        doc_id,
        qg_response.questions,
        qg_response.answer_options,
        qg_response.correct_answers,
    )

    return qg_response
