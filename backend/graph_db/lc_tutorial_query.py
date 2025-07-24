# %%
from langchain_neo4j import Neo4jGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from typing import List
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from IPython.display import Image, display
from langgraph.graph import END, START, StateGraph
from neo4j.exceptions import CypherSyntaxError
from typing import Optional


load_dotenv()

graph = Neo4jGraph()
llm = ChatGoogleGenerativeAI(temperature=0, model="gemini-2.0-flash")


# --- State Types ---
class InputState(TypedDict):
    question: str


class OverallState(TypedDict):
    question: str
    cypher_statement: str
    cypher_errors: List[str]
    database_records: List[dict]
    steps: List[str]


class OutputState(TypedDict):
    answer: str
    steps: List[str]
    cypher_statement: str


# --- Prompt for Cypher Generation ---
text2cypher_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "Given an input neuroscience question, convert it to a Cypher query. No pre-amble. "
                "Do not wrap the response in any backticks or anything else. Respond with a Cypher statement only!"
            ),
        ),
        (
            "human",
            (
                """You are a Neo4j expert. Given an input neuroscience question, create a syntactically correct Cypher query to run.\n"""
                "Here is the schema information\n{schema}\n\nUser input: {question}\nCypher query:"
            ),
        ),
    ]
)

text2cypher_chain = text2cypher_prompt | llm | (lambda x: x)


def generate_cypher(state: OverallState) -> OverallState:
    """
    Generates a cypher statement based on the provided schema and user input
    """
    generated_cypher = text2cypher_chain.invoke(
        {
            "question": state.get("question"),
            "schema": graph.schema,
        }
    )
    return {"cypher_statement": generated_cypher, "steps": ["generate_cypher"]}


validate_cypher_system = """
You are a Cypher expert reviewing a statement written by a junior developer.
"""

validate_cypher_user = """You must check the following:
* Are there any syntax errors in the Cypher statement?
* Are there any missing or undefined variables in the Cypher statement?
* Are any node labels missing from the schema?
* Are any relationship types missing from the schema?
* Are any of the properties not included in the schema?
* Does the Cypher statement include enough information to answer the question?

Schema:
{schema}

The question is:
{question}

The Cypher statement is:
{cypher}
"""

validate_cypher_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", validate_cypher_system),
        ("human", (validate_cypher_user)),
    ]
)


class ValidateCypherOutput(BaseModel):
    errors: Optional[List[str]] = Field(
        description="A list of syntax or semantical errors in the Cypher statement."
    )


validate_cypher_chain = validate_cypher_prompt | llm.with_structured_output(
    ValidateCypherOutput
)


def validate_cypher(state: OverallState) -> OverallState:
    errors = []
    try:
        graph.query(f"EXPLAIN {state.get('cypher_statement')}")
    except CypherSyntaxError as e:
        errors.append(e.message)
    llm_output = validate_cypher_chain.invoke(
        {
            "question": state.get("question"),
            "schema": graph.schema,
            "cypher": state.get("cypher_statement"),
        }
    )
    if llm_output.errors:
        errors.extend(llm_output.errors)
    next_action = "correct_cypher" if errors else "execute_cypher"
    return {
        "cypher_errors": errors,
        "cypher_statement": state.get("cypher_statement"),
        "steps": ["validate_cypher"],
        "question": state.get("question"),
        "database_records": [],
        "next_action": next_action,
    }


correct_cypher_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a Cypher expert reviewing a statement written by a junior developer. "
                "You need to correct the Cypher statement based on the provided errors. No pre-amble. "
                "Do not wrap the response in any backticks or anything else. Respond with a Cypher statement only!"
            ),
        ),
        (
            "human",
            (
                """Check for invalid syntax or semantics and return a corrected Cypher statement.\n\nSchema:\n{schema}\n\nThe question is:\n{question}\n\nThe Cypher statement is:\n{cypher}\n\nThe errors are:\n{errors}\n\nCorrected Cypher statement: """
            ),
        ),
    ]
)

correct_cypher_chain = correct_cypher_prompt | llm | (lambda x: x)


def correct_cypher(state: OverallState) -> OverallState:
    corrected_cypher = correct_cypher_chain.invoke(
        {
            "question": state.get("question"),
            "errors": state.get("cypher_errors"),
            "cypher": state.get("cypher_statement"),
            "schema": graph.schema,
        }
    )
    return {
        "cypher_statement": corrected_cypher,
        "steps": ["correct_cypher"],
        "question": state.get("question"),
        "cypher_errors": [],
        "database_records": [],
        "next_action": "validate_cypher",
    }


no_results = "I couldn't find any relevant information in the database"


def execute_cypher(state: OverallState) -> OverallState:
    records = graph.query(state.get("cypher_statement"))
    return {
        "database_records": records if records else no_results,
        "steps": ["execute_cypher"],
        "question": state.get("question"),
        "cypher_statement": state.get("cypher_statement"),
        "cypher_errors": [],
        "next_action": "end",
    }


generate_final_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant"),
        (
            "human",
            (
                """Use the following results retrieved from a database to provide\na succinct, definitive answer to the user's neuroscience question.\n\nResults: {results}\nQuestion: {question}"""
            ),
        ),
    ]
)

generate_final_chain = generate_final_prompt | llm | (lambda x: x)


def generate_final_answer(state: OverallState) -> OutputState:
    final_answer = generate_final_chain.invoke(
        {"question": state.get("question"), "results": state.get("database_records")}
    )
    return {
        "answer": final_answer,
        "steps": ["generate_final_answer"],
        "cypher_statement": state.get("cypher_statement"),
    }


def validate_cypher_condition(state: OverallState) -> str:
    next_action = state.get("next_action")
    if next_action == "end":
        return "generate_final_answer"
    elif next_action == "correct_cypher":
        return "correct_cypher"
    elif next_action == "execute_cypher":
        return "execute_cypher"
    else:
        raise ValueError(f"Unknown next_action: {next_action}. State: {state}")


langgraph = StateGraph(OverallState, input=InputState, output=OutputState)
langgraph.add_node(generate_cypher)
langgraph.add_node(validate_cypher)
langgraph.add_node(correct_cypher)
langgraph.add_node(execute_cypher)
langgraph.add_node(generate_final_answer)

langgraph.add_edge(START, "generate_cypher")
langgraph.add_edge("generate_cypher", "validate_cypher")
langgraph.add_conditional_edges(
    "validate_cypher",
    validate_cypher_condition,
)
langgraph.add_edge("execute_cypher", "generate_final_answer")
langgraph.add_edge("correct_cypher", "validate_cypher")
langgraph.add_edge("generate_final_answer", END)

langgraph = langgraph.compile()

display(Image(langgraph.get_graph().draw_mermaid_png()))

# Example usage:
result = langgraph.invoke({"question": "What does Primary sensory cell do?"})
print(result)
