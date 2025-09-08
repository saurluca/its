from .models import Chunk
import dspy


# summarises a document
class DocumentSummary(dspy.Signature):
    """You are summarizing a document.

    Your task is to summarize the document and extract its main points.
    Ignore organizational information like time of class, contact information, etc.

    MUST: Always respond with a summary.
    """

    document: str = dspy.InputField(description="The document to summarize.")

    summary: str = dspy.OutputField(description="The summary of the document.")


class ChunkImportance(dspy.Signature):
    """
    Your task is to determine if a single chunk is important or not.
    Based on the summary of the document, you should determine if this chunk is relevant.
    You should return whether the chunk is important or not.

    Especially ignore chunks related to organisational information, like homework assignments, lecture dates, etc.
    """

    chunk_text: str = dspy.InputField(
        description="The text content of the chunk to evaluate."
    )

    summary_of_document: str = dspy.InputField(
        description="The summary of the document."
    )

    is_important: bool = dspy.OutputField(
        description="Whether this chunk is important (True) or unimportant (False)."
    )


class DocumentTitle(dspy.Signature):
    """
    Generate a title for the document based on the summary.
    """

    summary: str = dspy.InputField(description="The summary of the document.")
    document_title: str = dspy.OutputField(
        description=f"A short title for the document based on the summary. The document is part of a lecture course. Max title length: {MAX_TITLE_LENGTH} characters."
    )


def generate_document_title(summary: str, lm: dspy.LM) -> str:
    try:
        model = dspy.ChainOfThought(DocumentTitle)
        result = model(summary=summary, lm=lm)
        return result.document_title
    except Exception as e:
        print(f"Error generating document title: {e}")
        return "Untitled Document"


def get_document_summary(document_content: str, lm: dspy.LM):
    """
    Generate a summary of the document.

    Args:
        document_content: The full text content of the document

    Returns:
        DocumentSummary result with summary
    """
    document_summary_model = dspy.ChainOfThought(DocumentSummary)

    return document_summary_model(document=document_content, lm=lm)


def filter_important_chunks(
    chunks: list[Chunk], document_summary: DocumentSummary, lm: dspy.LM
):
    """
    Filter chunks by evaluating each chunk individually for importance.

    Args:
        chunks: List of chunks to evaluate
        document_summary: The document summary result containing summary

    Returns:
        Dictionary with filtering results and statistics
    """
    unimportant_chunks_ids = []
    chunk_evaluations = []
    chunk_importance_model = dspy.Predict(ChunkImportance)

    for chunk in chunks:
        # Evaluate each chunk individually
        evaluation = chunk_importance_model(
            chunk_text=chunk.chunk_text,
            summary_of_document=document_summary.summary,
            lm=lm,
        )

        chunk_evaluations.append(
            {
                "chunk_id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "is_important": evaluation.is_important,
            }
        )

        if not evaluation.is_important:
            unimportant_chunks_ids.append(chunk.chunk_index)

    num_of_unimportant_chunks = len(unimportant_chunks_ids)
    num_of_all_chunks = len(chunks)

    return {
        "unimportant_chunks_ids": unimportant_chunks_ids,
        "summary": document_summary.summary,
        "all_chunk_ids": [chunk.id for chunk in chunks],
        "num_of_unimportant_chunks": num_of_unimportant_chunks,
        "num_of_all_chunks": num_of_all_chunks,
        "percentage_of_unimportant_chunks": (
            num_of_unimportant_chunks / num_of_all_chunks
        )
        * 100
        if num_of_all_chunks > 0
        else 0,
        "chunk_evaluations": chunk_evaluations,
    }
