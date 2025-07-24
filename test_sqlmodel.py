#!/usr/bin/env python3
"""
Test script for SQLModel migration
"""

from io import BytesIO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from db_utils import (
    create_db_and_tables,
    save_document_to_db,
    get_document_titles_and_ids_from_db,
)
from text_processing import extract_text_from_file_and_chunk


def test_sqlmodel_migration():
    print("Testing SQLModel migration...")

    # Initialize database
    print("1. Creating database tables...")
    create_db_and_tables()
    print("   ✅ Tables created successfully")

    # Test document save
    print("2. Testing document save...")
    test_content = "This is a test document for SQLModel migration testing."
    doc_id = save_document_to_db(test_content, title="Test Document")
    print(f"   ✅ Document saved with ID: {doc_id}")

    # Test document retrieval
    print("3. Testing document retrieval...")
    titles, ids = get_document_titles_and_ids_from_db()
    print(f"   ✅ Found {len(titles)} documents")
    print(f"   First document: {titles[0] if titles else 'None'}")

    # Test chunking with a markdown document
    print("4. Testing chunking functionality...")
    sample_markdown = """# Test Document for Chunking

## Introduction
This is a test document to verify that the chunking functionality works with SQLModel.

## Section 1
This section contains some content that should be split into chunks properly.

## Section 2
This is another section with more content for testing the chunking behavior.

## Conclusion
The chunking functionality should work correctly with the new SQLModel implementation.
"""

    # Create a BytesIO object to simulate file upload
    file_obj = BytesIO(sample_markdown.encode("utf-8"))
    file_obj.name = "test_chunking.md"

    try:
        result = extract_text_from_file_and_chunk(
            file_obj, save_to_db=True, mime_type="text/markdown"
        )
        print("   ✅ Chunking completed successfully")
        print(f"   Document ID: {result['document_id']}")
        print(f"   Total chunks: {len(result['chunks'])}")
        print(f"   Chunk IDs: {result['chunk_ids']}")

        # Show chunk previews
        for i, chunk in enumerate(result["chunks"][:3]):  # Show first 3 chunks
            print(f"   Chunk {i + 1}: {chunk['chunk_text'][:100]}...")

    except Exception as e:
        print(f"   ❌ Chunking failed: {e}")
        return False

    print("\n🎉 SQLModel migration test completed successfully!")
    return True


if __name__ == "__main__":
    try:
        test_sqlmodel_migration()
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
