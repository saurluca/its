# %%
import dspy
from dotenv import load_dotenv
import os
from pprint import pprint

load_dotenv()

lm = dspy.LM(
    "azure/gpt-4o",
    api_base="https://spg-piatutor.openai.azure.com/",
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version="2024-12-01-preview",
)
dspy.configure(lm=lm)


# %%

# read in document from file:
# data_file = "../data/anonymity2.html"
data_file = "../data/ethics.html"


with open(data_file, "r") as f:
    document = f.read()


# summarises a document and extracts the key points and purpose
class DocumentSummary(dspy.Signature):
    """You are summarizing a document.

    Your task is to summarize the document and extract its main points.
    Ignore organizational information like time of class, contact information, etc.

    MUST: Always respond with a summary.
    """

    document: str = dspy.InputField(description="The document to summarize.")

    summary: str = dspy.OutputField(description="The summary of the document.")


document_summary = dspy.ChainOfThought(DocumentSummary)


# %%

summary = document_summary(document=document)

print("-" * 100)
pprint(summary.summary)


# %%
