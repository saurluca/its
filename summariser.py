import dspy
from db_utils import save_key_points_to_db, get_document_content_from_db


def summarise_document(doc_id):
    document = get_document_content_from_db(doc_id)

    summarizer = dspy.ChainOfThought("document -> key_points")

    response = summarizer(document=document)

    save_key_points_to_db(doc_id, response.key_points)

    return response.key_points
