# %%
from langchain_community.graphs import Neo4jGraph

# from langchain_google_genai import ChatGoogleGenerativeAI  # Gemini LLM (commented out)
from langchain_openai import ChatOpenAI  # OpenAI LLM
from langchain.chains import GraphCypherQAChain
from dotenv import load_dotenv
import os

load_dotenv()

# Store Knowledge Graph in Neo4j
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_URL = os.getenv("NEO4J_URL")

# Connect to Neo4j using LangChain's Neo4jGraph
neo4j_graph = Neo4jGraph(
    url=NEO4J_URL, username=NEO4J_USERNAME, password=NEO4J_PASSWORD
)

llm = ChatOpenAI(temperature=0, model="gpt-4.1-nano")  # OpenAI GPT-4.1-nano
# llm = ChatGoogleGenerativeAI(temperature=0, model="gemini-2.0-flash")

# Create a GraphCypherQAChain for natural language to Cypher conversion
cypher_chain = GraphCypherQAChain.from_llm(
    llm=llm,
    graph=neo4j_graph,
    verbose=True,
    return_intermediate_steps=True,
    allow_dangerous_requests=True,
)


def query_and_synthesize(query):
    """
    Takes a natural language query, converts it to Cypher using LLM,
    executes the query against Neo4j, and synthesizes a response.
    """
    try:
        result = cypher_chain.invoke({"query": query})

        print(f"Query: {query}")
        print(
            f"Generated Cypher: {result.get('intermediate_steps', [{}])[0].get('query', 'N/A')}"
        )
        print(f"Answer: {result['result']}\n")

        return result
    except Exception as e:
        print(f"Error processing query '{query}': {str(e)}\n")
        return None


# Example queries
print("=== Natural Language Queries to Knowledge Graph ===\n")


# Additional example queries you can try:
query_and_synthesize("What do Sensory cells do?")
# query_and_synthesize("Show me all relationships in the database")
# query_and_synthesize("What companies are mentioned in the database?")
