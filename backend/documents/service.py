from .models import Chunk, Document
import dspy
from constants import MAX_TITLE_LENGTH
import os
import asyncio
import httpx
from uuid import UUID
from sqlmodel import Session
from starlette.concurrency import run_in_threadpool
from dependencies import get_database_engine, get_large_llm, get_small_llm
from sqlmodel import select as sql_select
from .events import document_events_manager

# Configure httpx timeout
DOCLING_TIMEOUT = httpx.Timeout(
    connect=10.0,
    read=600.0,  # 10 minutes for large documents
    write=30.0,
    pool=10.0,
)

DOCLING_LIMITS = httpx.Limits(
    max_keepalive_connections=5,
    max_connections=10,
    keepalive_expiry=30.0,
)


async def call_docling_with_retry(
    client: httpx.AsyncClient,
    url: str,
    file_data: tuple,
    params: dict,
    max_retries: int = 3,
) -> httpx.Response:
    """Call Docling service with exponential backoff retry."""
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            print(f"[bg] Calling Docling service at {url} (attempt {attempt + 1}/{max_retries})")
            return await client.post(url, files={"file": file_data}, params=params)
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = min(4 * (2 ** attempt), 60)
                print(f"[bg] Retry after {wait_time}s due to: {e}")
                await asyncio.sleep(wait_time)
            else:
                print(f"[bg] All retry attempts failed")
    
    raise last_exception


async def send_progress_heartbeat(document_id: UUID, max_duration: int = 600):
    """Send periodic status updates during long-running processing."""
    elapsed = 0
    interval = 30  # Send update every 30 seconds

    while elapsed < max_duration:
        await asyncio.sleep(interval)
        elapsed += interval
        await document_events_manager.broadcast_status(
            document_id,
            status="processing",
            message=f"Processing document... ({elapsed}s elapsed)",
            payload={"step": "docling", "elapsed_seconds": elapsed},
        )


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


