<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import DViewToggle from "~/components/d-view-toggle.vue";
import type { Task, Repository } from "~/types/models";

const { $authFetch } = useAuthenticatedFetch();

// Define the form interface for creating/editing tasks
interface TaskFormData {
  type: "multiple_choice" | "free_text";
  question: string;
  chunkId: string;
  options: string[];
  correctAnswer: string;
}

// Define view state
const isTeacherView = ref(true);
const tasks = ref<Task[]>([]);
const loading = ref(true);
const repositoriesList = ref<Repository[]>([]);
const documentsList = ref<{ value: string; label: string }[]>([]);
const editingTask = ref<Task | null>(null);

// For student answers
const studentAnswers = ref<Record<string, string>>({});
const showResults = ref(false);
const submittedAnswers = ref<Record<string, string>>({});

// For filtering tasks
const selectedRepositoryId = ref<string>("");
const selectedDocumentId = ref<string>("");
const filterType = ref<"repository" | "document">("repository");

// Get document ID or repository ID from route query if present
const route = useRoute();
const documentIdFromRoute = route.query.documentId as string;
const repositoryIdFromRoute = route.query.repositoryId as string;

// Initialize filter from route if present
if (documentIdFromRoute) {
  selectedDocumentId.value = documentIdFromRoute;
  filterType.value = "document";
} else if (repositoryIdFromRoute) {
  selectedRepositoryId.value = repositoryIdFromRoute;
  filterType.value = "repository";
}

// tasks are already filtered by the backend
const filteredTasks = computed(() => tasks.value);

// Toggle filter type
function toggleFilterType() {
  if (filterType.value === "repository") {
    filterType.value = "document";
    selectedRepositoryId.value = "";
  } else {
    filterType.value = "repository";
    selectedDocumentId.value = "";
  }
}

// Reset filters
function resetFilters() {
  selectedRepositoryId.value = "";
  selectedDocumentId.value = "";
  // Reload all tasks
  fetchAllTasks();
}

