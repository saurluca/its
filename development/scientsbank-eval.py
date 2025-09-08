# %%
from datasets import load_dataset
from datasets import ClassLabel
import dspy
import os
from dotenv import load_dotenv
from tqdm import tqdm
from sklearn.metrics import f1_score, precision_score, accuracy_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns


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

# shuffle ds
dataset = dataset.shuffle(seed=42)

dataset["train"][0]

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

    # score: int = dspy.OutputField(
    #     description="3 if the content of the student's answer is correct, 2 if it is partially correct but incomplete, 0 if it is contradictory, 1 if it is irrelevant."
    # )


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
scores = []
y_true = []
y_pred = []

number_of_examples = 100

for example in tqdm(dataset["train"]):
    pred = teacher(
        question=example["question"],
        reference_answer=example["reference_answer"],
        student_answer=example["student_answer"],
    )
    gold_score = example["label"]
    pred_score = pred.score
    scores.append(float(pred_score == gold_score))
    y_true.append(gold_score)
    y_pred.append(pred_score)
    if len(scores) >= number_of_examples:
        break

print(f"Average score: {sum(scores) / len(scores)}")
print(f"Correct: {sum(scores)} out of {len(scores)}")

# Calculate and print F1, precision, and accuracy
print(f"Accuracy: {accuracy_score(y_true, y_pred):.4f}")
print(f"Precision (macro): {precision_score(y_true, y_pred, average='macro'):.4f}")
print(f"F1 (macro): {f1_score(y_true, y_pred, average='macro'):.4f}")

# Plot confusion matrix
labels = dataset["train"].features["label"].names
cm = confusion_matrix(y_true, y_pred, labels=range(len(labels)))
plt.figure(figsize=(6, 5))
sns.heatmap(
    cm, annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels
)
plt.xlabel("Predicted label")
plt.ylabel("True label")
plt.title("Confusion Matrix")
plt.show()


# %%


def metric(gold, pred, trace=None):
    # gold is a DSPy Example with targets, pred is the model output
    gold_score = gold.label
    pred_score = pred.score

    return float(pred_score == gold_score)


evaluator = dspy.Evaluate(
    devset=dataset["train"][:20], num_threads=8, display_progress=True
)

# evaluator(teacher, metric=metric, display_table=5)