async def filter_important_chunks_async(
    chunks: list[Chunk], document_summary: DocumentSummary, lm: dspy.LM
):
    """Async version to evaluate chunks in parallel with controlled concurrency."""
    unimportant_chunks_ids = []
    chunk_evaluations = []
    chunk_importance_model = dspy.Predict(ChunkImportance)
    
    # Limit concurrency to avoid thread pool exhaustion
    semaphore = asyncio.Semaphore(10)
    
    async def evaluate_chunk(chunk):
        async with semaphore:
            evaluation = await run_in_threadpool(
                chunk_importance_model,
                chunk_text=chunk.chunk_text,
                summary_of_document=document_summary.summary,
                lm=lm
            )
            return chunk, evaluation

    # Evaluate all chunks concurrently
    results = await asyncio.gather(*[evaluate_chunk(chunk) for chunk in chunks])
    
    for chunk, evaluation in results:
        chunk_evaluations.append({
            "chunk_id": chunk.id,
            "chunk_index": chunk.chunk_index,
            "is_important": evaluation.is_important,
        })
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
    """Background task to process an uploaded document."""
    print(f"[bg] Start processing document {filename} ({document_id})...")
    print(f"Flatten pdf status: {flatten_pdf}")

    await document_events_manager.broadcast_status(
        document_id,
        status="processing",
        message="Starting document processing",
        payload={"step": "start"},
    )

    DOCLING_SERVE_API_URL = os.getenv("DOCLING_SERVE_API_URL")
    if not DOCLING_SERVE_API_URL:
        print("[bg] DOCLING_SERVE_API_URL not configured")
        await document_events_manager.broadcast_status(
            document_id,
            status="error",
            message="Document processing service is not configured.",
            payload={"step": "configuration"},
        )
        return

    engine = get_database_engine()

    with Session(engine) as session:
        try:
            await document_events_manager.broadcast_status(
                document_id,
                status="processing",
                message="Sending document to text extraction service",
                payload={"step": "docling"},
            )

            # Create heartbeat task for progress updates
            heartbeat_task = asyncio.create_task(
                send_progress_heartbeat(document_id, max_duration=600)
            )

            try:
                async with httpx.AsyncClient(
                    timeout=DOCLING_TIMEOUT,
                    limits=DOCLING_LIMITS,
                ) as client:
                    # Call with retry logic
                    resp = await call_docling_with_retry(
                        client,
                        f"{DOCLING_SERVE_API_URL}/process",
                        (filename, file_bytes, content_type),
                        {
                            "filename": filename,
                            "flatten_pdf": str(bool(flatten_pdf)).lower(),
                        },
                    )
            finally:
                # Stop heartbeat
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

            if resp.status_code != 200:
                print(f"[bg] Docling failed for {document_id}: {resp.status_code}")
                await document_events_manager.broadcast_status(
                    document_id,
                    status="error",
                    message=f"Document processing failed (status {resp.status_code})",
                    payload={"step": "docling", "status_code": resp.status_code},
                )
                return

            results = resp.json()
            chunks_data = results.get("chunks", [])
            html_text = results.get("html_text", "")

            db_document = session.get(Document, document_id)
            if not db_document:
                print(f"[bg] Document {document_id} not found in DB")
                await document_events_manager.broadcast_status(
                    document_id,
                    status="error",
                    message="Document reference not found.",
                    payload={"step": "database"},
                )
                return

            # Store content
            await document_events_manager.broadcast_status(
                document_id,
                status="processing",
                message="Storing extracted content",
                payload={"step": "persist_content"},
            )
            db_document.content = html_text
            session.add(db_document)
            session.commit()
            session.refresh(db_document)

            # Persist chunks: Use bulk insert with return_defaults for getting IDs
            await document_events_manager.broadcast_status(
                document_id,
                status="processing",
                message="Storing document sections",
                payload={"step": "persist_chunks"},
            )
            
            # Create chunk objects with document_id
            chunk_objects = [
                Chunk(**chunk, document_id=document_id) 
                for chunk in chunks_data
            ]
            
            # Bulk insert with return_defaults to get IDs back
            session.bulk_save_objects(chunk_objects, return_defaults=True)
            session.commit()

            # Generate summary
            print(f"[bg] Summarising document {document_id}...")
            await document_events_manager.broadcast_status(
                document_id,
                status="processing",
                message="Generating summary",
                payload={"step": "summarise"},
            )
            large_lm = get_large_llm()
            small_lm = get_small_llm()
            summary_result = await run_in_threadpool(
                get_document_summary, html_text, large_lm
            )
            db_document.summary = summary_result.summary

            # Generate title
            print(f"[bg] Generating title for document {document_id}...")
            await document_events_manager.broadcast_status(
                document_id,
                status="processing",
                message="Generating document title",
                payload={"step": "title"},
            )
            db_document.title = await run_in_threadpool(
                generate_document_title, summary_result.summary, small_lm
            )
            session.add(db_document)
            session.commit()
            session.refresh(db_document)

            # Filter important chunks
            print(f"[bg] Filtering important chunks for document {document_id}...")
            await document_events_manager.broadcast_status(
                document_id,
                status="processing",
                message="Prioritising key sections",
                payload={"step": "filter_chunks"},
            )

            # Use chunk_objects directly, no re-querying
            result = await filter_important_chunks_async(chunk_objects, summary_result, small_lm)
            
            # Bulk update chunks
            unimportant_set = set(result["unimportant_chunks_ids"])
            for chunk in chunk_objects:
                chunk.important = chunk.chunk_index not in unimportant_set
            
            session.bulk_save_objects(chunk_objects)
            session.commit()

            print(f"[bg] Finished processing document {document_id}")
            await document_events_manager.broadcast_status(
                document_id,
                status="completed",
                message="Document processed successfully",
                payload={
                    "step": "completed",
                    "title": db_document.title,
                    "summary": db_document.summary,
                    "important_chunks": result["num_of_all_chunks"]
                    - result["num_of_unimportant_chunks"],
                },
            )

        except httpx.TimeoutException as e:
            session.rollback()
            print(f"[bg] Timeout processing document {document_id}: {e}")
            await document_events_manager.broadcast_status(
                document_id,
                status="error",
                message="Document processing timed out. The file may be too large or complex.",
                payload={"step": "timeout", "detail": str(e)},
            )

        except (httpx.ConnectError, httpx.ReadError) as e:
            session.rollback()
            print(f"[bg] Connection error processing document {document_id}: {e}")
            await document_events_manager.broadcast_status(
                document_id,
                status="error",
                message="Failed to connect to document processing service.",
                payload={"step": "connection_error", "detail": str(e)},
            )

        except Exception as e:
            session.rollback()
            print(f"[bg] Error processing document {document_id}: {e}")
            await document_events_manager.broadcast_status(
                document_id,
                status="error",
                message="An unexpected error occurred while processing the document.",
                payload={"step": "exception", "detail": str(e)},
            )