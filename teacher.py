import dspy


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


def evaluate_student_answer(question, answer_options, student_answer):
    teacher = dspy.ChainOfThought(Teacher)
    response = teacher(
        question=question,
        answer_options=answer_options,
        student_answer=student_answer,
    )
    return response.feedback
