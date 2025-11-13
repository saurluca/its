from typing import List, Any, cast, Dict, Tuple
from uuid import UUID, uuid4
import asyncio
import dspy
import time
from tqdm import tqdm
import random
from fastapi import HTTPException
from datetime import datetime, timezone
from sqlmodel import Session, select
from dependencies import get_database_engine, get_large_llm_no_cache

from constants import (
    REQUIRED_ANSWER_OPTIONS,
    TASKS_PER_SESSION,
    SM2_PARTIAL_CREDIT,
    SM2_NEW_TASK_BOOST,
    SM2_RECENCY_WEIGHT,
)
from documents.models import Chunk
from tasks.models import (
    Task,
    TaskType,
    AnswerOption,
    TaskReadTeacher,
    TeacherResponseMultipleChoice,
    TeacherResponseFreeText,
    TaskUserLink,
)
from units.models import UnitTaskLink
import logging
# Set up logging
logger = logging.getLogger(__name__)

class BatchedLM:
    """A wrapper for DSPy LM that batches inference requests for better throughput."""
    
    def __init__(self, lm: dspy.LM, batch_size: int = 8, timeout: float = 30.0):
        self.lm = lm
        self.batch_size = batch_size
        self.timeout = timeout
        self._request_queue = asyncio.Queue()
        self._response_futures = {}
        self._batch_task = None
        self._running = False
    
    async def start(self):
        """Start the batch processing task."""
        if not self._running:
            self._running = True
            self._batch_task = asyncio.create_task(self._process_batches())
    
    async def stop(self):
        """Stop the batch processing task."""
        self._running = False
        if self._batch_task:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass
    
    async def _process_batches(self):
        """Process requests in batches."""
        while self._running:
            try:
                # Collect a batch of requests
                batch = []
                futures = []
                
                # Wait for the first request
                request_id, (signature, kwargs) = await asyncio.wait_for(
                    self._request_queue.get(), timeout=self.timeout
                )
                batch.append((request_id, signature, kwargs))
                futures.append(self._response_futures[request_id])
                
                # Try to collect more requests without waiting too long
                try:
                    while len(batch) < self.batch_size:
                        request_id, (signature, kwargs) = await asyncio.wait_for(
                            self._request_queue.get(), timeout=0.1
                        )
                        batch.append((request_id, signature, kwargs))
                        futures.append(self._response_futures[request_id])
                except asyncio.TimeoutError:
                    pass
                
                # Process the batch
                try:
                    # Group by signature type for more efficient batching
                    signature_groups = {}
                    for request_id, signature, kwargs in batch:
                        # FIXED: signature IS the class, not an instance
                        signature_type = signature
                        if signature_type not in signature_groups:
                            signature_groups[signature_type] = []
                        signature_groups[signature_type].append((request_id, kwargs))
                    
                    # Process each signature group
                    for signature_type, requests in signature_groups.items():
                        # Create a list of kwargs for this signature type
                        kwargs_list = [kwargs for _, kwargs in requests]
                        
                        # Process in a thread pool to avoid blocking the event loop
                        results = await asyncio.to_thread(
                            self._process_batch_for_signature, signature_type, kwargs_list
                        )
                        
                        # Set the results for each request
                        for (request_id, _), result in zip(requests, results):
                            if request_id in self._response_futures:
                                self._response_futures[request_id].set_result(result)
                                del self._response_futures[request_id]
                
                except Exception as e:
                    # If any error occurs, set it for all futures in the batch
                    for request_id, _, _ in batch:
                        if request_id in self._response_futures:
                            self._response_futures[request_id].set_exception(e)
                            del self._response_futures[request_id]
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.exception(f"Error in batch processing: {e}")
    
    def _process_batch_for_signature(self, signature_type, kwargs_list):
        """Process a batch of requests for a specific signature type."""
        results = []
        
        # FIXED: signature_type IS the class, compare directly
        # Create a ChainOfThought instance for this signature type
        if signature_type == TaskMultipleChoice:
            model = dspy.ChainOfThought(TaskMultipleChoice)
        elif signature_type == TaskFreeText:
            model = dspy.ChainOfThought(TaskFreeText)
        elif signature_type == TeacherMultipleChoice:
            model = dspy.ChainOfThought(TeacherMultipleChoice)
        elif signature_type == TeacherFreeText4Way:
            model = dspy.ChainOfThought(TeacherFreeText4Way)
        else:
            raise ValueError(f"Unknown signature type: {signature_type}")
        
        # Process each request in the batch
        for kwargs in kwargs_list:
            try:
                result = model(lm=self.lm, **kwargs)
                results.append(result)
            except Exception as e:
                results.append(e)
        
        return results
    
    async def infer(self, signature, **kwargs):
        """Submit an inference request and return the result."""
        if not self._running:
            await self.start()
        
        request_id = str(uuid4())
        future = asyncio.Future()
        self._response_futures[request_id] = future
        
        # Add the request to the queue
        await self._request_queue.put((request_id, (signature, kwargs)))
        
        # Wait for the result
        return await future

