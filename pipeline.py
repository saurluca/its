# %%
import dspy
from dotenv import load_dotenv
from text_processing import get_text_from_db


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
document = get_text_from_db(doc_id)

print(document)


# %% SUMMARISE DOCUMENT

summarizer = dspy.ChainOfThought("document -> key_points")

response = summarizer(document=document)
key_points = response.key_points
print(key_points)



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

# TODO: verify results: 1 answer correct, 3 wrong, answer is correct, results relevant
# TODO: also return the keypoint the answer was based on? For explainability, or for teacher.
# TODO: experiment wiht more nested data structure so answer / questions togeher. maybe easier for model to produce.

### ASK QUESTION

# %% EVALUATE STUDENT ANSWERS


class Teacher(dspy.Signature):
    """Evaluate the student's answer, and provide feedback."""

    # input fields
    question: str = dspy.InputField(
        description="The question to be answered and the 4 answer options."
    )
    answer_options: list[str] = dspy.InputField(
        description="The 4 answer options for the question."
    )
    correct_answer: int = dspy.InputField(
        description="The correct answer to the question."
    )
    student_answer: int = dspy.InputField(
        description="The student's answer to the question."
    )

    # output fields
    feedback: str = dspy.OutputField(
        description="Short feedback on the student's answer. If the answer is incorrect, provide a hint to the correct answer."
    )


teacher = dspy.ChainOfThought(Teacher)

response = teacher(
    question=qg_response.questions[0],
    answer_options=qg_response.answer_options[0],
    correct_answer=qg_response.correct_answers[0],
    student_answer=0,
)

print(response.feedback)
