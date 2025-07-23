from PyPDF2 import PdfReader
import mimetypes
import os
from db_utils import save_document_to_db
import re

def extract_text_from_pdf(pdf_path):
    with open(pdf_path, "rb") as file:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text


def clean_text(text):
    # remove NUL (0x00) bytes
    text = text.replace("\x00", "")   
    return text


def save_text_to_file(text, text_path):
    with open(text_path, "w") as file:
        file.write(text)


def read_text_from_file(text_path):
    with open(text_path, "r") as file:
        text = file.read()
    return text


def extract_text_from_file(
    file_or_path, output_path=None, save_to_file=False, mime_type=None, save_to_db=False
):
    assert file_or_path, "File or file path is required"
    text = None
    file_obj = None
    file_path = None

    # if it is a file path, get the mime type
    if isinstance(file_or_path, (str, bytes, os.PathLike)):
        file_path = file_or_path
        assert os.path.exists(file_path), f"File not found: {file_path}"
        assert os.path.isfile(file_path), f"File is a directory: {file_path}"
        assert os.path.getsize(file_path) != 0, "File is empty"
        mime_type = mimetypes.guess_type(file_path)[0]
    # if it is a file-like object
    elif hasattr(file_or_path, "read"):
        file_obj = file_or_path
        if not mime_type and hasattr(file_obj, "name"):
            mime_type = mimetypes.guess_type(file_obj.name)[0]
    else:
        raise ValueError("Input must be a file path or a file-like object")

    assert mime_type, (
        f"Could not determine MIME type of file: {getattr(file_obj, 'name', file_path)}"
    )

    if mime_type == "application/pdf":
        if file_obj:
            file_obj.seek(0)
            reader = PdfReader(file_obj)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
        else:
            text = extract_text_from_pdf(file_path)
    elif mime_type == "text/plain":
        if file_obj:
            file_obj.seek(0)
            text = (
                file_obj.read().decode()
                if hasattr(file_obj, "read")
                else file_obj.read()
            )
        else:
            text = read_text_from_file(file_path)
    elif mime_type and mime_type.startswith("image/"):
        # TODO: OCR image files
        raise ValueError("Image files are not yet supported")
    else:
        raise ValueError(f"Unsupported file type: {mime_type}")
    
    text = clean_text(text)

    if save_to_db:
        document_id = save_document_to_db(text)
        return document_id

    if save_to_file:
        assert output_path, "Output path is required when saving to file"
        save_text_to_file(text, output_path)

    return text
