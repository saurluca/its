<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from "vue";
import { PlusIcon } from "lucide-vue-next";
import type { Task, Repository, Unit, Document as ApiDocument } from "~/types/models";
import { useNotificationsStore } from "~/stores/notifications";

const { $authFetch } = useAuthenticatedFetch();

const tasks = ref<Task[]>([]);
const loading = ref(true);
const repositoriesList = ref<Repository[]>([]);
const unitsList = ref<Unit[]>([]);
const documentsList = ref<{ value: string; label: string }[]>([]);
const notifications = useNotificationsStore();

type AccessLevel = 'read' | 'write' | 'owner';

function hasWriteAccess(repo: Repository & { access_level?: AccessLevel }) {
  const level = repo.access_level as AccessLevel | undefined;
  return level === 'write' || level === 'owner';
}

// Keep repo list for generation modal context; compute when needed to avoid unused var
const _writableRepositories = computed<Repository[]>(() =>
  (repositoriesList.value || []).filter((r) => hasWriteAccess(r as Repository & { access_level?: AccessLevel }))
);

// Units available to the user (already access-filtered by backend)
const availableUnits = computed<Unit[]>(() => unitsList.value || []);

// Generate tasks modal state (reusable)
const showGenerateTasksModal = ref(false);
const selectedUnit = computed<Unit | null>(() => {
  return availableUnits.value.find(u => u.id === selectedUnitId.value) || null;
});
const selectedRepositoryForTasks = computed<Repository | null>(() => {
  const unit = selectedUnit.value;
  if (!unit) return null;
  const repo = repositoriesList.value.find(r => r.id === unit.repository_id);
  return repo || null;
});
function openGenerateTasksModalFromTasks() {
  if (!selectedRepositoryForTasks.value) {
    notifications.warning("Please select a unit first.");
    return;
  }
  showGenerateTasksModal.value = true;
}
function closeGenerateTasksModalFromTasks() {
  showGenerateTasksModal.value = false;
}
async function onGenerateTasksConfirm(params: {
  documentIds: string[];
  numTasks: number;
  taskType: "multiple_choice" | "free_text";
}) {
  console.log("Starting task generation in background");

  // Close modal immediately
  showGenerateTasksModal.value = false;

  const repository = selectedRepositoryForTasks.value;
  if (!repository || !selectedUnitId.value) return;

  const repositoryName = repository.name;
  const taskTypeText = params.taskType === "multiple_choice" ? "multiple choice" : "free text";
  const processingId = notifications.loading(
    `Generating ${params.numTasks} ${taskTypeText} tasks for "${repositoryName}" from ${params.documentIds.length} document${params.documentIds.length === 1 ? "" : "s"}. This may take a while.`
  );

  try {
    const createdTasks = await $authFetch("/tasks/generate_for_documents", {
      method: "POST",
      body: {
        unit_id: selectedUnitId.value,
        document_ids: params.documentIds,
        num_tasks: params.numTasks,
        task_type: params.taskType,
      },
    }) as Task[];

    notifications.remove(processingId);
    notifications.success(`Successfully generated ${params.numTasks} ${taskTypeText} tasks for "${repositoryName}"!`);

    // Add the created tasks to the list
    if (Array.isArray(createdTasks) && createdTasks.length > 0) {
      const normalized = createdTasks.map((task: Task) => ({
        ...task,
        created_at: new Date(task.created_at),
        updated_at: new Date(task.updated_at),
        answer_options: task.answer_options || [],
      })) as Task[];
      tasks.value = [...normalized, ...tasks.value];
      console.log("tasks", tasks.value);
    } else {
      // Fallback: refetch tasks if no tasks returned
      if (selectedUnitId.value) await fetchTasksByUnit(selectedUnitId.value);
      else await fetchAllTasks();
    }
  } catch (error) {
    console.error("Error generating tasks:", error);
    notifications.remove(processingId);
    notifications.error(`Failed to generate tasks for "${repositoryName}". Please try again. ${error}`);
  }
}

