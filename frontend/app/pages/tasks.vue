<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from "vue";
import { PlusIcon, EyeIcon, EyeOffIcon} from "lucide-vue-next";
import type { Task, Repository, Unit, Document as ApiDocument } from "~/types/models";
import { useNotificationsStore } from "~/stores/notifications";
import {useLocalStorage} from "@vueuse/core";

const { $authFetch } = useAuthenticatedFetch();

const tasks = ref<Task[]>([]);
const loading = ref(true);
const repositoriesList = ref<Repository[]>([]);
const unitsList = ref<Unit[]>([]);
const documentsList = ref<{ value: string; label: string }[]>([]);
const notifications = useNotificationsStore();

type AccessLevel = 'read' | 'write' | 'owner';

// ---------------------- Visibility -------------------------

// Feature flag for unit visibility toggle
const UNIT_VISIBILITY_FEATURE_ENABLED = false; // Set to false to disable the feature, true to enable

// Add unit visibility state 
const visibleUnits = useLocalStorage<Set<string>>("repository_visible_units", new Set());

// Add a new ref to track tasks by unit for counting purposes
const tasksByUnit = ref<Record<string, Task[]>>({});

// Toggle individual unit visibility
const toggleUnitVisibility = (unitId: string) => {
  const newVisible = new Set(visibleUnits.value);
  if (newVisible.has(unitId)) {
    newVisible.delete(unitId);
  } else {
    newVisible.add(unitId);
  }
  visibleUnits.value = newVisible;
};

// Check if a specific unit is visible
const isUnitVisible = (unitId: string) => {
  return visibleUnits.value.has(unitId);
};

// Show/hide all units
const showAllUnits = () => {
  const allUnitIds = new Set(availableUnits.value.map(unit => unit.id));
  visibleUnits.value = allUnitIds;
};

const hideAllUnits = () => {
  visibleUnits.value = new Set();
};

// Filter available units based on visibility
const visibleAvailableUnits = computed(() => {
  if (!UNIT_VISIBILITY_FEATURE_ENABLED) {
    return availableUnits.value; // Show all units when feature is disabled
  }
  return availableUnits.value.filter(unit => isUnitVisible(unit.id));
});

// ---------------------- Utility -------------------------

// Utility functions
const getTaskTypeLabel = (type: string): string => 
  type === "multiple_choice" ? "multiple choice" : "free text";

function hasWriteAccess(repo: Repository & { access_level?: AccessLevel }) {
  const level = repo.access_level as AccessLevel | undefined;
  return level === 'write' || level === 'owner';
}

// Helper function for development logging
const devLog = (message: string, ...args: any[]) => {
  if (import.meta.env.DEV) {
    console.log(message, ...args);
  }
};

// Helper: Track tasks by ID to avoid race conditions
function getTaskIds(taskList: Task[]): Set<string> {
  return new Set(taskList.map(t => t.id));
}

// Helper function to normalize task data
const normalizeTask = (task: Task): Task => ({
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
});

