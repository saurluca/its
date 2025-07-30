# ITS

## Vision

To provide an Intelligent Tutoring Sytem that helps student learn, through personalised tasks and dialog session with an
AI assitant. There is a great focus on individual control over data privacy and trustworthiness of the AI.

## Project Setup

1. `docker compose up -d`
2. `bun install`
3. `bunx drizzle-kit push` (if this fails, then `docker compose down -v` and jump back to step 1)
4. `bun run dev` and go to http://localhost:3000

Don't forget to copy .env.example to .env and fill in the values.

## Roadmap

1. MVP

- [x] Create Database
- [x] API endpoints
- [x] Create courses, skills
- [x] Tasks creation
  - [x] True/False
  - [x] Multiple Choice
  - [x] Free text
- [x] User view
  - [x] Solve tasks + right wrong feedback for true/false multiple choice
- [x] Teacher view
  - [x] Create tasks (questions / answers)
- [x] Skill progression
  - [x] Grade/point system?
  - [x] Each task contributes to a certain skill
- [x] Deployment for showcasing

2. AI and other features

- [ ] Save skillprogess on user and not on org
- [ ] AI can create novel questions
  - [ ] Based on uploaded pdf?
  - [ ] Based on existing questions / prof input?
  - [ ] Evaluate quality of questions and answers of ai (truthfulness, relevance, difficulty)
  - [ ] Seperate AI and Prof tasks? Indivudal vs general.
- [ ] AI evalutes quality of student answers (free text)
- [ ] Postmark for mailing
- [ ] skills can have different levels

3. AI with external information

- [ ] Incorporating Grades
- [ ] Interests ...

### Possible Ideas:

- [ ] Scheduling of rode learning repetitions
  - [ ] Improved scheduling based on algorithm
- [ ] Skill tree (connect skills)
  - [ ] Skill can be composed of other skills
- Task tree
  - Completing certain tasks well enough unlocks new ones
- Task difficulty ?
  - for AI and for Grading/ skill progression
- Explation of the soltuion
- Save previous answers / performance
  - for what?
- after registering log user in right away

Desgin:

- progress bar of current quiz at the top
- Only show one quesiton at a time vs all on one "sheet"

### questions

- What kind of learning are we talking about? What skills and courses? Math, programming, language ...
- Who is the user? And what do they want from the app?
- What is the goal of the app? What do we want to achieve? in one sentence
- What makes this app special?

## Planning of AI system

- How can we make the AI trustworthy? Relevance / truthfulness, control over data
- Where do we get training data from? Prompt engineering probably not enough.
- How to input information for the tasks and how to validate the output?
- Implemenation:
  - GPT wrapper?
  - self hosted?
  - How to evaluate the quality of the AI?

## Tech Stack

- Front- & Backend: Nuxt ssr: false
- Database: Postgres
- Hosting: kamal, self-hosted
