# Privacy-Focused Intelligent Tutoring System

A modern, privacy-conscious intelligent tutoring system that generates personalised learning tasks from your course materials while giving you full control over your data.

## Features

- **Document Upload**: Upload course materials (PDFs, documents) for automatic processing
- **AI-Generated Tasks**: Automatically creates multiple-choice questions
- **Personalised Learning**: Study mode with individual feedback and progress tracking
- **Course Management**: Organise materials into courses and track learning progress

## Manage lectures

<img width="1911" height="971" alt="image" src="https://github.com/user-attachments/assets/6cd2a74a-358c-4fad-82eb-e8ec46d20ea7" />

## Study

<img width="1242" height="831" alt="image" src="https://github.com/user-attachments/assets/888564f3-b573-4483-a334-5d07eaefe5d0" />


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
#### Detailed First Time Installation (uv)
If you are using Windows:
Open powershell and run the following:
```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

env:Path = "C:\Users\[replace_with_your_username]\.local\bin;$env:Path"
```

If you are using Linux (Ubuntu):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

source $HOME/.local/bin/env

```
Sync the project's dependencies with the environment.

``` bash
uv sync

```

##### NB: Ensure the docker deamon is running

You should see the following when you run docker compose command:

``` bash
docker-compose up -d  
[+] up 26/26
 ✔ Image ghcr.io/saurluca/its-docling-serve:main Pulled                                                           428.9s
 ✔ Image postgres:17-alpine                      Pulled                                                           23.9ss
 ✔ Network its_default                           Created                                                          0.1s
 ✔ Container db                                  Created                                                          0.5s
 ✔ Container docling-serve                       Created                                                          0.1s
```

### Frontend Setup

Set environment variables for database and AI API keys in frontend/.env.example

To instal bun: [installing bun](https://bun.com/docs/installation)

#### Detailed First Time Installation (Bun)
If you are using Windows:
Open powershell and run the following:
```bash
powershell -c "irm bun.sh/install.ps1|iex"

env:Path = "C:\Users\[replace_with_your_username]\.bun\bin;$env:Path"
```

If you are using Linux (Ubuntu):
```bash
curl -fsSL https://bun.com/install | bash

```




```bash
cd frontend

bun install

bun add -g pnpm
npx update-browserslist-db@latest

bun run dev
```

### Database and Docling Setup (Local development)

```bash
docker-compose up -d

docker-compose exec db psql -U postgres -c "CREATE DATABASE its;"

docker-compose exec db psql -U postgres -c "ALTER USER postgres WITH PASSWORD 'postgres';" #you can replace the with the password set in the .env
further troubleshooting :
docker-compose exec db psql -h localhost -p 5432 -U postgres -d its -W #psql terminal and create database from their ( internal connections (from inside the Docker #container) are set to "Trust" mode, meaning they ignore passwords. )

docker container ls
docker container inspect [container_id]
```
-d dbname
-U username
-W
--password

    Force psql to prompt for a password before connecting to a database, even if the password will not be used.

For further troubleshooting :
```bash
netstat -ano | findstr :5432 

docker container ls

docker container inspect [container_id] # obtained from the docker container ls command


Run the relation_creation.py file to create all the tables afer you create the database
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