// Helper function to merge tasks without duplicates
const mergeTasksWithoutDuplicates = (existingTasks: Task[], newTasks: Task[]): Task[] => {
  const existingIds = new Set(existingTasks.map(t => t.id));
  const uniqueNewTasks = newTasks.filter(t => !existingIds.has(t.id));
  return [...uniqueNewTasks, ...existingTasks];
};

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
  devLog("Starting task generation in background");

  // Close modal immediately
  showGenerateTasksModal.value = false;

  const repository = selectedRepositoryForTasks.value;
  if (!repository || !selectedUnitId.value) {
    notifications.error("No repository or unit selected.")
    return;
  }

  const repositoryName = repository.name;
  const taskTypeText = getTaskTypeLabel(params.taskType);
  const processingId = notifications.loading(
    `Generating ${params.numTasks} ${taskTypeText} tasks for "${repositoryName}" from ${params.documentIds.length} document${params.documentIds.length === 1 ? "" : "s"}. This may take a while.`
  );

  try {
    // Capture initial state BEFORE API call
    const initialTaskIds = getTaskIds(tasks.value);
    const generationStartTime = new Date();
    
    devLog("Generation started", {
      initialTaskCount: initialTaskIds.size,
      timestamp: generationStartTime.toISOString(),
      params
    });

    //Retry logic for network issues
    const maxRetries = 2;
    let response;

    for (let retry = 0; retry <= maxRetries; retry++) {
      try {
        response = await $authFetch("/tasks/generate_for_documents", {
          method: "POST",
          body: {
            unit_id: selectedUnitId.value,
            document_ids: params.documentIds,
            num_tasks: params.numTasks,
            task_type: params.taskType,
          },
        });
        break; // Success, exit retry loop
      } catch (error) {
        if (retry === maxRetries) throw error;
        await new Promise(r => setTimeout(r, 1000 * (retry + 1)));
        devLog(`Retry ${retry + 1} for task generation`);
      }
    }
    
    notifications.remove(processingId);

    const createdTasks = await handleTaskGenerationResponse(
      response,
      selectedUnitId.value,
      initialTaskIds,
      generationStartTime
    );

    if (createdTasks.length > 0) {
      // Prevent duplicates
      const existingIds = getTaskIds(tasks.value);
      const uniqueNewTasks = createdTasks.filter(t => !existingIds.has(t.id));
      
      if (uniqueNewTasks.length > 0) {
        const normalized = uniqueNewTasks.map(normalizeTask);
        tasks.value = mergeTasksWithoutDuplicates(tasks.value, normalized);
        
        notifications.success(
          `Successfully generated ${uniqueNewTasks.length} ${taskTypeText} tasks for "${repositoryName}"!`
        );
        
        devLog(`Added ${uniqueNewTasks.length} unique tasks. Total: ${tasks.value.length}`);
      } else {
        devLog("All tasks were duplicates, skipped adding");
        notifications.warning("Tasks already exist in list");
      }
    } else {
      // If no tasks returned, refetch from server
      await fetchTasksByUnit(selectedUnitId.value);
      const newTaskIds = getTaskIds(tasks.value);
      const newTasksCount = [...newTaskIds].filter(id => !initialTaskIds.has(id)).length;
      
      if (newTasksCount > 0) {
        notifications.success(`Task generation completed. Found ${newTasksCount} new tasks for this unit.`);
      } else {
        notifications.warning("Task generation completed but no new tasks were found.");
      }
    }

  } catch (error) {
    console.error("Error generating tasks:", error);
    notifications.remove(processingId);
    
    // Always try to refetch to show current state
    try {
      await fetchTasksByUnit(selectedUnitId.value);
      notifications.warning(
        `Task generation encountered an issue, but ${tasks.value.length} tasks are available.`
      );
    } catch (refetchError) {
      notifications.error(
        `Failed to generate tasks for "${repositoryName}". Please refresh the page.`
      );
    }
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
const filteredTasks = computed(() => {
  // If feature is disabled, show all tasks for selected unit or all units if none selected
  if (!UNIT_VISIBILITY_FEATURE_ENABLED) {
    if (!selectedUnitId.value) {
      // Show all tasks if no unit is selected
      return tasks.value;
    }
    // Show tasks for selected unit
    return tasks.value;
  }
  
  // If no unit is selected, show tasks from all visible units
  if (!selectedUnitId.value) {
    const visibleUnitIds = new Set(visibleAvailableUnits.value.map(unit => unit.id));
    let allTasks: Task[] = [];
    
    // Collect tasks from all visible units
    for (const unitId of visibleUnitIds) {
      if (tasksByUnit.value[unitId]) {
        allTasks = [...allTasks, ...tasksByUnit.value[unitId]];
      }
    }
    
    return allTasks;
  }
  
  // If a specific unit is selected, only show its tasks if the unit is visible
  const isSelectedUnitVisible = isUnitVisible(selectedUnitId.value);
  return isSelectedUnitVisible ? tasks.value : [];
});


// Function to fetch all tasks
async function fetchAllTasks() {
  try {
    const response = await $authFetch("/tasks") as Task[];
    tasks.value = response.map(normalizeTask);
  } catch (error) {
    console.error("Error fetching all tasks:", error);
  }
}

// Fetch tasks on page load, also function populates tasksByUnit for all units
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
    tasks.value = (tasksResponse || []).map(normalizeTask);

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
    
    // Fetch tasks for all units to populate tasksByUnit
    for (const unit of availableUnits.value) {
      if (unit.id) {
        await fetchTasksByUnit(unit.id);
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

// Remove keyboard event listener when component is unmounted
onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown);
});