# Global batched LM instance
_batched_lm = None

def get_batched_lm():
    """Get or create the global batched LM instance."""
    global _batched_lm
    if _batched_lm is None:
        lm = get_large_llm_no_cache()
        _batched_lm = BatchedLM(lm, batch_size=8)
        # Note: In a real implementation, you'd want to start this at application startup
        # and stop it at shutdown
        asyncio.create_task(_batched_lm.start())
    return _batched_lm


# Task generation with batched LM
async def generate_tasks(
    document_id: UUID,
    chunks: List[Chunk],
    num_tasks: int = 3,
    task_type: str = "multiple_choice",
    forbidden_questions: set[str] | None = None,
) -> List[Task]:
    """
    Generate tasks from document chunks using batched LM inference
    
    Args:
        document_id: Document ID
        chunks: List of document chunks
        num_tasks: Number of tasks to generate
        task_type: Type of task to generate
        forbidden_questions: Set of questions to avoid

    Returns:
        List of Task objects
    """
    batched_lm = get_batched_lm()
    
    logger.info(
        f"Generating {num_tasks} tasks for document {document_id} with {len(chunks)} chunks using batched LM"
    )

    tasks: List[Task] = []
    start_time = time.time()

    # Track questions to avoid duplicates against provided forbidden set and within this batch
    seen_questions: set[str] = (
        set(forbidden_questions) if forbidden_questions else set()
    )

    max_attempts = 4
    attempts = 0
    while len(tasks) < num_tasks and attempts < max_attempts:
        remaining = num_tasks - len(tasks)

        # Select up to len(chunks) chunks without replacement, then the rest with replacement
        if remaining <= len(chunks):
            selected_chunks = random.sample(chunks, remaining)
        else:
            selected_chunks = list(chunks)
            selected_chunks += [
                random.choice(chunks) for _ in range(remaining - len(chunks))
            ]

        # Create inference tasks for all chunks - FIXED SECTION
        inference_tasks = []
        for chunk in selected_chunks:
            if task_type == "multiple_choice":
                inference_tasks.append(
                    batched_lm.infer(TaskMultipleChoice, text=chunk.chunk_text)
                )
            elif task_type == "free_text":
                inference_tasks.append(
                    batched_lm.infer(TaskFreeText, text=chunk.chunk_text)
                )
            else:
                raise ValueError(f"Invalid task type: {task_type}")
        
        # Wait for all inferences to complete
        results = await asyncio.gather(*inference_tasks, return_exceptions=True)
        
        # Process results
        for chunk, result in zip(selected_chunks, results):
            if len(tasks) >= num_tasks:
                break
                
            if isinstance(result, Exception):
                logger.error(f"Error generating task for chunk {chunk.id}: {result}")
                continue
            
            # Validate multiple choice tasks have the correct number of answer options
            if (
                task_type == "multiple_choice"
                and len(result.answer) != REQUIRED_ANSWER_OPTIONS
            ):
                continue
            
            question_text = result.question
            if question_text in seen_questions:
                # Duplicate question, skip
                continue
            
            task = _create_task_from_response(result, task_type, chunk.id)
            tasks.append(task)
            seen_questions.add(question_text)

        attempts += 1

    end_time = time.time()
    logger.info(f"Generated {len(tasks)} unique tasks in {end_time - start_time} seconds")

    if not tasks:
        logger.warning(
            f"Warning: No tasks could be generated from the provided chunks for document {document_id}"
        )
        return []

    return tasks


