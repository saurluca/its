from PyPDF2 import PdfReader
import mimetypes
import os


def extract_text_from_pdf(pdf_path):
    with open(pdf_path, "rb") as file:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text


def save_text_to_file(text, text_path):
    with open(text_path, "w") as file:
        file.write(text)


def read_text_from_file(text_path):
    with open(text_path, "r") as file:
        text = file.read()
    return text


def extract_text_from_file(file_path, output_path=None, save_to_file=False):
    assert file_path, "File path is required"
    assert os.path.exists(file_path), f"File not found: {file_path}"
    assert os.path.isfile(file_path), f"File is a directory: {file_path}"
    assert os.path.getsize(file_path) != 0, "File is empty"
    
    mime_type = mimetypes.guess_type(file_path)[0]
    
    assert mime_type, f"Could not determine MIME type of file: {file_path}"

    text = None

    if mime_type == "application/pdf":
        text = extract_text_from_pdf(file_path)
    elif mime_type == "text/plain":
        text = read_text_from_file(file_path)
    elif mime_type and mime_type.startswith("image/"):
        # TODO: OCR image files
        raise ValueError("Image files are not yet supported")
    else:
        raise ValueError(f"Unsupported file type: {mime_type}")

    if save_to_file:
        assert output_path, "Output path is required when saving to file"
        save_text_to_file(text, output_path)

    return text


def main():
    pdf_path = "data/documents/neuroscience.pdf"
    text_path = "data/documents/neuroscience.txt"

    extract_text_from_file(pdf_path, output_path=text_path, save_to_file=True)
    
if __name__ == "__main__":
    main()
