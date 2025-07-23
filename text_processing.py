from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import DocumentStream
from db_utils import save_document_to_db
from io import BytesIO


def extract_text_from_file(file_obj, save_to_db=False, mime_type=None):
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
            name = "uploaded_file.pdf"

    # Read all bytes and wrap in BytesIO for Docling
    file_obj.seek(0)
    file_bytes = file_obj.read()
    byte_stream = BytesIO(file_bytes)

    # Create DocumentStream with name and BytesIO stream
    stream = DocumentStream(name=str(name), stream=byte_stream)

    # Convert using Docling
    converter = DocumentConverter()
    result = converter.convert(stream)
    docling_doc = result.document
    text = docling_doc.export_to_text()

    # Clean text (remove NUL bytes)
    text = text.replace("\x00", "")

    if save_to_db:
        document_id = save_document_to_db(text)
        return document_id

    return text