class TaskMultipleChoice(dspy.Signature):
    """Generate a single multiple choice question, with 4 answer options, and exactly one correct answer which is in the first position.
    Generate the question based on the provided text.
    The question should be short and concise.
    The question should be relevant to the text and require understanding of the material.
    Do not enumerate the answer options, no numbering or alphabet.
    The student does not see the text chunk.
    There should be exactly one correct answer.
    The text is an excerpt from a lecture.
    """

    text: str = dspy.InputField(description="The text to generate a question from.")

    question: str = dspy.OutputField(
        description="A single multiple choice question generated from the key points. It should foster a deep understanding of the material. The question should be short and concise."
    )

    answer: list[str] = dspy.OutputField(
        description="A list of 4 answer options for each question. Exactly one answer option is correct. The correct answer should always be in the first position. Do not enumerate the answer options, no numbering or alphabet."
    )


class TaskFreeText(dspy.Signature):
    """Generate a single free text question from a text chunk and an ideal answer.
    The question should be short and concise.
    The question should be answerable in 1 to 3 sentences.
    The question should be relevant to the text and require understanding of the material.
    Keep close to the text, do not make up information.
    The student does not see the text chunk.
    The text is an excerpt from a lecture.
    Also provide a correct answer to the question.
    Keep this answer short and concise, containing the key points relevant to answer the question.
    The user's answer will be compared to this answer.
    """

    text: str = dspy.InputField(description="The text to generate a question from.")

    question: str = dspy.OutputField(
        description="A single question generated from the text"
    )
    answer: str = dspy.OutputField(
        description="The ideal, correct answer to the question. Concise and contains the key points relevant to answer the question."
    )


class TeacherFreeText2Way(dspy.Signature):
    """You are grading a student's response to a short answer-question about the text {chunk} below.

    Students have been asked this question:  {question}

    A correct answer to this question is: {correct_answer}

    Your task is to decide if the student’s answer is correct or wrong.

    A student answer is wrong if it misses a key part of the correct answer.
    Ignore Grammar and Spelling mistakes, only evaluate the content.

    If the student response is correct, you will respond with score = 0.
    If the student response is wrong, you will respond with score = 1.
    """

    chunk: str = dspy.InputField(
        description="The chunk of text related to the question."
    )

    question: str = dspy.InputField(description="The question asked to the student.")

    correct_answer: str = dspy.InputField(
        description="The correct answer to the question."
    )

    student_answer: str = dspy.InputField(
        description="The student's answer to the question."
    )

    score: int = dspy.OutputField(
        description="0 if the content of the student's answer is correct, 1 if it is wrong."
    )


class TeacherFreeText4Way(dspy.Signature):
    """You are a teacher for undergraduate students.
    Your job is to evaluate the student's answers to a short answer-question about the text {chunk} below and provide short and concise feedback.

    Students have been asked this question:  {question}

    A correct answer to this question is: {correct_answer}

    Your task is to decide if the student’s answer is correct, partially correct but incomplete, irrelevant or contradictory.
    Answer based on the chunk and the provided correct answer only.

    Correct: The student's answer is correct and includes the key points from the correct answer.
    If the student response is correct, you will respond with score = 0

    Partially correct but incomplete: The student's answer correct, but does not include the key points from the correct answer.
    If the student response is partially correct but incomplete, you will respond with score = 1

    Contradictory: The student's answer contradicts the chunk and the correct answer. It is not related to the question.
    If the student response is contradictory, you will respond with score = 2

    Irrelevant: The student's answer is irrelevant to the question.
    If the student response is irrelevant, you will respond with score = 3

    The feedback should be short and concise, 1 to 2 sentences.
    The feedback should explain the reasoning behind the score, e.g. what is missing, what is wrong, what is right in the student's answer.
    The feedback should be based on the student's answer and the chunk.
    """

    chunk: str = dspy.InputField(
        description="The chunk of text related to the question."
    )

    question: str = dspy.InputField(description="The question asked to the student.")

    correct_answer: str = dspy.InputField(
        description="The correct answer to the question."
    )

    student_answer: str = dspy.InputField(
        description="The student's answer to the question."
    )

    score: int = dspy.OutputField(
        description="0 if the content of the student's answer is correct, 1 if it is partially correct but incomplete, 2 if it is contradictory, 3 if it is irrelevant."
    )

    feedback: str = dspy.OutputField(
        description="Short and concise feedback for the student based on their answer."
    )


