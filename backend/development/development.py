# %%
import dspy
from dotenv import load_dotenv
from datasets import load_dataset
from dspy.teleprompt import BootstrapFewShotWithRandomSearch
from tqdm import tqdm
import os

load_dotenv()

lm = dspy.LM("groq/deepseek-r1-distill-llama-70b", api_key=os.getenv("GROK_API_KEY"))
# lm = dspy.LM("ollama_chat/llama3.2", api_base="http://localhost:11434", api_key="test")
dspy.configure(lm=lm)

ds = load_dataset("rajpurkar/squad", split="train")

# shuffle ds
ds = ds.shuffle(seed=42)

# Split the dataset into train, validation, and test sets
# Convert to DSPy Example format with inputs and targets


def convert_to_dspy_format(dataset):
    examples = []
    for item in dataset:
        # Create DSPy Example with inputs and targets
        example = dspy.Example(
            context=item["context"],
            question=item["question"],
            answer=item["answers"]["text"][0] if item["answers"]["text"] else "",
        ).with_inputs("context")
        examples.append(example)
    return examples


n_train = 25
n_val = 100
n_test = 125

trainset = convert_to_dspy_format(ds.select(range(n_train)))
valset = convert_to_dspy_format(ds.select(range(n_train, n_train + n_val)))
testset = convert_to_dspy_format(
    ds.select(range(n_train + n_val, n_train + n_val + n_test))
)


# %%


# Question generation signatures
class QuestionSingle(dspy.Signature):
    """Generate a single multiple choice question, answer options, and correct answer indices from key points."""

    context: str = dspy.InputField(description="The text to generate a question from.")

    question: str = dspy.OutputField(
        description="A single multiple choice question generated from the key points. It should foster a deep understanding of the material. The question should be short and concise."
    )
    answer: str = dspy.OutputField(description="The correct answer to the question.")


question_generator = dspy.Predict(QuestionSingle)


# %%


# metric definition
# Define the signature for automatic assessments.
class AssessSameQuestion(dspy.Signature):
    """Assess the quality of a question along the specified dimension."""

    generated_question: str = dspy.InputField()
    gold_question: str = dspy.InputField()
    is_correct: bool = dspy.OutputField(
        description="Wether the generated question is the same as the gold question."
    )


class AssessCorrectness(dspy.Signature):
    """Assess the quality of a question along the specified dimension."""

    generated_question: str = dspy.InputField()
    generated_answer: str = dspy.InputField()
    context: str = dspy.InputField()
    is_correct: bool = dspy.OutputField(
        description="Wether the generated answer is correct based on the context."
    )


class AssessRelevance(dspy.Signature):
    """Assess the quality of a question along the specified dimension."""

    generated_question: str = dspy.InputField()
    context: str = dspy.InputField()
    is_relevant: bool = dspy.OutputField(
        description="Wether the generated question is relevant to the context."
    )


correctness_program = dspy.Predict(AssessCorrectness)
relevance_program = dspy.Predict(AssessRelevance)


def metric(gold, pred, trace=None):
    # gold is a DSPy Example with targets, pred is the model output
    # gold_question = gold.question
    generated_question = pred.question
    generated_answer = pred.answer
    context = gold.context

    correctness_result = correctness_program(
        generated_question=generated_question,
        generated_answer=generated_answer,
        context=context,
    )
    relevance_result = relevance_program(
        generated_question=generated_question, context=context
    )

    score = correctness_result.is_correct + relevance_result.is_relevant

    if trace is not None:
        return score >= 2
    return score / 2.0


evaluator = dspy.Evaluate(devset=trainset, num_threads=8, display_progress=True)

# %%

# # ASSESS QUESTION GENERATION
# scores = []

# for input_example in tqdm(trainset):
#     response = question_generator(context=input_example.context)
#     score = metric(input_example, response)
#     scores.append(score)


evaluator(question_generator, metric=metric, display_table=5)


# %%

# ASSES METRIC ON GOLD QUESTION
scores = []

for input_example in tqdm(trainset):
    score = metric(input_example, input_example)
    scores.append(score)

print(f"Average score: {sum(scores) / len(scores)}")


# %%

# Set up the optimizer: we want to "bootstrap" (i.e., self-generate) 8-shot examples of your program's steps.
# The optimizer will repeat this 10 times (plus some initial attempts) before selecting its best attempt on the devset.
config = dict(
    max_bootstrapped_demos=4,
    max_labeled_demos=4,
    num_candidate_programs=4,
    num_threads=4,
)

teleprompter = BootstrapFewShotWithRandomSearch(metric=metric, **config)
optimized_program = teleprompter.compile(question_generator, trainset=trainset)


# %%

optimized_program(context=trainset[0].context)

# %%

optimized_program.save("optimized_program.json")

# %%


# IDAES
"""
- Build a GAN like model, that generates questions, and a discriminator that checks if the question is an original question
or generated question.
- 

"""
