from fastapi import FastAPI, CORSMiddleware, HTTPException, status
from typing import BinaryIO, List, Tuple
import fitz
from PIL import Image
import io
from io import BytesIO
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import DocumentStream
from docling.datamodel.document import DoclingDocument as DLDocument
from docling.chunking import HybridChunker
from documents.models import Chunk
from dotenv import load_dotenv

MIN_CHUNK_LENGTH = 420


load_dotenv()

app = FastAPI(
    title="Docling Serve",
    description="Docling service for Intelligent Tutoring System",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


# TODO: this fixes the issues with some pdfs, but significantly increases the compute time, because docling needs to do full OCR on the images
def flatten_pdf_in_memory(pdf_bytes: BytesIO) -> BytesIO:
    """
    Rasters a PDF from a byte stream and returns a new flattened PDF as a byte stream.
    """
    print("Flattening PDF")
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

    return flattened_pdf_bytes


@app.post("/convert")
def extract_docling_doc(
    file_obj: BinaryIO, filename: str, flatten_pdf: bool = False
) -> Tuple[str, DLDocument]:
    if not (file_obj and hasattr(file_obj, "read")):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Input must be a file-like object with .read()"
        )

    print("Converting doc using Docling")
    # Use the provided filename directly
    name = filename or "uploaded_file"

    # Ensure name has a proper extension - if no extension, add .txt as fallback
    if "." not in name:
        name += ".txt"

    file_obj.seek(0)
    file_content = file_obj.read()
    if not file_content:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "File is empty or could not be read"
        )

    stream_like = BytesIO(file_content)
    if flatten_pdf:
        stream_like = flatten_pdf_in_memory(stream_like)

    stream = DocumentStream(name=str(name), stream=stream_like)
    converter = DocumentConverter()
    result = converter.convert(stream)
    if not result or not result.document:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Could not convert file to document"
        )
    docling_doc = result.document

    # Get full text for document saving to db
    html_text = docling_doc.export_to_html()
    if not html_text:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not export document to HTML"
        )
    # remove newlines
    html_text = html_text.replace("\n", "")

    return html_text, docling_doc


@app.post("/chunk")
def chunk_document(docling_doc: DLDocument) -> List[Chunk]:
    print("Chunking")

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
        print("Only 1 chunk")
        return chunk_objects

    og_num_chunks = len(chunk_objects)

    # Delete a chunk if the next chunk contains the current chunk text (i.e. it's a duplicate, or slides adding more text)
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

    # Merge chunks with neighbours until all chunks are above MIN_CHUNK_LENGTH
    i = 0
    n_merged = 0
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

    # update chunk length and reindex
    for i, chunk in enumerate(chunk_objects):
        chunk.chunk_length = len(chunk.chunk_text)
        chunk.chunk_index = i

    if len(chunk_objects) > 1:
        assert all(
            len(chunk.chunk_text) >= MIN_CHUNK_LENGTH for chunk in chunk_objects
        ), "Not all chunks are long enough after merging"

    return chunk_objects
