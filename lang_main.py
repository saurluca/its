# %%
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI
import os

load_dotenv()

os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "password"

graph = Neo4jGraph(refresh_schema=False)


text_path = "data/documents/neuroscience_mini.txt"

llm = ChatGoogleGenerativeAI(temperature=0, model="gemini-2.0-flash")

llm_transformer = LLMGraphTransformer(llm=llm, node_properties=True)

def read_text_from_file(text_path):
    with open(text_path, "r") as file:
        return file.read()

text = read_text_from_file(text_path)

# text = text[:1000]
print(f"Length of text: {len(text)}")


# %% 
documents = [Document(page_content=text)]
graph_documents = llm_transformer.convert_to_graph_documents(documents)
print(f"Nodes:{graph_documents[0].nodes}")
print(f"Relationships:{graph_documents[0].relationships}")

# %%

graph.add_graph_documents(graph_documents, baseEntityLabel=True)