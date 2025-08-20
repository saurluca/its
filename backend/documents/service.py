from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import DocumentStream
from docling.datamodel.document import DoclingDocument as DLDocument
from docling.chunking import HybridChunker
from io import BytesIO
from constants import SUPPORTED_MIME_TYPES, MAX_TITLE_LENGTH, MIN_CHUNK_LENGTH
from exceptions import InvalidFileFormatError
from .models import Document as DBDocument, Chunk
import time
import dspy
import fitz
import io
from PIL import Image


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


# def flatten_pdf_stream(input_stream: BytesIO) -> BytesIO:
#     """Flattens a PDF from an input stream and returns an output stream."""
#     print("Flattening PDF")
#     start_time = time.time()
#     doc = fitz.open(stream=input_stream.read(), filetype="pdf")
#     output_stream = io.BytesIO()
#     doc.save(output_stream, garbage=4, deflate=True)
#     doc.close()
#     output_stream.seek(0)
#     print(f"Time taken to flatten: {(time.time() - start_time):.2f} seconds")
#     return output_stream


# TODO: this fixes the issues with some pdfs, but significantly increases the compute time, because docling needs to do full OCR on the images
def flatten_pdf_in_memory(pdf_bytes):
    """
    Rasters a PDF from a byte stream and returns a new flattened PDF as a byte stream.
    """
    print("Flattening PDF")
    start_time = time.time()
    input_pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
    output_pdf = fitz.open()

    for page_num in range(len(input_pdf)):
        page = input_pdf.load_page(page_num)
        pixmap = page.get_pixmap(dpi=300)  # Higher DPI for better quality

        # Convert the pixmap to a Pillow Image
        img = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)

        # Save the image as a new PDF page
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PDF", resolution=300)
        img_bytes.seek(0)

        output_pdf.insert_pdf(fitz.open(stream=img_bytes.read(), filetype="pdf"))

    # Save the final flattened PDF to a byte stream
    flattened_pdf_bytes = io.BytesIO(output_pdf.tobytes())
    input_pdf.close()
    output_pdf.close()

    print(f"Time taken to flatten: {(time.time() - start_time):.2f} seconds")
    return flattened_pdf_bytes


def extract_docling_doc(file_obj) -> tuple[str, DLDocument]:
    assert file_obj and hasattr(file_obj, "read"), (
        "Input must be a file-like object with .read()"
    )

    print("Converting doc using Docling")
    start_time = time.time()

    # Build a DocumentStream as per Docling usage
    name = getattr(file_obj, "name", None)
    if hasattr(file_obj, "filename") and file_obj.filename:
        name = file_obj.filename
    if not name:
        name = "uploaded_file.pdf"

    try:
        file_obj.seek(0)
        file_content = file_obj.read()
        stream_like = BytesIO(file_content)
        stream_like = flatten_pdf_in_memory(stream_like)
    except Exception as e:
        print(f"Error reading file: {e}")
        raise InvalidFileFormatError("Could not read file content")

    stream = DocumentStream(name=str(name), stream=stream_like)

    converter = DocumentConverter()
    result = converter.convert(stream)
    docling_doc = result.document

    if hasattr(docling_doc, "tables"):
        print(f"Document has {len(docling_doc.tables)} tables")
    else:
        print("Document has 0 tables.")
    if hasattr(docling_doc, "images"):
        print(f"Document has {len(docling_doc.images)} images")
    else:
        print("Document has 0 images.")

    # Get full text for document saving to db
    html_text = docling_doc.export_to_html()
    # remove newlines
    html_text = html_text.replace("\n", "")

    print(f"Time taken to convert: {(time.time() - start_time):.2f} seconds")

    return html_text, docling_doc


def chunk_document(docling_doc: DLDocument):
    print("Chunking")
    start_time = time.time()

    # Use HybridChunker to split document into chunks
    chunker = HybridChunker(
        merge_peers=True,
    )
    chunk_iter = chunker.chunk(dl_doc=docling_doc)

    # Collect chunks without contextualization, only text content
    chunk_objects = []
    chunk_index = 0
    for chunk in chunk_iter:
        # Get text from DocChunk object
        chunk_text = chunk.text if hasattr(chunk, "text") else str(chunk)

        # Skip empty chunks or chunks that are not primarily text
        if not chunk_text or not chunk_text.strip():
            continue

        # Create Chunk object
        chunk_obj = Chunk(
            chunk_index=chunk_index,
            chunk_text=chunk_text.strip(),
            chunk_length=len(chunk_text.strip()),
        )
        chunk_objects.append(chunk_obj)
        chunk_index += 1

    if len(chunk_objects) <= 1:
        print(f"Time taken to chunk: {(time.time() - start_time):.2f} seconds")
        print("Only 1 chunk")
        return chunk_objects

    og_num_chunks = len(chunk_objects)

    # Delete a chunk if the next chunk contains the current chunk text (i.e. it's a duplicate, or slides adding more text)
    try:
        for i in range(len(chunk_objects) - 2):
            chunk_text = chunk_objects[i].chunk_text
            next_chunk_text = chunk_objects[i + 1].chunk_text
            # Check if the next chunk contains the current chunk text
            if len(next_chunk_text) > len(chunk_text) and chunk_text in next_chunk_text:
                chunk_objects.pop(i)
                i -= 1

        if len(chunk_objects) != og_num_chunks:
            print(
                f"Number of removed duplicate chunks: {og_num_chunks - len(chunk_objects)}"
            )
            og_num_chunks = len(chunk_objects)
    except Exception as e:
        print(f"Error deleting duplicate chunks: {e}")

    # Merge chunks with neighbours until all chunks are above MIN_CHUNK_LENGTH
    i = 0
    n_merged = 0
    try:
        while i < len(chunk_objects):
            chunk = chunk_objects[i]

            # check if chunk is long enough
            if len(chunk.chunk_text) >= MIN_CHUNK_LENGTH:
                # if last chunk, we're done
                if i == len(chunk_objects) - 1:
                    break
                # if not last chunk, move to next chunk
                i += 1
                continue

            # if first chunk, merge with next chunk
            if i == 0:
                idx_to_merge_with = i + 1
            # if last chunk, merge with prev chunk
            elif i == len(chunk_objects) - 1:
                idx_to_merge_with = i - 1
            # if middle chunk, merge with next chunk if it's smaller
            elif len(chunk_objects[i + 1].chunk_text) < len(
                chunk_objects[i - 1].chunk_text
            ):
                idx_to_merge_with = i + 1
            # else merge with prev chunk
            else:
                idx_to_merge_with = i - 1

            # merge chunk with chosen chunk
            chunk_objects[idx_to_merge_with].chunk_text += "\n\n" + chunk.chunk_text
            chunk_objects.pop(i)
            n_merged += 1
    except Exception as e:
        print(f"Error merging chunks: {e}")

    # update chunk length and reindex
    for i, chunk in enumerate(chunk_objects):
        chunk.chunk_length = len(chunk.chunk_text)
        chunk.chunk_index = i

    if len(chunk_objects) > 1:
        assert all(
            len(chunk.chunk_text) >= MIN_CHUNK_LENGTH for chunk in chunk_objects
        ), "Not all chunks are long enough after merging"

    print(f"Time taken to chunk: {(time.time() - start_time):.2f} seconds")

    return chunk_objects
