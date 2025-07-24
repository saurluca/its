from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import DocumentStream
from docling.chunking import HybridChunker
from io import BytesIO
import time

def extract_text_from_file_and_chunk(file_obj, mime_type=None):
    assert file_obj and hasattr(file_obj, "read"), (
        "Input must be a file-like object with .read()"
    )

    # Get the name for DocumentStream
    name = getattr(file_obj, "name", None)

    # For FastAPI UploadFile, use .filename if available
    if hasattr(file_obj, "filename") and file_obj.filename:
        name = file_obj.filename

    # If still no name, create a default based on mime_type or use generic
    if not name:
        if mime_type:
            # Map common mime types to extensions
            mime_to_ext = {
                "application/pdf": ".pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
                "text/html": ".html",
                "text/plain": ".txt",
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "image/tiff": ".tiff",
            }
            extension = mime_to_ext.get(mime_type, ".pdf")  # Default to PDF
            name = f"uploaded_file{extension}"
        else:
            # Default to PDF if no mime type provided
            # name = "uploaded_file.pdf"
            raise ValueError("No mime type provided")

    # Read all bytes and wrap in BytesIO for Docling
    file_obj.seek(0)
    file_bytes = file_obj.read()
    byte_stream = BytesIO(file_bytes)
    # Create DocumentStream with nam
    # e and BytesIO stream
    stream = DocumentStream(name=str(name), stream=byte_stream)
    print("Converting using Docling")
    # Convert using Docling
    converter = DocumentConverter()
    result = converter.convert(stream)
    docling_doc = result.document

    print("Exporting to text")
    # Get full text for document metadata
    full_text = docling_doc.export_to_text()

    print("Chunking")
    # Use HybridChunker to split document into chunks
    chunker = HybridChunker()
    chunk_iter = chunker.chunk(dl_doc=docling_doc)

    # Collect chunks with contextualized text
    chunks = []
    for i, chunk in enumerate(chunk_iter):
        enriched_text = chunker.contextualize(chunk=chunk)

        chunks.append(
            {
                "chunk_index": i,
                "chunk_text": enriched_text,
                "metadata": {"source_file": name, "chunk_length": len(enriched_text)},
            }
        )

    return {"full_text": full_text, "name": name, "chunks": chunks}
