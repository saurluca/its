# Privacy-Focused Intelligent Tutoring System

A modern, privacy-conscious intelligent tutoring system that generates personalized learning tasks from your course materials while giving you full control over your data.

## Features

- **Document Upload**: Upload course materials (PDFs, documents) for automatic processing
- **AI-Generated Tasks**: Automatically creates multiple-choice questions
- **Personalized Learning**: Study mode with individual feedback and progress tracking
- **Privacy Control**: You decide how much data to share - from local processing to cloud AI
- **Course Management**: Organize materials into courses and track learning progress

## Architecture

- **Backend**: FastAPI with PostgreSQL, using DSPy for AI task generation
- **Frontend**: Nuxt.js with Vue 3, Tailwind CSS for modern UI
- **AI**: Configurable LLM support (Groq, Ollama) for privacy-conscious AI processing
- **Database**: SQLModel with automatic migrations

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

### Database Setup

```bash
docker-compose up -d
```

### Pre commit hooks

```bash
uvx pre-commit install
```

## 🔒 Privacy Features

- **Local Processing**: Option to run AI models locally via Ollama
- **No Data Retention**: Clear data deletion options
- **Transparent Processing**: See exactly how your materials are processed
- **Control over Personal Data** Decide which data is saved about you

## 📚 How It Works

1. **Upload** your course materials (lectures, textbooks, notes)
2. **Generate** AI-powered questions and tasks automatically
3. **Study** with personalized feedback and progress tracking

## 🛠️ Tech Stack

- **Backend**: FastAPI, SQLModel, DSPy, PostgreSQL
- **Frontend**: Nuxt.js, Vue 3, Tailwind CSS
- **AI**: Grok API, Ollama (local), through LiteLLM
- **Deployment**: Docker, Docker Compose

## Roadmap

- [ ] Free text questions
- [ ] Reference to course material

## Deployment Testing

The repository includes automated deployment health checks that run in GitHub Actions:

- **Health Check Scripts**: Located in `/scripts/` directory
- **CI/CD Integration**: Automatic testing on `main` and `live` branch deployments  
- **Verification**: Tests backend API endpoints and frontend accessibility
- **Documentation**: See `/scripts/README.md` for detailed usage

The deployment testing ensures that Docker images are functional before production deployment.
