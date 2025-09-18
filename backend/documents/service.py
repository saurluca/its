from .models import Chunk, Document
import dspy
from constants import MAX_TITLE_LENGTH
import os
import httpx
from uuid import UUID
from sqlmodel import Session
from starlette.concurrency import run_in_threadpool
from dependencies import get_database_engine, get_large_llm, get_small_llm
from sqlmodel import select as sql_select


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


async def process_document_upload(
    document_id: UUID,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    flatten_pdf: bool,
):
    """Background task to process an uploaded document.

    - Calls Docling service
    - Stores content and chunks
    - Generates summary and title
    - Marks important chunks
    """
    print(f"[bg] Start processing document {filename} ({document_id})...")
    print(f"Flatten pdf status: {flatten_pdf}")
    DOCLING_SERVE_API_URL = os.getenv("DOCLING_SERVE_API_URL")
    if not DOCLING_SERVE_API_URL:
        print("[bg] DOCLING_SERVE_API_URL not configured; aborting document processing")
        return

    engine = get_database_engine()
    with Session(engine) as session:
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                resp = await client.post(
                    f"{DOCLING_SERVE_API_URL}/process",
                    files={
                        "file": (
                            filename,
                            file_bytes,
                            content_type,
                        )
                    },
                    params={
                        "filename": filename,
                        "flatten_pdf": str(bool(flatten_pdf)).lower(),
                    },
                )

            if resp.status_code != 200:
                print(
                    f"[bg] Docling processing failed for {document_id}: {resp.status_code} {resp.text}"
                )
                return

            results = resp.json()
            chunks_data = results.get("chunks", [])
            html_text = results.get("html_text", "")

            db_document = session.get(Document, document_id)
            if not db_document:
                print(f"[bg] Document {document_id} not found in DB")
                return

            # Update content
            db_document.content = html_text
            session.add(db_document)
            session.commit()
            session.refresh(db_document)

            # Persist chunks
            for chunk in chunks_data:
                db_chunk = Chunk(**chunk)
                db_chunk.document_id = document_id
                session.add(db_chunk)
            session.commit()

            # Summarize and title generation
            print(f"[bg] Summarising document {document_id}...")
            large_lm = get_large_llm()
            small_lm = get_small_llm()
            summary_result = await run_in_threadpool(
                get_document_summary, html_text, large_lm
            )
            db_document.summary = summary_result.summary

            print(f"[bg] Generating title for document {document_id}...")
            db_document.title = await run_in_threadpool(
                generate_document_title, summary_result.summary, small_lm
            )
            session.add(db_document)
            session.commit()
            session.refresh(db_document)

            # Filter important chunks
            print(f"[bg] Filtering important chunks for document {document_id}...")

            chunks = session.exec(
                sql_select(Chunk).where(Chunk.document_id == document_id)
            ).all()
            result = await run_in_threadpool(
                filter_important_chunks, chunks, summary_result, small_lm
            )
            for chunk in chunks:
                chunk.important = (
                    chunk.chunk_index not in result["unimportant_chunks_ids"]
                )
                session.add(chunk)
            session.commit()

            print(
                f"[bg] Finished processing document {document_id}. Marked {len(result['unimportant_chunks_ids'])} chunks as unimportant"
            )
        except Exception as e:
            session.rollback()
            print(f"[bg] Error processing document {document_id}: {e}")
