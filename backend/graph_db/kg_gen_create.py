from dotenv import load_dotenv
from kg_gen import KGGen
import os
from neo4j import GraphDatabase
from kg_gen.models import Graph

load_dotenv()


def read_text_from_file(text_path):
    with open(text_path, "r") as file:
        return file.read()


def extract_graph_from_text(kg, text, context="", block_size=6000, cluster=False):
    print(
        f"Splitting text into blocks {len(text) // block_size} of {block_size} characters"
    )
    for i in range(0, len(text), block_size):
        print(f"Processing block {i // block_size + 1} of {len(text) // block_size}")
        block = text[i : i + block_size]
        graph = kg.generate(
            input_data=block,
            context=context,
            chunk_size=block_size,
            cluster=cluster,
        )
        print(f"Saving graph {i // block_size + 1} of {len(text) // block_size}")
        save_graph_to_neo4j(graph)


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


def read_and_cluster_graph_from_neo4j(
    kg,
    context="Optional context for clustering",
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password",
):
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        # Get all entities
        entity_result = session.run("MATCH (n:Entity) RETURN n.name AS name")
        entities = set(record["name"] for record in entity_result)

        # Get all relations (subject, predicate, object)
        relation_result = session.run(
            """
            MATCH (a:Entity)-[r:RELATION]->(b:Entity)
            RETURN a.name AS subj, r.type AS pred, b.name AS obj
            """
        )
        relations = set(
            (record["subj"], record["pred"], record["obj"])
            for record in relation_result
        )

    driver.close()

    print("Starting to build graph...")
    # Build the Graph object
    combined_graph = Graph(
        entities=entities, relations=relations, edges={r[1] for r in relations}
    )

    print("Starting to cluster graph...")
    # Cluster the graph using KGGen
    clustered_graph = kg.cluster(combined_graph, context=context)
    return clustered_graph


def main():
    text_path = "data/documents/neuroscience.txt"

    text_input = read_text_from_file(text_path)
    print(f"Length of text: {len(text_input)}")

    kg = KGGen(
        model="gemini/gemini-2.5-flash",
        # model="openai/gpt-4.1",
        temperature=0.0,
        # api_key=os.getenv("OPENAI_API_KEY"),
        api_key=os.getenv("GOOGLE_API_KEY"),
    )

    print("Generating and saving initial graph...")
    # extract_graph_from_text(
    #     kg,
    #     text_input,
    #     context="Lecture for introduction to a neuroscience university course.",
    #     block_size=6000,
    #     cluster=False,
    # )

    print("Reading graph from Neo4j and clustering...")
    clustered_graph = read_and_cluster_graph_from_neo4j(
        kg, context="Lecture for introduction to a neuroscience university course."
    )

    print("Saving clustered graph back to Neo4j...")
    save_graph_to_neo4j(clustered_graph)


if __name__ == "__main__":
    main()
