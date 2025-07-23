# %%
import dspy
from dotenv import load_dotenv
from db_utils import get_document_content_from_db
from teacher import evaluate_student_answer
from summarizer import summarise_document
from question_generator import generate_questions


load_dotenv()

lm = dspy.LM("openai/gpt-4.1-nano")
dspy.configure(lm=lm)


# %% READ IN DOCUMENT

# raw_document_path = "data/documents/2_anonymization_I.pdf"
# text_document_path = "data/documents/2_anonymization_I.txt"

# document = extract_text_from_file(raw_document_path, output_path=text_document_path, save_to_file=True)

# test_document = read_text_from_file("data/documents/neuroscience_mini.txt")
# document = read_text_from_file(test_document)

doc_id = "2be3c874-20e3-4d69-a0b4-ffe6e021c206"
document = get_document_content_from_db(doc_id)

# print(document)

# %% SUMMARISE DOCUMENT

key_points = summarise_document(doc_id)

print(key_points)
# %% GENERATE QUESTIONS

qg_response = generate_questions(doc_id)

print(qg_response.questions[0])
print(qg_response.answer_options[0])
print("Correct answer: ", qg_response.correct_answers[0])

### ASK QUESTION

# %% EVALUATE STUDENT ANSWERS

evaluate_student_answer(
    question=qg_response.questions[0],
    answer_options=qg_response.answer_options[0],
    correct_answer=qg_response.correct_answers[0],
    student_answer=0,
)