// For filtering tasks
const selectedUnitId = ref<string>("");
const selectedDocumentId = ref<string>("");
const filterType = ref<"unit" | "document">("unit");

// Try task state
const previewingTask = ref<Task | null>(null);
const currentAnswer = ref("");
const showEvaluation = ref(false);
const evaluationStatus = ref<"correct" | "partial" | "incorrect" | "contradictory" | "irrelevant">("incorrect");
const isCorrect = ref<boolean | null>(null);
const evaluating = ref<boolean>(false);
const feedback = ref<string | null>(null);

// Get document ID or unit ID from route query if present
const route = useRoute();
const router = useRouter();
const documentIdFromRoute = route.query.documentId as string;
const unitIdFromRoute = route.query.unitId as string;

// Initialize filter from route if present
if (documentIdFromRoute) {
  selectedDocumentId.value = documentIdFromRoute;
  filterType.value = "document";
} else if (unitIdFromRoute) {
  selectedUnitId.value = unitIdFromRoute;
  filterType.value = "unit";
}

// tasks are already filtered by the backend
const filteredTasks = computed(() => tasks.value);


// Function to fetch all tasks
async function fetchAllTasks() {
  try {
    const response = await $authFetch("/tasks") as Task[];
    tasks.value = response.map((task: Task) => ({
      ...task,
      id: task.id,
      type: task.type,
      question: task.question,
      answer_options: task.answer_options || [],
      repository_id: task.repository_id || "",
      document_id: task.document_id || "",
      chunk_id: task.chunk_id || "",
      created_at: new Date(task.created_at),
      updated_at: new Date(task.updated_at),
    })) as Task[];
  } catch (error) {
    console.error("Error fetching all tasks:", error);
  }
}

// Fetch tasks on page load
onMounted(async () => {
  loading.value = true;
  try {
    const [tasksResponse, repositoriesResponse, unitsResponse, documentsResponse] =
      await Promise.all([
        $authFetch("/tasks"),
        $authFetch("/repositories"),
        $authFetch("/units"),
        $authFetch("/documents"),
      ]) as [Task[], { repositories?: Repository[] } | Repository[], Unit[], ApiDocument[]];

    // Default to all tasks; may be overridden by route-based filtering below
    tasks.value = (tasksResponse || []).map((task: Task) => ({
      ...task,
      id: task.id,
      type: task.type,
      question: task.question,
      answer_options: task.answer_options || [],
      repository_id: task.repository_id || "",
      document_id: task.document_id || "",
      chunk_id: task.chunk_id || "",
      created_at: new Date(task.created_at),
      updated_at: new Date(task.updated_at),
    })) as Task[];

    repositoriesList.value = ('repositories' in repositoriesResponse ? repositoriesResponse.repositories : repositoriesResponse) as Repository[];
    unitsList.value = (unitsResponse || []) as Unit[];

    // Process documents for dropdown
    if (documentsResponse && Array.isArray(documentsResponse)) {
      documentsList.value = documentsResponse.map((doc: ApiDocument) => ({
        value: doc.id,
        label: doc.title,
      }));
    }

    // Apply route-based filtering on initial load
    if (documentIdFromRoute) {
      await fetchTasksByDocument(documentIdFromRoute);
    } else if (unitIdFromRoute) {
      await fetchTasksByUnit(unitIdFromRoute);
    } else {
      // Default to first available unit if none selected
      const firstUnitId = availableUnits.value[0]?.id;
      if (firstUnitId) {
        selectedUnitId.value = firstUnitId;
        await router.replace({ query: { ...route.query, unitId: firstUnitId } });
        await fetchTasksByUnit(firstUnitId);
      }
    }
  } catch (error) {
    console.error("Error fetching data:", error);
  } finally {
    loading.value = false;
  }
});

// Add keyboard event listener when component is mounted
onMounted(() => {
  document.addEventListener('keydown', handleKeydown);
});


onMounted(() => {
  $authFetch('/analytics/pages/tasks/enter', {
    method: 'POST',
    credentials: 'include',
  }).catch(() => {})
})

