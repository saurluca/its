from PyPDF2 import PdfReader


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


def main():
    pdf_path = "data/documents/neuroscience.pdf"
    text_path = "data/documents/neuroscience.txt"

    text = extract_text_from_pdf(pdf_path)
    save_text_to_file(text, text_path)
    
if __name__ == "__main__":
    main()