// Function to fetch all tasks
async function fetchAllTasks() {
  try {
    const response = await $authFetch("/tasks/") as any[];
    tasks.value = response.map((task: any) => ({
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
    const [tasksResponse, repositoriesResponse, documentsResponse] =
      await Promise.all([
        $authFetch("/tasks/"),
        $authFetch("/repositories/"),
        $authFetch("/documents/"),
      ]) as [any, any, any];

    console.log("repositoriesResponse", repositoriesResponse);
    console.log("tasksResponse", tasksResponse);
    console.log("documentsResponse", documentsResponse);

    // Default to all tasks; may be overridden by route-based filtering below
    tasks.value = (tasksResponse || []).map((task: any) => ({
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

    repositoriesList.value = (repositoriesResponse.repositories || repositoriesResponse) as Repository[];

    // Process documents for dropdown
    if (documentsResponse && Array.isArray(documentsResponse)) {
      documentsList.value = documentsResponse.map((doc: any) => ({
        value: doc.id,
        label: doc.title,
      }));
    }

    // Apply route-based filtering on initial load
    if (documentIdFromRoute) {
      await fetchTasksByDocument(documentIdFromRoute);
    } else if (repositoryIdFromRoute) {
      await fetchTasksByRepository(repositoryIdFromRoute);
    }
  } catch (error) {
    console.error("Error fetching data:", error);
  } finally {
    loading.value = false;
  }
});

// Function to fetch tasks by document
async function fetchTasksByDocument(documentId: string) {
  try {
    const response = await $authFetch(`/tasks/document/${documentId}`) as any[];
    tasks.value = response.map((task: any) => ({
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

// Function to fetch tasks by repository
async function fetchTasksByRepository(repositoryId: string) {
  try {
    const response = await $authFetch(`/tasks/repository/${repositoryId}`) as any[];
    tasks.value = response.map((task: any) => ({
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
    console.error("Error fetching tasks by repository:", error);
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

watch(selectedRepositoryId, (newValue) => {
  if (filterType.value !== "repository") return;
  if (newValue) {
    fetchTasksByRepository(newValue);
  } else {
    fetchAllTasks();
  }
});

async function createTask(taskData: TaskFormData) {
  try {
    // Create answer options from the form data
    const answer_options = taskData.options?.map((option, index) => ({
      id: `temp-${index}`,
      answer: option,
      is_correct: option === taskData.correctAnswer,
      task_id: ""
    })) || [];

    // Create the basic task
    const createdTask = await $authFetch("/tasks/", {
      method: "POST",
      body: {
        type: taskData.type,
        question: taskData.question,
        answer_options: answer_options,
        chunk_id: taskData.chunkId,
      },
    }) as Task;

    // Add task details - in a real app, you would have a separate API for this
    // For now, we'll just add it to our local array
    tasks.value.push({
      ...createdTask,
      question: taskData.question,
      answer_options: answer_options,
    });
  } catch (error) {
    console.error("Error creating task:", error);
    alert("Failed to create task. Please try again.");
  }
}

async function updateTask(taskData: Task) {
  try {
    // Create answer options from the form data
    const answer_options = taskData.answer_options?.map((option) => ({
      answer: option.answer,
      is_correct: option.is_correct
    })) || [];

    // Update the basic task
    await $authFetch(`/tasks/${taskData.id}/`, {
      method: "PUT",
      body: {
        type: taskData.type,
        question: taskData.question,
        answer_options: answer_options,
        repository_id: taskData.repository_id,
      },
    });

    const index = tasks.value.findIndex((t) => t.id === taskData.id);
    if (index !== -1) {
      tasks.value[index] = {
        ...taskData,
        updated_at: new Date(),
      };
    }

    editingTask.value = null;
  } catch (error) {
    console.error("Error updating task:", error);
    alert("Failed to update task. Please try again.");
  }
}

async function deleteTask(id: string) {
  try {
    await $authFetch(`/tasks/${id}/`, {
      method: "DELETE",
    });

    tasks.value = tasks.value.filter((t) => t.id !== id);
  } catch (error) {
    console.error("Error deleting task:", error);
    alert("Failed to delete task. Please try again.");
  }
}

function handleSaveTask(taskData: TaskFormData) {
  if (editingTask.value) {
    const updatedTask = {
      ...editingTask.value,
      type: taskData.type,
      question: taskData.question,
      answer_options: taskData.options.map((option, index) => ({
        id: `temp-${index}`,
        answer: option,
        is_correct: option === taskData.correctAnswer,
        task_id: editingTask.value!.id,
      })),
      chunk_id: taskData.chunkId,
    };
    updateTask(updatedTask);
  } else {
    // Create the task
    createTask(taskData);

    // After successful creation, create a new task form with preserved chunk
    // We do this by temporarily setting editingTask to a new object with preserved values
    // then immediately setting it back to null to trigger a form reset
    const preservedChunkId = taskData.chunkId;
    const preservedType = taskData.type;

    // Use setTimeout to ensure this happens after the current execution context
    setTimeout(() => {
      // First set a temporary task with preserved values
      editingTask.value = {
        id: "",
        type: preservedType,
        question: "",
        answer_options: [],
        repository_id: "",
        document_id: "",
        chunk_id: preservedChunkId,
        created_at: new Date(),
        updated_at: new Date(),
      } as Task;

      // Then immediately set it back to null to trigger the form reset
      setTimeout(() => {
        editingTask.value = null;
      }, 10);
    }, 0);
  }
}

function handleEditTask(task: Task) {
  editingTask.value = { ...task };
}
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-8">
      <h1 class="text-3xl font-bold">Tasks</h1>

      <DViewToggle v-model="isTeacherView" />
    </div>

    <div v-if="loading" class="py-20 text-center">
      <div class="text-xl">Loading tasks...</div>
    </div>

    <!-- Teacher View -->
    <div v-else-if="isTeacherView" class="space-y-8">
      <!-- Task Creation Form -->
      <DTaskForm :chunks="[]" :initial-task="editingTask
        ? {
          type: editingTask.type,
          question: editingTask.question || '',
          chunkId: editingTask.chunk_id || '',
          options: editingTask.answer_options?.map(option => option.answer) || [],
          correctAnswer: editingTask.answer_options?.find(option => option.is_correct)?.answer || '',
        }
        : undefined
        " @save="handleSaveTask" />

      <!-- Existing Tasks -->
      <div v-if="tasks.length > 0" class="space-y-4">
        <h2 class="text-xl font-bold">Existing Tasks</h2>

        <DTaskCard v-for="task in tasks" :key="task.id" :task="task" :is-teacher-view="true" @delete="deleteTask"
          @edit="handleEditTask" />
      </div>

      <div v-else class="bg-white p-6 rounded-lg shadow text-center">
        <p class="text-gray-500">No tasks have been created yet.</p>
      </div>
    </div>

    <!-- Student View -->
    <div v-else class="space-y-8">
      <div>
        <div class="bg-white p-6 rounded-lg shadow mb-6">
          <h2 class="text-xl font-bold mb-4">Filter Tasks</h2>

          <div class="flex justify-between items-center mb-4">
            <div class="flex items-center space-x-2">
              <span class="text-gray-700">Filter by:</span>
              <DButton @click="toggleFilterType" variant="secondary" :class="filterType === 'repository'
                ? 'inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md shadow-sm bg-blue-100 text-blue-800 border-blue-300'
                : 'inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50'
                ">
                Repository
              </DButton>
              <DButton @click="toggleFilterType" variant="secondary" :class="filterType === 'document'
                ? 'inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md shadow-sm bg-blue-100 text-blue-800 border-blue-300'
                : 'inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50'
                ">
                Document
              </DButton>
            </div>
            <DButton @click="resetFilters" variant="secondary"
              class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50">
              Reset
            </DButton>
          </div>

          <div v-if="filterType === 'repository'">
            <DLabel>Select Repository</DLabel>
            <DSearchableDropdown v-model="selectedRepositoryId" :options="[
              { value: '', label: 'All Repositories' },
              ...repositoriesList.map((repo) => ({
                value: repo.id,
                label: repo.name,
              })),
            ]" placeholder="All Repositories" search-placeholder="Search repositories..." class="mt-1 w-full" />
          </div>

          <div v-else-if="filterType === 'document'">
            <DLabel>Select Document</DLabel>
            <DSearchableDropdown v-model="selectedDocumentId" :options="[
              { value: '', label: 'All Documents' },
              ...documentsList,
            ]" placeholder="All Documents" search-placeholder="Search documents..." class="mt-1 w-full" />
          </div>
        </div>

        <h2 class="text-xl font-bold mb-4">Answer Tasks</h2>

        <div v-if="filteredTasks.length === 0" class="bg-white p-6 rounded-lg shadow text-center">
          <p class="text-gray-500">
            No tasks available for the selected filters.
          </p>
        </div>

        <div v-else class="space-y-6">
          <DTaskAnswer v-for="(task, index) in filteredTasks" :key="task.id" :task="task" :index="index"
            :model-value="studentAnswers[task.id] || ''" :disabled="showResults"
            @update:model-value="(val) => (studentAnswers[task.id] = val)" />
        </div>
      </div>
    </div>
  </div>
</template>
