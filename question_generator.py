import dspy


# TODO: validate and verify results: 1 answer correct, 3 wrong, answer is correct, results relevant
# TODO: also return the keypoint the answer was based on? For explainability, or for teacher.
# TODO: experiment wiht more nested data structure so answer / questions togeher. maybe easier for model to produce.

# IDEAS:
# split key points into list to generate question based on single key points instead of all at once.


class QuestionSingle(dspy.Signature):
    """Generate a single multiple choice question, answer options, and correct answer indices from key points."""

    text: str = dspy.InputField(description="The text to generate a question from.")

    question: str = dspy.OutputField(
        description="A single multiple choice question generated from the key points. The question should be short and concise."
    )
    answer_options: list[str] = dspy.OutputField(
        description="A list of 4 answer options for each question. Exactly one answer option is correct. The correct answer should always be in the first position."
    )


# def validate_question_single(qg_response):
#     assert len(qg_response.answer_options) == 4, (
#         f"Answer options for question has {len(qg_response.answer_options)} choices, "
#         "but should have exactly 4 choices."
#     )


# def generate_question_single(text):
#     question_generator = dspy.ChainOfThought(QuestionSingle)
#     qg_response = question_generator(text=text)

#     validate_question_single(qg_response)

#     return qg_response


def generate_questions(document_id, chunks):
    print(f"Generating questions for document {document_id} with {len(chunks)} chunks")
    questions = []
    answer_options = []
    for chunk in chunks:
        question_generator = dspy.ChainOfThought(QuestionSingle)
        qg_response = question_generator(text=chunk["chunk_text"])

        if len(qg_response.answer_options) != 4:
            print(
                f"Skipping chunk {chunk['chunk_index']} because it has {len(qg_response.answer_options)} answer options, but should have exactly 4 choices."
            )
            continue

        questions.append(qg_response.question)
        answer_options.append(qg_response.answer_options)

    print(
        f"Generated {len(questions)} questions and {len(answer_options)} answer options"
    )
    return questions, answer_options
