# %%

import os
from dotenv import load_dotenv
import dspy
from pprint import pprint

load_dotenv()

lm = dspy.LM(
    "azure/gpt-4o",
    api_base="https://spg-piatutor.openai.azure.com/",
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version="2024-12-01-preview",
)

lm2 = dspy.LM(
    "ollama_chat/llama3.2:3b",
    api_base="http://localhost:11434",
    api_key="",
)

dspy.configure(lm=lm)


class Assistant(dspy.Signature):
    """You are a helpful assistant that can answer questions."""

    question: str = dspy.InputField(description="The question to answer.")
    answer: str = dspy.OutputField(description="The answer to the question.")


qa = dspy.Predict(Assistant)

response = qa(question="When is your knowledge cutoff?")
print("model", lm.model)
pprint(response.answer)

# # with dspy.context(lm=lm2):
qa2 = dspy.Predict(Assistant)


# def foo():
#     response2 = qa2(question="When is your knowledge cutoff")
#     return response2


# with dspy.context(lm=lm2):
#     response2 = foo()

response2 = qa2(question="When is your knowledge cutoff", lm=lm2)

print("model", lm2.model)
pprint(response2.answer)
