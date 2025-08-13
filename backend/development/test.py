# %%

import os
from openai import AzureOpenAI
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
dspy.configure(lm=lm)


class Assistant(dspy.Signature):
    """You are a python programmer that can write code to solve problems."""

    coding_problem: str = dspy.InputField(description="The coding problem to solve.")
    code: str = dspy.OutputField(description="The python code to solve the problem.")


qa = dspy.ChainOfThought(Assistant)


response = qa(
    coding_problem="Write a small DSPy programm that has a ChainOfThough agent that responds to questios. configured with openai's gpt-4o-mini model."
)
pprint(response.code)

# %%
11
