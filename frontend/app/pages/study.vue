<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useSessionStorage } from "@vueuse/core";
import type { Task } from "~/types/models";

const route = useRoute();
const { $authFetch } = useAuthenticatedFetch();
const pageState = ref<"studying" | "finished" | "no-tasks">("studying");
const repositoryId = ref("");
const tasks = ref<Task[]>([]);
const currentTaskIndex = ref(0);
const currentAnswer = ref("");
const showEvaluation = ref(false);
const evaluationStatus = ref<"correct" | "partial" | "incorrect">("incorrect");
const isCorrect = ref<boolean | null>(null);
const score = ref(0);
const loading = ref(false);
const error = ref<string | null>(null);
const feedback = ref<string | null>(null);
const router = useRouter();
const evaluating = ref<boolean>(false);


// Utility: Fisher-Yates shuffle to randomize tasks each session
function shuffleArray<T>(items: T[]): T[] {
  const array = [...items];
  for (let i = array.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    const temp = array[i]!;
    array[i] = array[j]!;
    array[j] = temp;
  }
  return array;
}

// Task generation state
const showGenerateTasksModal = ref(false);
const generatingTasks = ref(false);
const numTasksToGenerate = ref(5);

const currentTask = computed(() => tasks.value[currentTaskIndex.value]);

// HTML viewer state
const showHtmlViewer = ref(false);
const htmlContent = ref("");
const loadingHtml = ref(false);
const htmlError = ref("");
const highlightedChunkText = ref("");

// Sidebar state
const collapsed = useSessionStorage("collapsed", false);

// Keyboard handler for Enter key
function handleKeyPress(event: KeyboardEvent) {
  // Block navigation while evaluating
  if (evaluating.value) {
    event.preventDefault();
    return;
  }
  // Handle Enter key when evaluation is shown
  if (event.key === 'Enter' && showEvaluation.value) {
    event.preventDefault();
    nextQuestion();
  }
  // Handle Enter key when study session is finished
  else if (event.key === 'Enter' && pageState.value === 'finished') {
    event.preventDefault();
    restart();
  }
}

onMounted(() => {
  // Check if repositoryId is provided in URL parameters
  const repoId = route.query.repositoryId as string;
  if (repoId) {
    repositoryId.value = repoId;
    startStudy();
  }

  // Add keyboard event listener
  document.addEventListener('keydown', handleKeyPress);
});

onUnmounted(() => {
  // Clean up keyboard event listener
  document.removeEventListener('keydown', handleKeyPress);
});