class TeacherMultipleChoice(dspy.Signature):
    """You are a teacher for undergraduate students. Your job is to evaluate the student's answers to a Multiple Choice question
    based on the chunk of text, which is an excerpt from the lecture, and the question.

    Evaluate the student's answer, and provide feedback.
    """

    chunk: str = dspy.InputField(
        description="The chunk of text related to the question."
    )
    question: str = dspy.InputField(description="The question asked to the student.")

    correct_answer: str = dspy.InputField(
        description="The correct answer to the question."
    )

    student_answer: str = dspy.InputField(
        description="The student's answer to the question. One of multiple predefined answer options."
    )

    feedback: str = dspy.OutputField(
        description="Short and concise feedback for the student based on their answer, if it is correct or incorrect, based on the chunk and the answer options."
        "If it is incorrect, provide a short explanation of what the correct answer is and why it is correct. The feedback should be based on the student's answer and the chunk."
    )


def _get_task_generator(task_type: str):
    """Get the appropriate task generator based on task type."""
    if task_type == "multiple_choice":
        return dspy.ChainOfThought(TaskMultipleChoice)
    elif task_type == "free_text":
        return dspy.ChainOfThought(TaskFreeText)
    else:
        raise ValueError(f"Invalid task type: {task_type}")


def _generate_single_task(chunk: Chunk, task_generator, task_type: str, lm: dspy.LM):
    """Generate a single task from a chunk."""
    try:
        qg_response = task_generator(text=chunk.chunk_text, lm=lm)

        # Validate multiple choice tasks have the correct number of answer options
        if (
            task_type == "multiple_choice"
            and len(qg_response.answer) != REQUIRED_ANSWER_OPTIONS
        ):
            return None

        return qg_response
    except Exception as e:
        logger.exception(f"Error generating task for chunk {chunk.id}: {e}")
        return None


def _create_task_from_response(qg_response, task_type: str, chunk_id: UUID) -> Task:
    """Create a Task object from a task generation response."""
    task = Task(
        type=TaskType.MULTIPLE_CHOICE
        if task_type == "multiple_choice"
        else TaskType.FREE_TEXT,
        question=qg_response.question,
        chunk_id=chunk_id,
    )

    # Create answer options for multiple choice questions
    if task_type == "multiple_choice":
        for i, answer in enumerate(qg_response.answer):
            answer_option = AnswerOption(
                answer=answer,
                is_correct=(i == 0),  # First answer is correct
                task=task,
            )
            task.answer_options.append(answer_option)
    # For free text questions, create a single answer option with the ideal answer
    elif task_type == "free_text":
        answer_option = AnswerOption(
            answer=qg_response.answer,
            is_correct=True,  # The ideal answer is always correct
            task=task,
        )
        task.answer_options.append(answer_option)

    return task


# Use batch LM
async def process_generate_tasks_for_documents(
    unit_id: UUID,
    document_ids: List[UUID],
    num_tasks: int,
    task_type: TaskType,
    forbidden_questions: set[str],
):
    """Background task that generates tasks for given documents and links them to a unit using batched LM."""
    logger.info(f"[bg] Start generating tasks for unit {unit_id}...")
    engine = get_database_engine()
    with Session(engine) as session:
        try:
            all_generated_tasks: list[Task] = []

            # Get the batched LM instance
            batched_lm = get_batched_lm()

            for document_id in document_ids:
                chunks_for_doc: list[Chunk] = session.exec(
                    select(Chunk).where(
                        Chunk.document_id == document_id, Chunk.important
                    )
                ).all()

                if not chunks_for_doc:
                    logger.error("[bg] no chunks for document", document_id)
                    continue

                # Use the batched task generation
                task_type_str = "multiple_choice" if task_type == TaskType.MULTIPLE_CHOICE else "free_text"
                generated: list[Task] = await generate_tasks(
                    document_id,
                    chunks_for_doc,
                    num_tasks,
                    task_type_str,
                    forbidden_questions,
                )

                for task in generated:
                    session.add(task)
                    session.flush()
                    session.add(UnitTaskLink(unit_id=unit_id, task_id=task.id))
                    if task.question:
                        forbidden_questions.add(task.question)

                all_generated_tasks.extend(generated)

            if all_generated_tasks:
                session.commit()
                logger.info(
                    f"[bg] Finished generating {len(all_generated_tasks)} tasks for unit {unit_id}"
                )
            else:
                logger.error(
                    f"[bg] No tasks generated for unit {unit_id} (no important chunks or other constraints)"
                )
        except Exception as e:
            session.rollback()
            logger.exception(f"[bg] Error generating tasks for unit {unit_id}: {e}")