// Function to fetch tasks by document
async function fetchTasksByDocument(documentId: string) {
  try {
    const response = await $authFetch(`/tasks/document/${documentId}`) as Task[];
    tasks.value = response.map(normalizeTask);
  } catch (error) {
    console.error("Error fetching tasks by document:", error);
  }
}
// Main response handler for different backend patterns
async function handleTaskGenerationResponse(
  response: any,
  unitId: string,
  initialTaskIds: Set<string>,
  generationStartTime: Date
): Promise<Task[]> {
  devLog("=== TASK GENERATION RESPONSE ===");
  devLog("Type:", typeof response);
  devLog("Is Array:", Array.isArray(response));
  
  if (response && typeof response === 'object') {
    devLog("Keys:", Object.keys(response));
    devLog("Full response:", JSON.stringify(response, null, 2));
  }
  devLog("================================");

  // Case 1: Direct array of tasks
  if (Array.isArray(response)) {
    if (response.length > 0) {
      devLog("Case 1: Direct array of tasks");
      return response;
    } else {
      // Empty array - this indicates an issue with task generation
      devLog("Case 1: Empty array returned, checking if tasks were created");
      
      // Wait a bit and then poll to see if tasks appear
      await new Promise(resolve => setTimeout(resolve, 2000));
      const currentTasks = await fetchTasksByUnit(unitId, true);
      const newTasks = currentTasks.filter(task => !initialTaskIds.has(task.id));
      
      if (newTasks.length > 0) {
        devLog(`Found ${newTasks.length} tasks after delay`);
        return newTasks;
      } else {
        devLog("No tasks found after delay, backend likely failed to generate tasks");
        return [];
      }
    }
  }

  // Case 2: Wrapped in { tasks: [...] }
  if (response?.tasks && Array.isArray(response.tasks)) {
    devLog("Case 2: Wrapped tasks array");
    return response.tasks;
  }

  // Case 3: Task IDs returned
  if (response?.task_ids && Array.isArray(response.task_ids)) {
    devLog("Case 3: Task IDs array", response.task_ids);
    return await fetchTasksByIds(response.task_ids);
  }

  // Case 4: Background job indicators
  const asyncIndicators = [
    response?.status === 202,
    response?.status === "processing",
    response?.status === "queued",
    response?.status === "accepted",
    response?.message?.toLowerCase().includes("background"),
    response?.message?.toLowerCase().includes("queued"),
    response?.job_id !== undefined,
    response?.task_id !== undefined
  ];

  if (asyncIndicators.some(Boolean)) {
    devLog("Case 4: Background job detected");
    return await pollForGeneratedTasks(unitId, initialTaskIds, generationStartTime);
  }

  // Case 5: Unknown format - poll anyway
  devLog("Case 5: Unknown response format, defaulting to poll");
  console.warn("Unexpected response format:", response);
  return await pollForGeneratedTasks(unitId, initialTaskIds, generationStartTime);
}

// Polling with timeout and exponential backoff
async function pollForGeneratedTasks(
  unitId: string,
  initialTaskIds: Set<string>, // Changed from count to IDs
  generationStartTime: Date,
  maxAttempts = 30,
  initialIntervalMs = 2000
): Promise<Task[]> {
  const startTime = Date.now();
  const maxDuration = 300000; // 5 minutes
  
  devLog(`Starting polling for unit ${unitId}, tracking ${initialTaskIds.size} initial tasks`);

  // Small initial delay to allow DB commit
  await new Promise(resolve => setTimeout(resolve, 1000));

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    if (Date.now() - startTime > maxDuration) {
      console.warn("Polling timeout reached after 5 minutes");
      break;
    }

    // Exponential backoff WITH jitter
    const delay = Math.min(initialIntervalMs * Math.pow(1.5, attempt), 10000);
    const jitter = Math.random() * 1000;
    await new Promise(resolve => setTimeout(resolve, delay + jitter));

    try {
      const currentTasks = await fetchTasksByUnit(unitId, true);
      
      // Find tasks that weren't in the initial set (most reliable)
      const newTasks = currentTasks.filter(task => !initialTaskIds.has(task.id));

      if (newTasks.length > 0) {
        // Verify timestamps as sanity check
        const recentNewTasks = newTasks.filter(task => {
          const taskCreatedAt = new Date(task.created_at);
          return taskCreatedAt >= generationStartTime; // Use >= not >
        });

        if (recentNewTasks.length > 0) {
          devLog(`Polling completed: Found ${recentNewTasks.length} new tasks`);
          return recentNewTasks;
        } else {
          devLog(`Found ${newTasks.length} new tasks but timestamps predate generation. Continuing poll...`);
        }
      }

    } catch (error) {
      console.error(`Polling attempt ${attempt + 1} failed:`, error);
      // Continue polling despite errors
    }
  }

  devLog("No new tasks found after polling");
  return [];
}

