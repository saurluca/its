from .models import Chunk, Document
import dspy
from constants import MAX_TITLE_LENGTH
import os
import asyncio
import httpx
from uuid import UUID
from sqlmodel import Session, select
from starlette.concurrency import run_in_threadpool
from dependencies import get_database_engine, get_large_llm, get_small_llm
from .events import document_events_manager
from sqlalchemy import update
import logging
import random

# Set up logging
logger = logging.getLogger(__name__)

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
DOCLING_SERVE_API_URL = os.getenv("DOCLING_SERVE_API_URL")
shared_client = httpx.AsyncClient(timeout=DOCLING_TIMEOUT, limits=DOCLING_LIMITS)

async def call_docling_with_retry(
    url: str,
    file_data: tuple,
    params: dict,
    max_retries: int = 3,
) -> httpx.Response:
    """Call Docling service with exponential backoff retry."""
    last_exception = None
    
    for attempt in range(max_retries):
        async with httpx.AsyncClient(timeout=DOCLING_TIMEOUT, limits=DOCLING_LIMITS) as client:
            try:
                logger.info(f"[bg] Calling Docling service at {url} (attempt {attempt + 1}/{max_retries})")
                response = await client.post(url, files={"file": file_data}, params=params)
                response.raise_for_status()
                return response
            except (
                httpx.TimeoutException, 
                httpx.ConnectError, 
                httpx.ReadError, 
                httpx.HTTPStatusError,
                httpx.RemoteProtocolError,
            ) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = min(4 * (2 ** attempt), 60)
                    jittered_wait = wait_time + random.uniform(0, 1)
                    logger.warning(f"[bg] Retry after {jittered_wait:.2f}s due to: {type(e).__name__}: {e}")
                    await asyncio.sleep(jittered_wait)
                else:
                    logger.error(f"[bg] All retry attempts failed with {type(e).__name__}")
    
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
        logger.error(f"Error generating document title: {e}")
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
    
    # OPTIMIZATION: Increase concurrency for faster processing
    # Adjust based on your API rate limits
    semaphore = asyncio.Semaphore(20)  # Increased from 10
    
    async def evaluate_chunk(chunk):
        async with semaphore:
            try:
                evaluation = await run_in_threadpool(
                    chunk_importance_model,
                    chunk_text=chunk.chunk_text,
                    summary_of_document=document_summary.summary,
                    lm=lm
                )
                return chunk, evaluation, None
            except Exception as e:
                logger.error(f"Error evaluating chunk {chunk.id}: {e}")
                # Default to important if evaluation fails
                return chunk, None, e

    # Evaluate all chunks concurrently
    logger.info(f"[bg] Evaluating {len(chunks)} chunks with concurrency={semaphore._value}")
    results = await asyncio.gather(*[evaluate_chunk(chunk) for chunk in chunks])
    
    for chunk, evaluation, error in results:
        if error:
            # Default to important on error
            chunk_evaluations.append({
                "chunk_id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "is_important": True,
                "error": str(error)
            })
        else:
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
    logger.info(f"[bg] ----- START PROCESSING DOCUMENT -----")
    logger.info(f"[bg] Document ID: {document_id}")
    logger.info(f"[bg] Filename: {filename}")
    logger.info(f"[bg] Content Type: {content_type}")
    logger.info(f"[bg] Flatten PDF: {flatten_pdf}")
    logger.info(f"[bg] File size: {len(file_bytes)} bytes")
    logger.info(f"[bg] -------------------------------------")

    await document_events_manager.broadcast_status(
        document_id,
        status="processing",
        message="Starting document processing",
        payload={"step": "start"},
    )

    
    if not DOCLING_SERVE_API_URL:
        logger.warning("[bg] DOCLING_SERVE_API_URL not configured")
        await document_events_manager.broadcast_status(
            document_id,
            status="error",
            message="Document processing service is not configured.",
            payload={"step": "configuration"},
        )
        return

    logger.info(f"[bg] DOCLING_SERVE_API_URL: {DOCLING_SERVE_API_URL}")

    engine = get_database_engine()

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
            logger.info(f"[bg] Calling Docling service at {DOCLING_SERVE_API_URL}/process")
            resp = await call_docling_with_retry(
                f"{DOCLING_SERVE_API_URL}/process",
                (filename, file_bytes, content_type),
                {
                    "filename": filename,
                    "flatten_pdf": str(bool(flatten_pdf)).lower(),
                },
            )
            logger.info(f"[bg] Docling response status: {resp.status_code}")
        finally:
            # Stop heartbeat
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

        if resp.status_code != 200:
            logger.error(f"[bg] Docling failed for {document_id}: {resp.status_code}")
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
        
        logger.info(f"[bg] Docling completed, persisting {len(chunks_data)} chunks...")

        #Use a single session context and minimize DB round-trips
        with Session(engine) as session:
            db_document = session.get(Document, document_id)
            if not db_document:
                logger.error(f"[bg] Document {document_id} not found in DB")
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

            # Bulk insert without return_defaults, then fetch IDs separately
            await document_events_manager.broadcast_status(
                document_id,
                status="processing",
                message="Storing document sections",
                payload={"step": "persist_chunks"},
            )
            
            # Create chunk objects
            chunk_objects = [
                Chunk(**chunk, document_id=document_id) 
                for chunk in chunks_data
            ]
            
            # Bulk insert
            session.bulk_save_objects(chunk_objects)
            session.commit()
            
            # Fetch the inserted chunks with their IDs
            chunks_from_db = session.exec(
                select(Chunk)
                .where(Chunk.document_id == document_id)
                .order_by(Chunk.chunk_index)
            ).all()

        logger.info(f"[bg] Persisted {len(chunks_from_db)} chunks to database")

        # Schedule summarization as background task
        # Pass the chunks with IDs from database
        logger.info(f"[bg] Scheduling summarization task for document {document_id}")
        asyncio.create_task(
            summarise_and_filter_document(document_id, html_text, list(chunks_from_db))
        )

        # Changed status from "processed" to "processing" with updated message
        await document_events_manager.broadcast_status(
            document_id,
            status="processing",  # Changed from "processed"
            message="Text extraction complete. Generating summary and analyzing content...",
            payload={"step": "starting_summarization"},
        )

    except httpx.TimeoutException as e:
        logger.error(f"[bg] Timeout processing document {document_id}: {e}")
        await document_events_manager.broadcast_status(
            document_id,
            status="error",
            message="Document processing timed out. The file may be too large or complex.",
            payload={"step": "timeout", "detail": str(e)},
        )

    except (httpx.ConnectError, httpx.ReadError) as e:
        logger.error(f"[bg] Connection error processing document {document_id}: {e}")
        await document_events_manager.broadcast_status(
            document_id,
            status="error",
            message="Failed to connect to document processing service.",
            payload={"step": "connection_error", "detail": str(e)},
        )

    except Exception as e:
        logger.exception(f"[bg] Error processing document {document_id}: {e}")
        await document_events_manager.broadcast_status(
            document_id,
            status="error",
            message="An unexpected error occurred while processing the document.",
            payload={"step": "exception", "detail": str(e)},
        )

