# Project Description

This Project implements a Pipeline for an Intelligent Tutoring System (ITS). The goal is to prepare the data for a RAG system,
by converting information from files to machine readable knowledge graphs.

1. Convert input files (pdf, for now) to text. (Clean text?)
2. Convert text to Knowledge Graph
3. Provide API to query knowledge graph.

## Tech stack

To be discussed, so far:

- Langchain
- PyPDF2
- Neo4J


## Folder structure:

backend/
├── router.py         # FastAPI endpoints (moved from main.py)
├── schemas.py        # Pydantic request/response models
├── models.py         # Database models (unchanged)
├── dependencies.py   # Router dependencies (DB sessions)
├── config.py         # Configuration settings (DB, LLM, app)
├── constants.py      # Module-specific constants
├── exceptions.py     # Custom exception classes
├── service.py        # Business logic (question generation, evaluation, summarization)
├── utils.py          # Utility functions (DB operations, text processing)
└── main.py           # Clean app setup with router integration