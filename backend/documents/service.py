from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import DocumentStream
from docling.chunking import HybridChunker
from io import BytesIO
from constants import SUPPORTED_MIME_TYPES, MAX_TITLE_LENGTH, MIN_CHUNK_LENGTH
from exceptions import InvalidFileFormatError
from .models import Document, Chunk
import time
import dspy


def extract_text_from_file_and_chunk(file_obj, mime_type=None):
    """
    Extract text from file and chunk it

    Args:
        file_obj: File-like object
        mime_type: MIME type of the file

    Returns:
        Tuple of (Document, list[Chunk]) with the document and its chunks
    """
    assert file_obj and hasattr(file_obj, "read"), (
        "Input must be a file-like object with .read()"
    )

    # Get the name for DocumentStream
    name = getattr(file_obj, "name", None)

    # For FastAPI UploadFile, use .filename if available
    if hasattr(file_obj, "filename") and file_obj.filename:
        name = file_obj.filename

    # If still no name, create a default based on mime_type
    if not name:
        if mime_type:
            extension = SUPPORTED_MIME_TYPES.get(mime_type, ".pdf")
            name = f"uploaded_file{extension}"
        else:
            raise InvalidFileFormatError("No mime type provided")

    # Read all bytes and wrap in BytesIO for Docling
    file_obj.seek(0)
    file_bytes = file_obj.read()
    byte_stream = BytesIO(file_bytes)

    # Create DocumentStream with name and BytesIO stream
    stream = DocumentStream(name=str(name), stream=byte_stream)

    print("Converting using Docling")
    start_time = time.time()

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
    full_text = docling_doc.export_to_html()
    # remove newlines
    full_text = full_text.replace("\n", "")

    print(f"Time taken to convert: {time.time() - start_time} seconds")

    print("Chunking")
    # Use HybridChunker to split document into chunks, excluding images and documents
    chunker = HybridChunker(
        merge_peers=True,  # Merge undersized successive chunks with same headings
        include_images=False,  # Exclude images from chunks
        include_tables=False,  # Exclude tables from chunks
        include_figures=False,  # Exclude figures from chunks
        include_formulas=False,  # Exclude formulas from chunks
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

        # Skip chunks that are too short (likely non-text content)
        if len(chunk_text.strip()) < 10:  # Minimum text length
            continue

        # Create Chunk object
        chunk_obj = Chunk(
            chunk_index=chunk_index,
            chunk_text=chunk_text.strip(),
            chunk_length=len(chunk_text.strip()),
        )
        chunk_objects.append(chunk_obj)
        chunk_index += 1

    print(f"Time taken to chunk: {time.time() - start_time} seconds")

    if len(chunk_objects) <= 1:
        # Create Document object
        document = Document(
            title=name,
            content=full_text,
            source_file=name,
        )
        return document, chunk_objects

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

    assert all(len(chunk.chunk_text) >= MIN_CHUNK_LENGTH for chunk in chunk_objects), (
        "Not all chunks are long enough after merging"
    )

    # Create Document object
    document = Document(
        title=name,
        content=full_text,
        source_file=name,
    )

    return document, chunk_objects


class DocumentTitle(dspy.Signature):
    document_start: str = dspy.InputField(
        description="The first characters of the document."
    )
    document_title: str = dspy.OutputField(
        description=f"A short title for the document based on the first characters of the document. The document is part of a lecture course. Max length: {MAX_TITLE_LENGTH} characters."
    )


def generate_document_title(document_start: str) -> str:
    try:
        model = dspy.ChainOfThought(DocumentTitle)
        result = model(document_start=document_start)
        return result.document_title
    except Exception as e:
        print(f"Error generating document title: {e}")
        return "Untitled Document"