async function startStudy() {
  if (!repositoryId.value) {
    error.value = "Please enter a Repository ID.";
    return;
  }
  loading.value = true;
  error.value = null;

  try {
    const responseData = await $authFetch(`/tasks/repository/${repositoryId.value}`) as Task[];

    if (responseData && responseData.length > 0) {
      // Randomize order of tasks for this study session
      tasks.value = shuffleArray(responseData);
      currentTaskIndex.value = 0;
      pageState.value = "studying";
    } else {
      pageState.value = "no-tasks";
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'An error occurred';
  } finally {
    loading.value = false;
  }
}

function openGenerateTasksModal() {
  numTasksToGenerate.value = 1;
  showGenerateTasksModal.value = true;
}

function closeGenerateTasksModal() {
  showGenerateTasksModal.value = false;
}

async function confirmGenerateTasks() {
  if (!repositoryId.value) return;
  generatingTasks.value = true;
  try {
    // Call the API to generate tasks for repository
    await $authFetch(
      `/tasks/generate_for_multiple_documents`,
      {
        method: "POST",
        body: {
          repository_id: repositoryId.value,
          document_ids: [], // This would need to be populated with repository documents
          num_tasks: numTasksToGenerate.value,
          task_type: "multiple_choice",
        },
      },
    );
    closeGenerateTasksModal();
    // Reload the page to start the study session
    await startStudy();
  } catch (err: unknown) {
    error.value = "Failed to generate tasks. Please try again. " + (err instanceof Error ? err.message : 'Unknown error');
  } finally {
    generatingTasks.value = false;
  }
}

async function evaluateAnswer() {
  if (currentAnswer.value === null || currentAnswer.value === "") {
    error.value = "Please enter an answer.";
    return;
  }

  feedback.value = "Evaluating...";
  evaluating.value = true

  if (currentTask.value?.type === 'multiple_choice') {
    const correct = currentAnswer.value === currentTask.value.answer_options.find(option => option.is_correct)?.answer;
    isCorrect.value = correct;
    evaluationStatus.value = correct ? 'correct' : 'incorrect';
    showEvaluation.value = true;
    if (correct) {
      score.value++;
      evaluating.value = false;
      return;
    }
    // Incorrect multiple choice: request backend feedback
    try {
      const responseData = await $authFetch(`/tasks/evaluate_answer/${currentTask.value?.id}`, {
        method: "POST",
        body: { student_answer: currentAnswer.value },
      }) as { feedback: string; };
      feedback.value = responseData.feedback || null;
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : "Failed to evaluate answer.";
      return;
    } finally {
      evaluating.value = false;
    }
  } else {
    // Free text: wait for backend response, use score thresholds
    try {
      const responseData = await $authFetch(`/tasks/evaluate_answer/${currentTask.value?.id}`, {
        method: "POST",
        body: { student_answer: currentAnswer.value },
      }) as { feedback: string; score: number; };
      feedback.value = responseData.feedback || null;
      const scoreNum = responseData.score;
      if (scoreNum > 7) {
        evaluationStatus.value = 'correct';
        isCorrect.value = true;
        score.value++;
      } else if (scoreNum < 4) {
        evaluationStatus.value = 'incorrect';
        isCorrect.value = false;
      } else {
        evaluationStatus.value = 'partial';
        isCorrect.value = false;
      }
      showEvaluation.value = true;
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : "Failed to evaluate answer.";
      return;
    } finally {
      evaluating.value = false;
    }
  }
}

function nextQuestion() {
  if (currentTaskIndex.value < tasks.value.length - 1) {
    currentTaskIndex.value++;
    currentAnswer.value = "";
    isCorrect.value = null;
    showEvaluation.value = false;
    // Hide HTML viewer when moving to next question
    closeHtmlViewer();
  } else {
    pageState.value = "finished";
  }
}

async function showSource() {
  if (!repositoryId.value || !currentTask.value?.chunk_id) {
    console.error("Missing repositoryId or chunk_id:", {
      repositoryId: repositoryId.value,
      chunkId: currentTask.value?.chunk_id,
    });
    return;
  }

  loadingHtml.value = true;
  htmlError.value = "";
  showHtmlViewer.value = true;

  // Collapse sidebar to give more space
  collapsed.value = true;

  try {
    // First, fetch the specific chunk data
    const chunkUrl = `/documents/chunks/${currentTask.value.chunk_id}`;

    const chunkData = await $authFetch(chunkUrl) as { chunk_text: string };

    if (!chunkData.chunk_text) {
      throw new Error("Chunk data not found");
    }

    // For repository-based study, we'll show the chunk text directly
    // since we don't have a specific document to show
    htmlContent.value = `<div class="p-4"><div class="bg-gray-50 p-4 rounded text-lg">${chunkData.chunk_text}</div></div>`;
    highlightedChunkText.value = chunkData.chunk_text;
  } catch (err) {
    console.error("Error fetching chunk content:", err);
    htmlError.value = "Failed to load chunk content";
  } finally {
    loadingHtml.value = false;
  }
}

function closeHtmlViewer() {
  showHtmlViewer.value = false;
  highlightedChunkText.value = "";
}

function restart() {
  pageState.value = "studying";
  repositoryId.value = "";
  tasks.value = [];
  currentTaskIndex.value = 0;
  currentAnswer.value = "";
  showEvaluation.value = false;
  isCorrect.value = null;
  score.value = 0;
  error.value = null;
  feedback.value = null;

  // Reset HTML viewer state
  showHtmlViewer.value = false;
  htmlContent.value = "";
  htmlError.value = "";
  highlightedChunkText.value = "";

  router.push("/repositories");
}
</script>

<template>
  <div class="h-full flex">
    <!-- Left side - Study interface -->
    <div :class="showHtmlViewer ? 'w-1/2 p-4 overflow-y-auto' : 'w-full p-4'">
      <div class="max-w-4xl mx-auto">
        <DPageHeader title="Repository Study Mode" class="mt-4" />
        <div class="mx-auto max-w-2xl">
          <!-- Loading State -->
          <div v-if="loading" class="text-center space-y-4">
            <div class="text-xl">Loading tasks...</div>
          </div>

          <!-- No Tasks State -->
          <div v-else-if="pageState === 'no-tasks'" class="text-center space-y-6">
            <div class="space-y-4">
              <h2 class="text-2xl font-bold">No Tasks Found</h2>
              <p class="text-lg text-gray-600">
                No study tasks have been generated for this repository yet.
              </p>
              <p class="text-gray-500">
                Generate some tasks to start studying this repository.
              </p>
            </div>
            <div class="flex justify-center">
              <DButton @click="openGenerateTasksModal" variant="primary">
                Generate Tasks
              </DButton>
            </div>
          </div>

          <!-- Studying State: Displaying Questions -->
          <div v-else-if="
            pageState === 'studying' && tasks.length > 0 && currentTask
          " class="space-y-2">
            <DTaskAnswer :task="currentTask" :index="currentTaskIndex" v-model="currentAnswer"
              :disabled="showEvaluation || evaluating" :is-evaluated="showEvaluation" :is-correct="isCorrect ?? false"
              @evaluate="evaluateAnswer" />

            <div v-if="showEvaluation">
              <DTaskResult v-if="!isCorrect || currentTask.type === 'free_text'" :task="currentTask"
                :index="currentTaskIndex" :user-answer="currentAnswer" :status="evaluationStatus"
                :feedback="feedback ?? ''" class="mt-4" />
              <div class="flex flex-wrap justify-end gap-2">
                <DButton @click="showSource" variant="secondary" class="mt-4">
                  Show Source
                </DButton>
                <DButton @click="nextQuestion" class="mt-4">
                  {{
                    currentTaskIndex < tasks.length - 1 ? "Next Question" : "Show Results" }} </DButton>
              </div>
              <div v-if="evaluating" class="mt-4 flex justify-center">
                <DSpinner />
              </div>

            </div>
            <div v-else class="flex justify-end items-center min-h-10">
              <template v-if="evaluating">
                <div class="flex items-center gap-2 text-gray-600">
                  <DSpinner size="sm" />
                  <span>Evaluating…</span>
                </div>
              </template>
              <template v-else>
                <DButton @click="evaluateAnswer">Evaluate</DButton>
              </template>
            </div>
          </div>

          <!-- Finished State: Show Score -->
          <div v-else-if="pageState === 'finished'" class="text-center space-y-4">
            <h2 class="text-2xl font-bold">Study Session Complete!</h2>
            <p class="text-lg">
              You scored <span class="font-bold">{{ score }}</span> out of
              <span class="font-bold">{{ tasks.length }}</span>.
            </p>
            <div class="flex justify-center">
              <DButton @click="restart">Study Another Document</DButton>
            </div>
            <div class="text-xs text-gray-500 text-center mt-2">
              Press <kbd class="px-1 py-0.5 bg-gray-100 rounded text-xs">Enter</kbd> to continue
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Right side - HTML viewer -->
    <div v-if="showHtmlViewer" class="w-1/2 border-l border-gray-200">
      <div class="h-full p-4">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-semibold">Source Text</h2>
          <DButton @click="closeHtmlViewer" variant="secondary" class="!p-2">
            Close
          </DButton>
        </div>
        <div class="h-[calc(100%-4rem)]">
          <DHtmlViewer :html-content="htmlContent" :loading="loadingHtml" :error="htmlError"
            :highlighted-chunk-text="highlightedChunkText" />
        </div>
      </div>
    </div>

    <!-- Generate Tasks Modal -->
    <DModal v-if="showGenerateTasksModal" titel="Generate Tasks"
      :confirm-text="generatingTasks ? 'Generating...' : 'Generate'" @close="closeGenerateTasksModal"
      @confirm="confirmGenerateTasks">
      <div class="p-4">
        <label for="num-tasks" class="block mb-2 font-medium">Number of tasks to generate:</label>
        <input id="num-tasks" type="number" min="1" v-model.number="numTasksToGenerate"
          class="border rounded px-2 py-1 w-24" />
      </div>
    </DModal>
  </div>
</template>
