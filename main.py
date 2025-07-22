from PyPDF2 import PdfReader
from dotenv import load_dotenv
from kg_gen import KGGen
import os
from neo4j import GraphDatabase

load_dotenv()


def extract_text_from_pdf(pdf_path):
    with open(pdf_path, "rb") as file:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text


def save_text_to_file(text, text_path):
    with open(text_path, "w") as file:
        file.write(text)


def read_text_from_file(text_path):
    with open(text_path, "r") as file:
        return file.read()


def save_graph_to_neo4j(
    graph, uri="bolt://localhost:7687", user="neo4j", password="password"
):
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        # Create nodes
        for entity in graph.entities:
            session.run("MERGE (n:Entity {name: $name})", name=entity)
        # Create relationships
        for subj, pred, obj in graph.relations:
            session.run(
                """
                MATCH (a:Entity {name: $subj}), (b:Entity {name: $obj})
                MERGE (a)-[r:RELATION {type: $pred}]->(b)
                """,
                subj=subj,
                obj=obj,
                pred=pred,
            )
        # Save clusters if present
        if getattr(graph, "entity_clusters", None):
            for cluster_id, entities in graph.entity_clusters.items():
                # Create a Cluster node
                session.run(
                    "MERGE (c:Cluster {id: $cluster_id})", cluster_id=cluster_id
                )
                # Link entities to their cluster
                for entity in entities:
                    session.run(
                        """
                        MATCH (e:Entity {name: $entity}), (c:Cluster {id: $cluster_id})
                        MERGE (e)-[:IN_CLUSTER]->(c)
                        """,
                        entity=entity,
                        cluster_id=cluster_id,
                    )
    driver.close()


def main():
    print("Starting...")
    pdf_path = "data/documents/neuroscience.pdf"
    text_path = "data/documents/neuroscience.txt"

    # text = extract_text_from_pdf(pdf_path)
    # save_text_to_file(text, text_path)

    text_input = read_text_from_file(text_path)
    # text_input = text_input[:10000]
    print(f"Length of text: {len(text_input)}")

    kg = KGGen(
        model="gemini/gemini-2.5-flash",
        # model="openai/gpt-4.1",
        temperature=0.0,
        # api_key=os.getenv("OPENAI_API_KEY"),
        api_key=os.getenv("GOOGLE_API_KEY"),
    )

    print("Generating graph 1...")
    graph_1 = kg.generate(
        input_data=text_input,
        context="Lecture for introduction to a neuroscience university course.",
        chunk_size=5000,
        # cluster=True,
    )

    print("Saving graph to Neo4j...")
    save_graph_to_neo4j(graph_1)


if __name__ == "__main__":
    main()