# Parallelize summary and title generation
async def summarise_and_filter_document(document_id: UUID, html_text: str, chunk_objects: list[Chunk]):
    """Background task to summarize document and filter important chunks."""
    logger.info(f"[bg] ----- Starting Summarization, Filtering -----")
    logger.info(f"[bg] Document ID: {document_id}")
    logger.info(f"[bg] Number of chunks: {len(chunk_objects)}")
    logger.info(f"[bg] HTML text length: {len(html_text)}")
    logger.info(f"[bg] ----------------------------------------------")
    
    engine = get_database_engine()
    
    try:
        large_lm = get_large_llm()
        small_lm = get_small_llm()
        
        # OPTIMIZATION: Run summary and title generation in parallel
        logger.info(f"[bg] Generating summary and title for document {document_id}...")
        await document_events_manager.broadcast_status(
            document_id,
            status="processing",
            message="Generating summary and title",
            payload={"step": "summarise_and_title"},
        )
        
        # Run both in parallel
        summary_result, title = await asyncio.gather(
            run_in_threadpool(get_document_summary, html_text, large_lm),
            run_in_threadpool(
                lambda: generate_document_title(
                    # We'll update this after summary completes
                    html_text[:500],  # Use first 500 chars as fallback
                    small_lm
                )
            )
        )
        
        logger.info(f"[bg] Generated summary: {summary_result.summary[:50]}...")
        logger.info(f"[bg] Generated title: {title}")
        
        # If title generation needs the summary, regenerate it
        # Otherwise, keep the parallel version
        if not title or title == "Untitled Document":
            title = await run_in_threadpool(
                generate_document_title, 
                summary_result.summary, 
                small_lm
            )
            logger.warning(f"[bg] Regenerated title: {title}")
        
        # Filter important chunks
        logger.info(f"[bg] Filtering important chunks for document {document_id}...")
        await document_events_manager.broadcast_status(
            document_id,
            status="processing",
            message="Prioritising key sections",
            payload={"step": "filter_chunks"},
        )
        result = await filter_important_chunks_async(
            chunk_objects, 
            summary_result, 
            small_lm
        )
        
        # OPTIMIZATION: Single DB transaction for all updates
        with Session(engine) as session:
            db_document = session.get(Document, document_id)
            if not db_document:
                logger.error(f"[bg] Document {document_id} not found")
                return
                
            db_document.summary = summary_result.summary
            db_document.title = title
            
            # Update chunk importance
            unimportant_set = set(result["unimportant_chunks_ids"])
            chunk_ids_to_update = [
                chunk.id for chunk in chunk_objects 
                if chunk.chunk_index in unimportant_set
            ]
            
            logger.info(f"[bg] Marking {len(chunk_ids_to_update)} chunks as unimportant")
            
            # Bulk update chunks that are unimportant
            if chunk_ids_to_update:
                session.exec(
                    update(Chunk)
                    .where(Chunk.id.in_(chunk_ids_to_update))
                    .values(important=False)
                )
            
            session.add(db_document)
            session.commit()
            
            logger.info(f"[bg] Updated document with summary and title")

        logger.info(f"[bg] Finished processing document {document_id}")
        await document_events_manager.broadcast_status(
            document_id,
            status="processed",  # Changed from "completed" to "processed" to indicate fully processed
            message="Document fully processed and ready for task generation",
            payload={"step": "fully_complete"},
        )
        
    except Exception as e:
        logger.exception(f"[bg] Error in background processing for document {document_id}: {e}")
        await document_events_manager.broadcast_status(
            document_id,
            status="error",
            message="Error during background processing",
            payload={"step": "background_error", "detail": str(e)},
        )