async def evaluate_student_answer_async(
    task_teacher: TaskReadTeacher,
    student_answer: str,
    task_type: TaskType,
) -> TeacherResponseMultipleChoice | TeacherResponseFreeText:
    """Evaluate student answer using batched LM."""
    batched_lm = get_batched_lm()
    
    try:
        if task_type == TaskType.MULTIPLE_CHOICE:
            logger.info("Evaluating multiple choice task")
            response = await batched_lm.infer(
                TeacherMultipleChoice,
                chunk=task_teacher.chunk,
                question=task_teacher.question,
                correct_answer=task_teacher.answer_options[0].answer,
                student_answer=student_answer,
            )
        elif task_type == TaskType.FREE_TEXT:
            logger.info("Evaluating free text task")
            response = await batched_lm.infer(
                TeacherFreeText4Way,
                chunk=task_teacher.chunk,
                question=task_teacher.question,
                correct_answer=task_teacher.answer_options[0].answer,
                student_answer=student_answer,
            )

        logger.info("response", response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating answer: {e}")
    
# Wrapper to maintain compatibility with existing synchronous interface
def evaluate_student_answer(
    task_teacher: TaskReadTeacher,
    student_answer: str,
    task_type: TaskType,
    lm: dspy.LM,  # This parameter is kept for compatibility but not used
) -> TeacherResponseMultipleChoice | TeacherResponseFreeText:
    """Synchronous wrapper for evaluate_student_answer_async."""
    # Run the async function in the event loop
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        evaluate_student_answer_async(task_teacher, student_answer, task_type)
    )


def _compute_task_priority(
    task: Task,
    progress: TaskUserLink | None,
    now: datetime,
) -> float:
    """
    Compute a priority score for a task using simplified SM-2 ideas:
    - Unseen tasks get a large boost so they appear first.
    - Otherwise, higher when last attempt is older and correctness ratio is low.
    """
    if progress is None:
        return SM2_NEW_TASK_BOOST

    total = progress.times_correct + progress.times_incorrect + progress.times_partial
    if total == 0:
        return SM2_NEW_TASK_BOOST

    # Quality as proportion of success with partial weighted
    weighted_correct = (
        progress.times_correct + SM2_PARTIAL_CREDIT * progress.times_partial
    )
    quality = weighted_correct / total  # 0..1

    # Recency in days
    last = progress.updated_at or progress.created_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    days_since = (now - last).total_seconds() / 86400.0

    # Lower quality and older review => higher priority
    priority = (1.0 - quality) * 10.0 + days_since * SM2_RECENCY_WEIGHT
    return priority


def get_study_tasks_for_unit(
    unit_id: UUID,
    user_id: UUID,
    session,
) -> list[Task]:
    """
    Return up to TASKS_PER_SESSION tasks for a unit, ordered by priority.
    New tasks first; then ones with low performance and longest since review.
    """
    # Fetch tasks in unit
    from sqlmodel import select
    from units.models import UnitTaskLink

    db_tasks: list[Task] = session.exec(
        select(Task)
        .join(UnitTaskLink, Task.id == UnitTaskLink.task_id)
        .where(UnitTaskLink.unit_id == unit_id)
    ).all()

    if not db_tasks:
        return []

    # Fetch user progress links for these tasks
    task_ids = [t.id for t in db_tasks]
    progress_rows: list[TaskUserLink] = session.exec(
        select(TaskUserLink).where(
            TaskUserLink.user_id == user_id,
            cast(Any, TaskUserLink.task_id).in_(task_ids),
        )
    ).all()

    progress_by_task = {row.task_id: row for row in progress_rows}
    now = datetime.now(timezone.utc)

    scored = [
        (
            _compute_task_priority(task, progress_by_task.get(task.id), now),
            progress_by_task.get(task.id) is None,  # unseen flag
            task,
        )
        for task in db_tasks
    ]

    # Sort by priority desc (higher first), while keeping unseen before seen as tie-breaker
    # We can sort by (-priority, not unseen) to get desired order
    scored.sort(key=lambda x: (-x[0], not x[1]))

    ordered = [t for _, _, t in scored][:TASKS_PER_SESSION]
    return ordered
