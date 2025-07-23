# %%
import dspy
from dotenv import load_dotenv
from db_utils import (
    get_document_content_from_db,
    save_key_points_to_db,
    save_questions_to_db,
)
from teacher import evaluate_student_answer


load_dotenv()

lm = dspy.LM("openai/gpt-4.1-nano")
dspy.configure(lm=lm)


# %% READ IN DOCUMENT

# raw_document_path = "data/documents/neuroscience_mini.pdf"
# text_document_path = "data/documents/neuroscience_mini.txt"

# document = extract_text_from_file(raw_document_path, output_path=text_document_path, save_to_file=True)

# test_document = read_text_from_file("data/documents/neuroscience_mini.txt")
# document = read_text_from_file(test_document)

doc_id = "83ea9618-eb51-4e98-af2b-5068590ef4c2"
document = get_document_content_from_db(doc_id)

print(document)


# %% SUMMARISE DOCUMENT

summarizer = dspy.ChainOfThought("document -> key_points")

response = summarizer(document=document)
key_points = response.key_points
print(key_points)

# save key points to db
save_key_points_to_db(doc_id, key_points)

# %% GENERATE QUESTIONS


class Question(dspy.Signature):
    """Generate multiple choice questions, answer options, and correct answer indices from key points."""

    key_points: str = dspy.InputField(description="The key points of the document.")

    questions: list[str] = dspy.OutputField(
        description="A list of multiple choice questions generated from the key points."
    )
    answer_options: list[list[str]] = dspy.OutputField(
        description="A list of answer options for each question. Each entry is a list of 4 answer strings."
    )
    correct_answers: list[int] = dspy.OutputField(
        description="A list of integers, each representing the index (0-3) of the correct answer in the answer options for each question."
    )


question_generator = dspy.ChainOfThought(Question)

qg_response = question_generator(key_points=key_points)

print(qg_response.questions[0])
print(qg_response.answer_options[0])
print("Correct answer: ", qg_response.correct_answers[0])

# Save generated questions to the database
save_questions_to_db(
    doc_id,
    qg_response.questions,
    qg_response.answer_options,
    qg_response.correct_answers,
)

# TODO: verify results: 1 answer correct, 3 wrong, answer is correct, results relevant
# TODO: also return the keypoint the answer was based on? For explainability, or for teacher.
# TODO: experiment wiht more nested data structure so answer / questions togeher. maybe easier for model to produce.

### ASK QUESTION

# %% EVALUATE STUDENT ANSWERS

evaluate_student_answer(
    question=qg_response.questions[0],
    answer_options=qg_response.answer_options[0],
    correct_answer=qg_response.correct_answers[0],
    student_answer=0,
)
