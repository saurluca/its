# %%
import dspy
from dotenv import load_dotenv
import os

load_dotenv()


print("Hello world!")

# lm = dspy.LM("groq/deepseek-r1-distill-llama-70b", api_key=os.getenv("GROQ_API_KEY"))
lm = dspy.LM("ollama_chat/llama3.2", api_base="http://localhost:11434", api_key="test")

dspy.configure(lm=lm)


# result = lm("Say this is a test!", temperature=0.7)
# print(result)

# %%

model = dspy.ChainOfThought("question -> answer")

result = model(question="What is the capital of France?")


print(result)

# %%
