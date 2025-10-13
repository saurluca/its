# Privacy-Focused Intelligent Tutoring System

A modern, privacy-conscious intelligent tutoring system that generates personalised learning tasks from your course materials while giving you full control over your data.

## Features

- **Document Upload**: Upload course materials (PDFs, documents) for automatic processing
- **AI-Generated Tasks**: Automatically creates multiple-choice questions
- **Personalised Learning**: Study mode with individual feedback and progress tracking
- **Course Management**: Organise materials into courses and track learning progress


<img width="1921" height="1081" alt="image" src="https://github.com/user-attachments/assets/813f6c1c-7332-48bd-ab70-22af97bd2e70" />


## Architecture

- **Frontend:** Vue, Nuxt, TailwindCSS
- **Backend:** Python, FastAPI, PostgreSQL
- **CICD:** Docker, GitHub, GitHub Actions, 
- **AI:** DSPy, OpenRouter, GPT-4o, GPT-4o-mini
- **Document Parsing:** Docling

## Quick Start

### Backend Setup

Set environment variables for database and AI API keys in backend/.env.example

With UV no venv needs to be manually created, requirements will installed automatically as well.
If you don't have UV install it first: [installing uv](https://docs.astral.sh/uv/getting-started/installation/)

```bash
cd backend

uv run uvicorn main:app --reload
```

### Frontend Setup

Set environment variables for database and AI API keys in frontend/.env.example

To instal bun: [installing bun](https://bun.com/docs/installation)

```bash
cd frontend

bun install

bun run dev
```

### Database and Docling Setup

```bash
docker-compose up -d
```

### Pre commit hooks

```bash
uvx pre-commit install
```

## 🔒 Privacy Features

- **Everything Open Source**: You can easil host the system yourself
- **Local Processing**: Option to run AI models locally via Ollama
- **Transparent Processing**: See exactly how your materials are processed
- **Control over Personal Data** Decide which data is saved about you

## 📚 How It Works

1. **Upload** your course materials (lectures, textbooks, notes)
2. **Generate** AI-powered questions and tasks automatically
3. **Study** with personalized feedback and progress tracking

## Deployment Testing

The repository includes automated deployment health checks that run in GitHub Actions:

- **Health Check Scripts**: Located in `/scripts/` directory
- **CI/CD Integration**: Automatic testing on `main` and `live` branch deployments
- **Verification**: Tests backend API endpoints and frontend accessibility
- **Documentation**: See `/scripts/README.md` for detailed usage

The deployment testing ensures that Docker images are functional before production deployment.