onBeforeUnmount(() => {
  $authFetch('/analytics/pages/tasks/leave', {
    method: 'POST',
    credentials: 'include',
  }).catch(() => {})
})

// Remove keyboard event listener when component is unmounted
onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown);
});

// Function to fetch tasks by document
async function fetchTasksByDocument(documentId: string) {
  try {
    const response = await $authFetch(`/tasks/document/${documentId}`) as Task[];
    tasks.value = response.map((task: Task) => ({
      ...task,
      id: task.id,
      type: task.type,
      question: task.question,
      answer_options: task.answer_options || [],
      repository_id: task.repository_id || "",
      document_id: task.document_id || "",
      chunk_id: task.chunk_id || "",
      created_at: new Date(task.created_at),
      updated_at: new Date(task.updated_at),
    })) as Task[];
  } catch (error) {
    console.error("Error fetching tasks by document:", error);
  }
}

// Function to fetch tasks by unit
async function fetchTasksByUnit(unitId: string) {
  try {
    const response = await $authFetch(`/tasks/unit/${unitId}`) as Task[];
    tasks.value = response.map((task: Task) => ({
      ...task,
      id: task.id,
      type: task.type,
      question: task.question,
      answer_options: task.answer_options || [],
      repository_id: task.repository_id || "",
      document_id: task.document_id || "",
      chunk_id: task.chunk_id || "",
      created_at: new Date(task.created_at),
      updated_at: new Date(task.updated_at),
    })) as Task[];
  } catch (error) {
    console.error("Error fetching tasks by unit:", error);
  }
}

// Watch for filter changes and fetch tasks accordingly
watch(selectedDocumentId, (newValue) => {
  if (filterType.value !== "document") return;
  if (newValue) {
    fetchTasksByDocument(newValue);
  } else {
    fetchAllTasks();
  }
});

watch(selectedUnitId, async (newValue) => {
  if (filterType.value !== "unit") return;
  if (newValue) {
    await router.replace({ query: { ...route.query, unitId: newValue } });
    fetchTasksByUnit(newValue);
  } else {
    const fallback = availableUnits.value[0]?.id;
    if (fallback) {
      selectedUnitId.value = fallback;
      await router.replace({ query: { ...route.query, unitId: fallback } });
    }
  }
});

async function deleteTask(id: string) {
  try {
    await $authFetch(`/tasks/${id}`, {
      method: "DELETE",
    });

    tasks.value = tasks.value.filter((t) => t.id !== id);
  } catch (error) {
    console.error("Error deleting task:", error);
    notifications.error("Failed to delete task. Please try again.");
  }
}


function handleUpdateTask(updatedTask: Task) {
  const index = tasks.value.findIndex((t) => t.id === updatedTask.id);
  if (index !== -1) {
    tasks.value[index] = {
      ...updatedTask,
      updated_at: new Date(),
    };
  }
}

// Preview task functions
function startPreviewingTask(task: Task) {
  previewingTask.value = task;
  currentAnswer.value = "";
  showEvaluation.value = false;
  isCorrect.value = null;
  evaluationStatus.value = "incorrect";
  feedback.value = null;
}

// Handle keyboard events for modal
function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && previewingTask.value) {
    closeTryTask();
  }
}

// Removed polling; tasks are returned by the backend and injected immediately

