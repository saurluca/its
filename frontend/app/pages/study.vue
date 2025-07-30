<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useSessionStorage } from "@vueuse/core";
import type { Task } from "~/types/models";

const route = useRoute();
const pageState = ref<"studying" | "finished" | "no-tasks">("studying");
const fileId = ref("");
const tasks = ref<Task[]>([]);
const currentTaskIndex = ref(0);
const currentAnswer = ref("");
const showEvaluation = ref(false);
const isCorrect = ref<boolean | null>(null);
const score = ref(0);
const loading = ref(false);
const error = ref<string | null>(null);
const feedback = ref<string | null>(null);
const router = useRouter();
const runtimeConfig = useRuntimeConfig();
const apiUrl = runtimeConfig.public.apiBase;

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

onMounted(() => {
  // Check if documentId is provided in URL parameters
  const documentId = route.query.documentId as string;
  if (documentId) {
    fileId.value = documentId;
    startStudy();
  }
});

async function startStudy() {
  if (!fileId.value) {
    error.value = "Please enter a Document ID.";
    return;
  }
  loading.value = true;
  error.value = null;

  try {
    const { data: responseData, error: fetchError } = await useFetch<{
      tasks: Task[];
    }>(`${apiUrl}/tasks/document/${fileId.value}`);

    if (fetchError.value) {
      throw new Error(
        fetchError.value.data?.message || "Failed to load tasks.",
      );
    }

    const fetchedTasks = responseData.value?.tasks;

    if (fetchedTasks && fetchedTasks.length > 0) {
      tasks.value = fetchedTasks;
      console.log("Loaded tasks:", fetchedTasks.length, fetchedTasks);
      console.log("First task structure:", fetchedTasks[0]);
      pageState.value = "studying";
    } else {
      pageState.value = "no-tasks";
    }
  } catch (e: any) {
    error.value = e.message;
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
  if (!fileId.value) return;
  generatingTasks.value = true;
  try {
    // Call the API to generate tasks
    await fetch(
      `${apiUrl}/tasks/generate/${fileId.value}/?num_tasks=${numTasksToGenerate.value}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      },
    );
    closeGenerateTasksModal();
    // Reload the page to start the study session
    await startStudy();
  } catch (err: any) {
    error.value = "Failed to generate tasks. Please try again. " + err;
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

  const correct = currentAnswer.value === currentTask.value?.correct_answer;
  isCorrect.value = correct;

  showEvaluation.value = true;

  if (correct) {
    score.value++;
  } else {
    const { data: responseData, error: fetchError } = await useFetch<{
      feedback: string;
    }>(`${apiUrl}/tasks/evaluate_answer/${currentTask.value?.id}`, {
      method: "POST",
      body: {
        student_answer: currentAnswer.value,
      },
    });

    if (fetchError.value) {
      error.value =
        fetchError.value.data?.message || "Failed to evaluate answer.";
      return;
    }
    feedback.value = responseData.value?.feedback || null;
  }
}

function nextQuestion() {
  console.log(
    "Next question called. Current index:",
    currentTaskIndex.value,
    "Total tasks:",
    tasks.value.length,
  );
  if (currentTaskIndex.value < tasks.value.length - 1) {
    currentTaskIndex.value++;
    currentAnswer.value = "";
    isCorrect.value = null;
    showEvaluation.value = false;
    // Hide HTML viewer when moving to next question
    closeHtmlViewer();
    console.log("Moving to question:", currentTaskIndex.value + 1);
  } else {
    console.log("Study session finished");
    pageState.value = "finished";
  }
}

async function showSource() {
  console.log("Showing source for chunk:", currentTask.value?.chunk_id);
  console.log("Current task:", currentTask.value);
  console.log("File ID:", fileId.value);

  if (!fileId.value || !currentTask.value?.chunk_id) {
    console.error("Missing fileId or chunk_id:", { fileId: fileId.value, chunkId: currentTask.value?.chunk_id });
    return;
  }

  loadingHtml.value = true;
  htmlError.value = "";
  showHtmlViewer.value = true;

  // Collapse sidebar to give more space
  collapsed.value = true;

  try {
    // First, fetch the specific chunk data
    const chunkUrl = `${apiUrl}/documents/chunks/${currentTask.value.chunk_id}`;
    console.log("Fetching chunk from:", chunkUrl);

    const chunkResponse = await fetch(chunkUrl);

    if (!chunkResponse.ok) {
      const errorData = await chunkResponse.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to fetch chunk: ${chunkResponse.status}`);
    }

    const chunkData = await chunkResponse.json();
    console.log("Chunk data received:", chunkData);

    if (!chunkData.chunk_text) {
      throw new Error("Chunk data not found");
    }

    // Then fetch the full document content
    const response = await fetch(`${apiUrl}/documents/${fileId.value}/`);
    const data = await response.json();

    if (data.content) {
      htmlContent.value = data.content;
      // Pass chunk data to the HTML viewer for highlighting
      highlightedChunkText.value = chunkData.chunk_text;
    } else {
      htmlError.value = "Document content not found";
    }
  } catch (err) {
    console.error("Error fetching document content:", err);
    htmlError.value = "Failed to load document content";
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
  fileId.value = "";
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

  router.push("/documents");
}
</script>

<template>
  <div class="h-full flex">
    <!-- Study content - centered when no HTML viewer, left-aligned when HTML viewer is shown -->
    <div :class="showHtmlViewer ? 'w-1/2 p-6 overflow-y-auto' : 'w-full flex justify-center px-6'">
      <div :class="showHtmlViewer ? 'max-w-4xl mx-auto' : 'max-w-2xl w-full'">

        <DPageHeader title="Study Mode" class="mt-4" />
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
                No study tasks have been generated for this document yet.
              </p>
              <p class="text-gray-500">
                Generate some tasks to start studying this document.
              </p>
            </div>
            <div class="flex justify-center">
              <DButton @click="openGenerateTasksModal" variant="primary">
                Generate Tasks
              </DButton>
            </div>
          </div>

          <!-- Studying State: Displaying Questions -->
          <div v-else-if="pageState === 'studying' && tasks.length > 0 && currentTask" class="space-y-2">
            <DTaskAnswer :task="currentTask" :index="currentTaskIndex" v-model="currentAnswer"
              :disabled="showEvaluation" />

            <div v-if="showEvaluation">
              <DTaskResult :task="currentTask" :index="currentTaskIndex" :userAnswer="currentAnswer"
                :isCorrect="isCorrect ?? false" :feedback="feedback ?? ''" class="mt-4" />
              <div class="flex flex-wrap justify-end gap-2">
                <DButton @click="showSource" variant="secondary" class="mt-4">
                  Show Source
                </DButton>
                <DButton @click="nextQuestion" class="mt-4">
                  {{
                    currentTaskIndex < tasks.length - 1 ? "Next Question" : "Show Results" }} </DButton>
              </div>
            </div>
            <div v-else class="flex justify-end">
              <DButton @click="evaluateAnswer">Evaluate</DButton>
            </div>
          </div>

          <!-- Finished State: Show Score -->
          <div v-else-if="pageState === 'finished'" class="text-center space-y-4">
            <h2 class="text-2xl font-bold">Study Session Complete!</h2>
            <p class="text-lg">
              You scored <span class="font-bold">{{ score }}</span> out of
              <span class="font-bold">{{ tasks.length }}</span>.
            </p>
            <DButton @click="restart">Study Another Document</DButton>
          </div>
        </div>
      </div>
    </div>

    <!-- Right side - HTML viewer -->
    <div v-if="showHtmlViewer" class="w-1/2 border-l border-gray-200">
      <div class="h-full p-4">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-semibold">Document Source</h2>
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
  </div>

  <!-- Generate Tasks Modal -->
  <DModal v-if="showGenerateTasksModal" titel="Generate Tasks"
    :confirmText="generatingTasks ? 'Generating...' : 'Generate'" @close="closeGenerateTasksModal"
    @confirm="confirmGenerateTasks">
    <div class="p-4">
      <label for="num-tasks" class="block mb-2 font-medium">Number of tasks to generate:</label>
      <input id="num-tasks" type="number" min="1" v-model.number="numTasksToGenerate"
        class="border rounded px-2 py-1 w-24" />
    </div>
  </DModal>
</template>
