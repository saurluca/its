# %%
from datasets import load_dataset
from datasets import ClassLabel
import dspy
import os
from dotenv import load_dotenv
from dspy.teleprompt import MIPROv2


load_dotenv()


azure_api_key = os.getenv("AZURE_API_KEY")
azure_api_base = os.getenv("AZURE_API_BASE")

lm = dspy.LM(
    "azure/gpt-4o-mini",
    api_base=azure_api_base,
    api_key=azure_api_key,
    api_version="2024-12-01-preview",
)
dspy.configure(lm=lm)

dataset = load_dataset("nkazi/SciEntsBank", cache_dir="../data")

# convert to 4 way classification
dataset = dataset.align_labels_with_mapping(
    {
        "correct": 0,
        "contradictory": 1,
        "partially_correct_incomplete": 1,
        "irrelevant": 1,
        "non_domain": 1,
    },
    "label",
)
dataset = dataset.cast_column("label", ClassLabel(names=["correct", "incorrect"]))

# shuffle ds for reproducibility
dataset = dataset.shuffle(seed=42)

# %%


# Convert HF dataset split into DSPy Examples expected by our signature
def convert_to_dspy_format(dataset_split):
    examples = []
    for item in dataset_split:
        example = dspy.Example(
            question=item["question"],
            reference_answer=item["reference_answer"],
            student_answer=item["student_answer"],
            label=item["label"],
        ).with_inputs("question", "reference_answer", "student_answer")
        examples.append(example)
    return examples


# %%


class TeacherFreeText3Way(dspy.Signature):
    """You are a teacher for undergraduate students.
    Your job is to evaluate the student's answers to a short answer-question.

    Your task is to decide if the student’s answer is correct, partially correct but incomplete, irrelevant or contradictory.
    Answer based on the provided correct answer only.

    Correct: The student's answer is correct and includes the key points from the correct answer.
    If the student response is correct, you will respond with score = 0

    Contradictory: The student's answer directly contradicts the correct answer.
    If the student response is contradictory, you will respond with score = 1

    Incorrect: The student's answer is incorrect, for example it is not related to the question or it is not correct, but does not contradict the correct answer.
    If the student response is incorrect, you will respond with score = 2
    """

    # Irrelevant: The student's answer is irrelevant to the question.
    # If the student response is irrelevant, you will respond with score = 3

    question: str = dspy.InputField(description="The question asked to the student.")

    reference_answer: str = dspy.InputField(
        description="The correct answer to the question."
    )

    student_answer: str = dspy.InputField(
        description="The student's answer to the question."
    )

    score: int = dspy.OutputField(
        description="0 if the content of the student's answer is correct, 1 if it is contradictory, 2 if it is incorrect."
    )


class TeacherFreeText2Way(dspy.Signature):
    """You are a teacher for undergraduate students.
    Your job is to evaluate the student's answers to a short answer-question.

    Your task is to decide if the student’s answer is correct or incorrect.
    Answer based on the provided correct answer.

    Correct: The student's answer is correct and matches the correct answer.
    If the student response is correct, you will respond with score = 0

    Incorrect: The student's answer is incorrect, for example it is not related to the question or it is not correct,
    or if it contradict the correct answer.
    If the student response is incorrect, you will respond with score = 1
    """

    question: str = dspy.InputField(description="The question asked to the student.")

    reference_answer: str = dspy.InputField(
        description="The correct answer to the question."
    )

    student_answer: str = dspy.InputField(
        description="The student's answer to the question."
    )

    score: int = dspy.OutputField(
        description="0 if the content of the student's answer is correct, 1 if it is incorrect."
    )


# %%

teacher = dspy.Predict(TeacherFreeText2Way)

# Select a small subset (300) from train for optimization and evaluation
subset = dataset["train"].select(range(1000))

# Split into train/val/test: 60% / 20% / 20%
train_size = int(0.6 * len(subset))
val_size = int(0.2 * len(subset))
test_size = len(subset) - train_size - val_size

print(f"Number of train examples: {train_size}")
print(f"Number of val examples: {val_size}")
print(f"Number of test examples: {test_size}")

train_split = subset.select(range(0, train_size))
val_split = subset.select(range(train_size, train_size + val_size))
test_split = subset.select(
    range(train_size + val_size, train_size + val_size + test_size)
)

# Convert to DSPy Examples
train_examples = convert_to_dspy_format(train_split)
val_examples = convert_to_dspy_format(val_split)
test_examples = convert_to_dspy_format(test_split)


# %%


def metric(gold, pred, trace=None):
    # gold is a DSPy Example with targets, pred is the model output
    gold_score = gold.label
    pred_score = pred.score

    return float(pred_score == gold_score)


# Build the program as a DSPy module
class JudgeProgram(dspy.Module):
    def __init__(self):
        super().__init__()
        self.judge = dspy.Predict(TeacherFreeText2Way)

    def forward(self, question, reference_answer, student_answer):
        return self.judge(
            question=question,
            reference_answer=reference_answer,
            student_answer=student_answer,
        )


program = JudgeProgram()

# Evaluate baseline on held-out test set
baseline_evaluator = dspy.Evaluate(
    devset=test_examples, metric=metric, display_progress=True, display_table=False
)
# %%

baseline_score = baseline_evaluator(program)
print(f"Baseline accuracy (test): {baseline_score.score}")

# %%

# Optimize with MIPROv2
# optimizer_m = MIPROv2(
#     metric=metric,
#     auto="medium",
#     num_threads=12,
# )

# optimized_program = optimizer_m.compile(
#     student=program,
#     trainset=train_examples,
#     valset=val_examples,
#     max_bootstrapped_demos=4,
#     max_labeled_demos=6,  # number of examples in prompt
# )

optimizer_b = dspy.BootstrapFewShot(
    metric=metric,
    max_bootstrapped_demos=4,
    max_labeled_demos=2,
)


optimized_program = optimizer_b.compile(
    student=program,
    trainset=train_examples,
)

# Evaluate optimized program on the same held-out test set
optimized_score = baseline_evaluator(optimized_program)
print(f"Optimized accuracy (test): {optimized_score.score}")

# %%

optimized_score = baseline_evaluator(optimized_program)

# %%
optimized_program.save("optimised_program.json")
