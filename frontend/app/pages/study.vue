<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useSessionStorage, useMediaQuery } from "@vueuse/core";
import type { Task, UnitDetail } from "~/types/models";
import { useNotificationsStore } from "~/stores/notifications";

const route = useRoute();
const { $authFetch } = useAuthenticatedFetch();
const notifications = useNotificationsStore();
const pageState = ref<"studying" | "finished" | "no-tasks">("studying");
const unitId = ref("");
const unitTitle = ref("");
const repositoryId = ref("");
const tasks = ref<Task[]>([]);
const currentTaskIndex = ref(0);
const currentAnswer = ref("");
const showEvaluation = ref(false);
const evaluationStatus = ref<"correct" | "partial" | "incorrect" | "contradictory" | "irrelevant">("incorrect");
const isCorrect = ref<boolean | null>(null);
const score = ref<number>(0);
const loading = ref(false);
const error = ref<string | null>(null);
const feedback = ref<string | null>(null);
const router = useRouter();
const evaluating = ref<boolean>(false);

// Reporting UI state (per-task)
const showTaskReport = ref(false);
const reportOptions = ref({
  too_easy: false,
  too_hard: false,
  not_appropriate: false,
  not_relevant: false,
});
const reportText = ref("");
const reportSubmitting = ref(false);

const currentTask = computed(() => tasks.value[currentTaskIndex.value]);
const tasksDone = computed(() => showEvaluation.value ? currentTaskIndex.value + 1 : currentTaskIndex.value);


// Text viewer state
const showTextViewer = ref(false);
const htmlContent = ref("");
const loadingText = ref(false);
const textError = ref("");


// Sidebar state
const collapsed = useSessionStorage("collapsed", false);

// Detect touch/mobile devices to hide keyboard shortcut hints
const isMobile = useMediaQuery('(hover: none) and (pointer: coarse)');

// Keyboard handler for Enter key
function handleKeyPress(event: KeyboardEvent) {
  // Block navigation while evaluating
  if (evaluating.value) return;
  // Handle Enter key when study session is finished (takes precedence)
  if (event.key === 'Enter' && pageState.value === 'finished') {
    event.preventDefault();
    restart();
  }
  // Handle Enter key when evaluation is shown
  else if (event.key === 'Enter' && showEvaluation.value) {
    event.preventDefault();
    nextQuestion();
  }
  // Hotkey: 'S' to show source when available (after evaluation)
  else if (event.key.toLowerCase() === 's' && showEvaluation.value && currentTask.value?.chunk_id) {
    event.preventDefault();
    showSource();
  }
}

onMounted(() => {
  // Check if unitId or documentId is provided in URL parameters
  const unitIdParam = route.query.unitId as string;
  const docId = route.query.documentId as string;

  if (!unitIdParam && !docId) {
    // No unit or document ID provided, redirect to units page
    notifications.warning("No unit or document selected for study. Please select one from the units page.");
    router.push("/units");
    return;
  }
  currentTask.value?.chunk_id
  startStudy();

  // Note: documentId handling would need to be implemented separately if needed

  // Add keyboard event listener
  document.addEventListener('keydown', handleKeyPress);

  // Analytics: enter study page
  $authFetch('/analytics/pages/study/enter', { 
    method: 'POST', 
    credentials: 'include' 
  }).catch(() => {});
});

onBeforeUnmount(() => {
  // Analytics: leave study page
  $authFetch('/analytics/pages/study/leave', { 
    method: 'POST', 
    credentials: 'include'
  }).catch(() => {});
});


onUnmounted(() => {
  // Clean up keyboard event listener
  document.removeEventListener('keydown', handleKeyPress);
});

async function startStudy() {
  loading.value = true;
  error.value = null;

  try {
    // First, fetch unit details to get the title
    const unitResponse = await $authFetch(`/units/${unitId.value}`) as UnitDetail;
    unitTitle.value = unitResponse.title;
    repositoryId.value = unitResponse.repository_id;

    const responseData = await $authFetch(`/tasks/unit/${unitId.value}/study`) as Task[];
    tasks.value = responseData.length > 0 ? responseData : [];
    pageState.value = tasks.value.length > 0 ? "studying" : "no-tasks";

  } catch (e: any) {
    error.value = e instanceof Error ? e.message : 'Failed to load study session';
  } finally {
    loading.value = false;
  }
}

