# %%
import dspy
from dotenv import load_dotenv
import pandas as pd
from dspy.evaluate import Evaluate
from dspy.teleprompt import BootstrapFewShotWithRandomSearch

load_dotenv()

# lm = dspy.LM("groq/deepseek-r1-distill-llama-70b", api_key=os.getenv("GROK_API_KEY"))
lm = dspy.LM("ollama_chat/mistral:7b", api_base="http://localhost:11434", api_key="")
dspy.configure(lm=lm)

# load in csv
df = pd.read_csv("../data/tasks.csv")

# select relevant columns
df = df[["topic", "question", "correct_answer", "student_answer", "ground_truth"]]
df.head()

# %%


def convert_df_to_dspy_format(dataframe):
    """Convert DataFrame rows to DSPy Example objects."""
    examples = []
    for _, row in dataframe.iterrows():
        # Create DSPy Example with inputs and targets
        example = dspy.Example(
            topic=row["topic"],
            question=row["question"],
            correct_answer=row["correct_answer"],
            student_answer=row["student_answer"],
            ground_truth=row["ground_truth"],
        ).with_inputs("topic", "question", "correct_answer", "student_answer")
        examples.append(example)
    return examples


# %%


class TeacherFreeTextBinary(dspy.Signature):
    """You are grading a student's response to a short answer-question related to the {topic} below.

    Students have been asked this question:  {question}

    A correct answer to this question is: {correct_answer}

    Your task is to decide if the student’s answer is correct or wrong.

    A student answer is wrong if it misses a key part of the correct answer.

    If the student response is correct, you will respond with score = 1.
    If the student response is wrong, you will respond with score = 0.

    MUST: Always respond with a score. Either score = 1 or score = 0.
    """

    topic: str = dspy.InputField(description="The topic of the question.")

    question: str = dspy.InputField(description="The question asked to the student.")

    correct_answer: str = dspy.InputField(
        description="The correct answer to the question."
    )

    student_answer: str = dspy.InputField(
        description="The student's answer to the question."
    )

    score: int = dspy.OutputField(
        description="1 if the student's answer is correct, 0 if it is wrong."
    )


teacher = dspy.Predict(TeacherFreeTextBinary)


# %%


def metric(gold, pred, trace=None):
    # gold is a DSPy Example with targets, pred is the model output
    # gold_question = gold.question
    generated_answer = int(pred.score)
    correct_answer = int(gold.ground_truth)

    # Check for NaN values first
    if pd.isna(correct_answer) or pd.isna(generated_answer):
        return 0.0

    # For single sample comparison, use simple accuracy instead of Cohen's kappa
    if generated_answer == correct_answer:
        return 1.0
    else:
        return 0.0


# shuffle df
df = df.sample(frac=1, random_state=42).reset_index(drop=True)


# select first 20 rows
df_dev = df.head(100)
df_test = df.tail(50)

# Convert DataFrame to DSPy format
devset = convert_df_to_dspy_format(df_dev)
testset = convert_df_to_dspy_format(df_test)

# Evaluate basic
y_true = []
y_pred = []

n_problematic_samples = 0

# for example in tqdm(devset):
#     try:
#         pred = teacher(
#             topic=example.topic,
#             question=example.question,
#             correct_answer=example.correct_answer,
#             student_answer=example.student_answer,
#         )

#         # gold.ground_truth is assumed to be 1 or 0
#         y_true.append(example.ground_truth)
#         # pred.score is assumed to be 1 or 0
#         y_pred.append(pred.score)

#     except Exception as e:
#         n_problematic_samples += 1
#         continue

#     # print(f"Evaluation: {pred.score}, Ground Truth: {example.ground_truth}")

# if len(y_true) > 0:
#     precision = precision_score(y_true, y_pred, zero_division=0)
#     recall = recall_score(y_true, y_pred, zero_division=0)
#     f1 = f1_score(y_true, y_pred, zero_division=0)
#     kappa = cohen_kappa_score(y_true, y_pred)

#     print(f"Precision: {precision:.4f}")
#     print(f"Recall: {recall:.4f}")
#     print(f"F1 Score: {f1:.4f}")
#     print(f"Cohen's Kappa: {kappa:.4f}")
#     print(
#         f"Mean score: {sum([int(a == b) for a, b in zip(y_true, y_pred)]) / len(y_true)} with {n_problematic_samples} problematic samples"
#     )
# else:
#     print("No valid samples to evaluate.")

# %%


evaluator = Evaluate(
    devset=devset, num_threads=4, display_progress=False, display_table=False
)

# Launch evaluation.
evaluator(teacher, metric=metric)


# %%
#
# improve the teacher

# Set up the optimizer: we want to "bootstrap" (i.e., self-generate) 8-shot examples of your program's steps.
# The optimizer will repeat this 10 times (plus some initial attempts) before selecting its best attempt on the devset.
config = dict(
    max_bootstrapped_demos=4,
    max_labeled_demos=4,
    num_candidate_programs=4,
    num_threads=8,
)

teleprompter = BootstrapFewShotWithRandomSearch(metric=metric, **config)
optimized_teacher = teleprompter.compile(teacher, trainset=devset)


# # %%

# optimized_teacher.save("optimized_teacher.json")

evaluator(optimized_teacher, metric=metric)

# # %%