async function evaluateAnswer() {
  if (!previewingTask.value || !currentAnswer.value?.trim()) {
    notifications.error("Please enter an answer.");
    return;
  }

  feedback.value = "Evaluating...";
  evaluating.value = true;
  showEvaluation.value = false;

  try {
    let payload: any = {};

    if (previewingTask.value.type === 'multiple_choice') {
      const selectedOption = previewingTask.value.answer_options.find(
        opt => opt.answer === currentAnswer.value
      );
      if (!selectedOption) {
        notifications.error("Invalid answer selected.");
        return;
      }
      payload.option_id = selectedOption.id;
    } else {
      payload.text = currentAnswer.value;
    }

    const response = await $authFetch(`/tasks/${previewingTask.value.id}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }) as {
      result: "CORRECT" | "INCORRECT" | "PARTIAL";
      score?: number;
      feedback?: string;
    };

    // Map result
    isCorrect.value = response.result === "CORRECT";
    evaluationStatus.value = response.result === "CORRECT" ? "correct" :
                             response.result === "PARTIAL" ? "partial" :
                             "incorrect";

    feedback.value = response.feedback || "No feedback.";
    showEvaluation.value = true;

  } catch (e: any) {
    console.error("Answer submission failed:", e);
    notifications.error(e.message || "Failed to submit answer.");
    feedback.value = "Error.";
  } finally {
    evaluating.value = false;
  }
}

function closeTryTask() {
  previewingTask.value = null;
  currentAnswer.value = "";
  showEvaluation.value = false;
  isCorrect.value = null;
  evaluationStatus.value = "incorrect";
  feedback.value = null;
  evaluating.value = false;
}
</script>

<template>
  <div class="h-full max-w-4xl mx-auto mt-8">
    <DPageHeader title="Tasks" />
    <div class="bg-white p-6 rounded-lg shadow mb-4">
      <h2 class="text-xl font-bold mb-4">Unit Filter</h2>

      <div v-if="filterType === 'unit'">
        <DSearchableDropdown v-model="selectedUnitId"
          :options="availableUnits.map((unit) => ({ value: unit.id, label: unit.title }))" placeholder="Select a unit"
          search-placeholder="Search units..." class="mt-1 w-full" />
      </div>
    </div>

    <div v-if="filteredTasks.length > 0" class="flex justify-start mb-4">
      <DButtonLabelled title="Generate Tasks" :icon="PlusIcon" @click="openGenerateTasksModalFromTasks">
        Generate multiple choice or free text tasks for the current unit.
      </DButtonLabelled>
    </div>

    <div v-if="loading" class="py-20 text-center">
      <div class="text-xl">Loading tasks...</div>
    </div>

    <div v-else-if="filteredTasks.length === 0" class="bg-white p-6 rounded-lg shadow text-center mt-4">
      <p class="text-gray-500">
        No tasks available for the selected unit.
      </p>
      <div class="flex justify-center mt-2">
        <DButton variant="primary" @click="openGenerateTasksModalFromTasks" :icon-left="PlusIcon">
          Generate Tasks
        </DButton>
      </div>
    </div>

    <div v-else class="space-y-6 my-4">
      <DTaskCard v-for="task in filteredTasks" :key="task.id" :task="task" @delete="deleteTask"
        @update="handleUpdateTask" @preview-task="startPreviewingTask" />
    </div>

    <!-- Test Task Modal/Overlay -->
    <div v-if="previewingTask" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="rounded-lg bg-white max-w-[942px] w-full max-h-[90vh]  p-6">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-bold">Task Preview</h2>
          <button @click="closeTryTask" class="text-gray-500 hover:text-gray-700">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>

        <!-- Task Display -->
        <div class="space-y-4">
          <DTaskAnswer :task="previewingTask" :index="0" v-model="currentAnswer"
            :disabled="showEvaluation || evaluating" :is-evaluated="showEvaluation" :is-correct="isCorrect ?? false"
            @evaluate="evaluateAnswer" />

          <!-- Evaluation Results -->
          <div v-if="showEvaluation">
            <DTaskResult v-if="!isCorrect || previewingTask.type === 'free_text'" :task="previewingTask" :index="0"
              :user-answer="currentAnswer" :status="evaluationStatus" :feedback="feedback ?? ''" class="mt-2" />
            <div class="flex justify-end gap-2 mt-2">
              <DButton @click="closeTryTask" variant="secondary">
                Close
              </DButton>
            </div>
          </div>

          <!-- Evaluate Button -->
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
      </div>
    </div>
    <!-- Generate Tasks Modal (DRY reusable component) -->
    <DGenerateTasksModal v-if="showGenerateTasksModal" :repository="selectedRepositoryForTasks"
      :unit-id="selectedUnitId" @close="closeGenerateTasksModalFromTasks" @confirm="onGenerateTasksConfirm" />
  </div>
</template>