async function evaluateAnswer() {
  if (!currentAnswer.value?.trim()) {
    error.value = "Please enter an answer.";
    return;
  }

  evaluating.value = true;
  feedback.value = "Evaluating...";
  showEvaluation.value = false;

  try {
  let payload: any = {};

  if (currentTask.value?.type === 'multiple_choice') {
    const selected = currentTask.value.answer_options.find(opt =>
        opt.answer.trim().toLowerCase() === currentAnswer.value.trim().toLowerCase()
      );
    if (!selected) throw new Error("Answer not found in options");
      payload.option_id = selected.id;
    } else {
      payload.text = currentAnswer.value;
    }

  const response = await $authFetch(`/tasks/${currentTask.value?.id}/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }) as {
    result: "CORRECT" | "INCORRECT" | "PARTIAL";
    feedback: string | null;
    score: number | null;
  };

  const { result, feedback: apiFeedback, score: aiScore } = response;
  feedback.value = apiFeedback || "No feedback provided.";

  if (currentTask.value?.type === 'multiple_choice') {
    const correct = result === "CORRECT";
    isCorrect.value = correct;
    evaluationStatus.value = correct ? "correct" : "incorrect";

    if (correct) {
      score.value += 1;
    }
  } else {
    const aiScore = response.score ?? 50;

    if (aiScore >= 90) {
      evaluationStatus.value = "correct";
      isCorrect.value = true;
      score.value += 1;
    } else if (aiScore >= 50) {
      evaluationStatus.value = "partial";
      isCorrect.value = false;
      score.value += 0.5;
    } else if (aiScore >= 20) {
      evaluationStatus.value = "contradictory";
      isCorrect.value = false;
    } else {
      evaluationStatus.value = "irrelevant";
      isCorrect.value = false;
    }
  }

  showEvaluation.value = true;

} catch (e: any) {
  console.error("Evaluation failed:",e);
  error.value = e.message || "Failed to evaluate answer";
} finally {
  evaluating.value = false;
}
}

function nextQuestion() {
  if (currentTaskIndex.value < tasks.value.length - 1) {
    currentTaskIndex.value++;
    currentAnswer.value = "";
    isCorrect.value = null;
    showEvaluation.value = false;
    feedback.value = null;
    // Hide text viewer when moving to next question
    closeTextViewer();
  } else {
    pageState.value = "finished";
    showEvaluation.value = false;
  }
}

async function showSource() {
  if (!unitId.value || !currentTask.value?.chunk_id) {
    console.error("Missing repositoryId or chunk_id:", {
      unitId: unitId.value,
      chunkId: currentTask.value?.chunk_id,
    });
    return;
  }

  loadingText.value = true;
  textError.value = "";
  showTextViewer.value = true;

  // Collapse sidebar to give more space
  collapsed.value = true;

  try {
    // First, fetch the specific chunk data
    const chunk = await $authFetch(`/documents/chunks/${currentTask.value.chunk_id}`) as { chunk_text: string }
    // Convert plain text to HTML (escape HTML and preserve whitespace)
    const escapedText = chunk.chunk_text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');

    htmlContent.value = `<html><head><style>body { font-family: system-ui, -apple-system, sans-serif; padding: 1rem; white-space: pre-wrap; line-height: 1.75; font-size: 0.875rem; background-color: #f9fafb; }</style></head><body>${escapedText}</body></html>`;
  } catch (err) {
    console.error("Error fetching chunk content:", err);
    textError.value = "Failed to load chunk content";
  } finally {
    loadingText.value = false;
  }
}

function closeTextViewer() {
  showTextViewer.value = false;
}

function restart() {
  pageState.value = "studying";
  unitId.value = "";
  unitTitle.value = "";
  tasks.value = [];
  currentTaskIndex.value = 0;
  currentAnswer.value = "";
  showEvaluation.value = false;
  isCorrect.value = null;
  score.value = 0;
  error.value = null;
  feedback.value = null;

  // Reset text viewer state
  showTextViewer.value = false;
  htmlContent.value = "";
  textError.value = "";

  if (repositoryId.value) {
    router.push(`/repository?repositoryId=${repositoryId.value}`);
  }
}

async function submitTaskReport() {
  if (!currentTask.value) return;
  if (reportSubmitting.value) return;
  reportSubmitting.value = true;
  try {
    const tags = Object.entries(reportOptions.value)
      .filter(([_, v]) => v)
      .map(([k]) => k)
      .join(",");

    await $authFetch("/reports/", {
      method: "POST",
      body: {
        report_type: "task",
        url: window.location.href,
        category_tags: tags || null,
        message: reportText.value || null,
        task_id: currentTask.value.id,
        unit_id: unitId.value || null,
      },
    });
    notifications.success("Thanks for the report!");
    showTaskReport.value = false;
    reportOptions.value = {
      too_easy: false,
      too_hard: false,
      not_appropriate: false,
      not_relevant: false,
    };
    reportText.value = "";
  } catch {
    notifications.error("Failed to submit report");
  } finally {
    reportSubmitting.value = false;
  }
}
</script>

<template>
  <div class="h-full flex">
    <!-- Left side - Study interface -->
    <div :class="showTextViewer ? 'w-1/2 overflow-y-auto' : 'w-full'">
      <div class="max-w-4xl mx-auto">
        <DPageHeader :title="unitTitle ? `Studying: ${unitTitle}` : 'Unit Study Mode'" class="mt-4" />
        <div class="mx-auto max-w-4xl">
          <!-- Progress Bar -->
          <div v-if="pageState === 'studying' && tasks.length > 0" class="mt-4 mb-6">
            <DProgressBar :current="tasksDone" :total="tasks.length" />
          </div>
          <!-- Loading State -->
          <div v-if="loading" class="text-center space-y-4">
            <div class="text-xl">Loading tasks...</div>
          </div>

          <!-- No Tasks State -->
          <div v-else-if="pageState === 'no-tasks'" class="text-center space-y-6">
            <div class="space-y-4">
              <h2 class="text-2xl font-bold">No Tasks Found</h2>
              <p class="text-lg text-gray-600">
                No study tasks have been generated for this unit yet.
              </p>
              <p class="text-gray-500">
                Generate some tasks to start studying this unit.
              </p>
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
              <div class="flex flex-wrap justify-between items-center gap-2">
                <div>
                  <DButton variant="secondary" class="mt-4" @click="showTaskReport = true">Report this task</DButton>
                </div>
                <DButton @click="showSource" variant="secondary" class="mt-4">
                  Show Source<span v-if="!isMobile"> (S)</span>
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
                <DButton @click="evaluateAnswer" :disabled="!currentAnswer || currentAnswer.trim() === ''">Evaluate
                </DButton>
              </template>
            </div>
          </div>

          <!-- Finished State: Show Score -->
          <div v-else-if="pageState === 'finished'" class="text-center space-y-4">
            <h2 class="text-2xl font-bold">Study Session Complete!</h2>
            <p class="text-lg">
              You scored <span class="font-bold">{{ score.toFixed(1) }}</span> out of
              <span class="font-bold">{{ tasks.length }}</span>.
            </p>
            <div class="flex justify-center">
              <DButton @click="restart">Study Another Unit</DButton>
            </div>
            <div v-if="!isMobile" class="text-xs text-gray-500 text-center mt-2">
              Press <kbd class="px-1 py-0.5 bg-gray-100 rounded text-xs">Enter</kbd> to continue
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Right side - HTML viewer -->
    <div v-if="showTextViewer" class="relative w-0 md:w-1/2">
      <div class="h-full md:p-4">
        <DHtmlViewer :html-content="htmlContent" :loading="loadingText" :error="textError" @close="closeTextViewer" />
      </div>
    </div>

    <!-- Task Report Sheet/Modal -->
    <div v-if="showTaskReport" class="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      <div class="absolute inset-0 bg-black/40" @click="showTaskReport = false"></div>
      <div class="relative w-full sm:max-w-md bg-white rounded-t-2xl sm:rounded-2xl p-4 sm:p-6 shadow-xl">
        <h3 class="text-lg font-semibold mb-2">Report task issue</h3>
        <div class="grid grid-cols-2 gap-3">
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" v-model="reportOptions.too_easy" /> Too easy
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" v-model="reportOptions.too_hard" /> Too hard
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" v-model="reportOptions.not_appropriate" /> Not appropriate
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" v-model="reportOptions.not_relevant" /> Not relevant
          </label>
        </div>
        <textarea v-model="reportText" rows="3"
          class="mt-3 w-full rounded border border-gray-300 p-2 focus:ring-2 focus:ring-red-300"
          placeholder="Optional details" />
        <div class="mt-4 flex justify-end gap-2">
          <DButton variant="secondary" @click="showTaskReport = false">Cancel</DButton>
          <DButton :disabled="reportSubmitting" @click="submitTaskReport">Submit</DButton>
        </div>
      </div>
    </div>
  </div>
</template>