// Function to fetch tasks by Id
async function fetchTasksByIds(taskIds: string[]): Promise<Task[]> {
  if (!taskIds.length) return [];

  devLog(`Fetching ${taskIds.length} tasks by IDs`);

  try {
    const tasksPromises = taskIds.map(async (id) => {
      try {
        const task = await $authFetch(`/tasks/${id}`);
        return task ? normalizeTask(task as Task) : null;
      } catch (error) {
        console.error(`Failed to fetch task ${id}:`, error);
        return null;
      }
    });

    const tasksResults = await Promise.all(tasksPromises);
    const validTasks = tasksResults.filter(Boolean) as Task[];
    
    devLog(`Successfully fetched ${validTasks.length}/${taskIds.length} tasks`);
    return validTasks;

  } catch (error) {
    console.error("Error fetching tasks by IDs:", error);
    return [];
  }
}


// Function to fetch tasks by unit, also populates by tasksByUnit
async function fetchTasksByUnit(unitId: string, forceRefetch = false): Promise<Task[]> {
  if (!unitId) return [];

  try {
    const response = await $authFetch(`/tasks/unit/${unitId}`) as Task[];
    const fetchedTasks = response.map(normalizeTask);
    
    if (forceRefetch) {
      tasks.value = fetchedTasks;
    }
    
    // Update tasksByUnit for counting purposes
    tasksByUnit.value[unitId] = fetchedTasks;
    
    return fetchedTasks;
  } catch (error) {
    console.error("Error fetching tasks by unit:", error);
    return [];
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

async function evaluateAnswer() {
  if (!previewingTask.value || currentAnswer.value === null || currentAnswer.value === "") {
    notifications.error("Please enter an answer.");
    return;
  }

  feedback.value = "Evaluating...";
  evaluating.value = true;

  if (previewingTask.value.type === 'multiple_choice') {
    const correct = currentAnswer.value === previewingTask.value.answer_options.find(option => option.is_correct)?.answer;
    isCorrect.value = correct;
    evaluationStatus.value = correct ? 'correct' : 'incorrect';
    showEvaluation.value = true;
    if (correct) {
      evaluating.value = false;
      return;
    }
    // Incorrect multiple choice: request backend feedback
    try {
      const responseData = await $authFetch(`/tasks/evaluate_answer/${previewingTask.value.id}`, {
        method: "POST",
        body: { student_answer: currentAnswer.value },
      }) as { feedback: string; };
      feedback.value = responseData.feedback || null;
    } catch (e: unknown) {
      notifications.error(e instanceof Error ? e.message : "Failed to evaluate answer.");
      return;
    } finally {
      evaluating.value = false;
    }
  } else {
    // Free text: wait for backend response, use new 4-way scoring system
    try {
      const responseData = await $authFetch(`/tasks/evaluate_answer/${previewingTask.value.id}`, {
        method: "POST",
        body: { student_answer: currentAnswer.value },
      }) as { feedback: string; score: number; };
      feedback.value = responseData.feedback || null;
      const scoreNum = responseData.score;

      // Handle new 4-way scoring system (0-3)
      if (scoreNum === 0) {
        // Correct: 1 point
        evaluationStatus.value = 'correct';
        isCorrect.value = true;
      } else if (scoreNum === 1) {
        // Partially correct but incomplete: 0.5 points
        evaluationStatus.value = 'partial';
        isCorrect.value = false;
      } else if (scoreNum === 2) {
        // Contradictory: 0 points
        evaluationStatus.value = 'contradictory';
        isCorrect.value = false;
      } else if (scoreNum === 3) {
        // Irrelevant: 0 points
        evaluationStatus.value = 'irrelevant';
        isCorrect.value = false;
      }
      showEvaluation.value = true;
    } catch (e: unknown) {
      notifications.error(e instanceof Error ? e.message : "Failed to evaluate answer.");
      return;
    } finally {
      evaluating.value = false;
    }
  }
}

function closeTryTask() {
  previewingTask.value = null;
  currentAnswer.value = "";
  showEvaluation.value = false;
  isCorrect.value = null;
  evaluationStatus.value = "incorrect";
  feedback.value = null;
}
</script>

<template>
  <div class="h-full max-w-4xl mx-auto mt-8">
    <DPageHeader title="Tasks" />
    <div class="bg-white p-6 rounded-lg shadow mb-4">
      <h2 class="text-xl font-bold ">Unit Filter</h2>
      
      <div v-if="UNIT_VISIBILITY_FEATURE_ENABLED" class="flex gap-2">
          <!-- Bulk visibility controls -->
          <DHamburgerMenu>
            <template #default="{ close }">
              <button @click="() => { showAllUnits(); close(); }"
                      class="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                <EyeIcon class="h-4 w-4" />
                Show All Units
              </button>
              <button @click="() => { hideAllUnits(); close(); }"
                      class="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                <EyeOffIcon class="h-4 w-4" />
                Hide All Units
              </button>
            </template>
          </DHamburgerMenu>
      </div>

      <div v-if="filterType === 'unit'">
        <!-- Unit Dropdown with Visibility Indicators -->
        <div class="space-y-2">
          <DSearchableDropdown 
            v-model="selectedUnitId"
            :options="visibleAvailableUnits.map((unit) => ({ 
              value: unit.id, 
              label: unit.title,
              disabled: UNIT_VISIBILITY_FEATURE_ENABLED ? !isUnitVisible(unit.id) : false
            }))" 
            placeholder="Select a unit"
            search-placeholder="Search units..." 
            class="mt-1 w-full" 
          />

          <!-- Unit Visibility Toggle List -->
          <div v-if="UNIT_VISIBILITY_FEATURE_ENABLED" class="mt-4 space-y-2 max-h-60 overflow-y-auto">
            <div v-for="unit in availableUnits" 
                :key="unit.id"
                class="flex items-center justify-between p-2 rounded border border-gray-200"
                :class="{ 'opacity-60': !isUnitVisible(unit.id) }">
                <div class="flex items-center gap-3 flex-1">
                  <button @click="toggleUnitVisibility(unit.id)" 
                          class="text-gray-500 hover:text-gray-700 transition-colors">
                    <component :is="isUnitVisible(unit.id) ? EyeIcon : EyeOffIcon" class="h-4 w-4" />
                  </button>
                  <span class="text-sm font-medium truncate" :class="{ 'text-gray-400': !isUnitVisible(unit.id) }">
                    {{ unit.title }}
                  </span>
                </div>
                <span class="text-xs text-gray-500 ml-2 flex-shrink-0">
                  {{ tasksByUnit[unit.id]?.length || 0 }} tasks
                </span>
            </div>
          </div>
        </div>
      </div>  
    </div>

    <!-- Empty state when selected unit is hidden -->
    <div v-if="UNIT_VISIBILITY_FEATURE_ENABLED && selectedUnitId && !isUnitVisible(selectedUnitId)" 
         class="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center mb-4">
      <div class="flex items-center justify-center gap-2 mb-2">
        <EyeOffIcon class="h-5 w-5 text-yellow-600" />
        <h3 class="text-lg font-medium text-yellow-800">Unit Hidden</h3>
      </div>
      <p class="text-yellow-700 mb-4">
        The selected unit is currently hidden. Show it to view its tasks.
      </p>
      <DButton @click="toggleUnitVisibility(selectedUnitId)" variant="primary">
        <EyeIcon class="h-4 w-4 mr-2" />
        Show This Unit
      </DButton>
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