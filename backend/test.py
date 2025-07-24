# %%
import dspy
from dotenv import load_dotenv
import os   
load_dotenv()

lm = dspy.LM("groq/deepseek-r1-distill-llama-70b", api_key=os.getenv("GROQ_API_KEY"))
dspy.configure(lm=lm)

# %%

model = dspy.ChainOfThought("question -> answer")

result = model(question="What is the capital of France?")


print(result)

# %%