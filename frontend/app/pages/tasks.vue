<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import DViewToggle from "~/components/d-view-toggle.vue";
import type { Task, Repository, Document as ApiDocument } from "~/types/models";
import { useNotificationsStore } from "~/stores/notifications";

const { $authFetch } = useAuthenticatedFetch();



// Define view state
const isTeacherView = ref(true);
const tasks = ref<Task[]>([]);
const loading = ref(true);
const repositoriesList = ref<Repository[]>([]);
const documentsList = ref<{ value: string; label: string }[]>([]);
const notifications = useNotificationsStore();

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
    const response = await $authFetch("/tasks/") as Task[];
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
    const [tasksResponse, repositoriesResponse, documentsResponse] =
      await Promise.all([
        $authFetch("/tasks/"),
        $authFetch("/repositories/"),
        $authFetch("/documents/"),
      ]) as [Task[], { repositories?: Repository[] } | Repository[], ApiDocument[]];

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

// Function to fetch tasks by repository
async function fetchTasksByRepository(repositoryId: string) {
  try {
    const response = await $authFetch(`/tasks/repository/${repositoryId}`) as Task[];
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

async function deleteTask(id: string) {
  try {
    await $authFetch(`/tasks/${id}/`, {
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
</script>

<template>
  <div class="h-full max-w-4xl mx-auto mt-8">
    <DPageHeader title="Tasks">
      <DViewToggle v-model="isTeacherView" />
    </DPageHeader>


    <div class="space-y-8">
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

        <div v-else>
          <DLabel>Select Document</DLabel>
          <DSearchableDropdown v-model="selectedDocumentId" :options="[
            { value: '', label: 'All Documents' },
            ...documentsList,
          ]" placeholder="All Documents" search-placeholder="Search documents..." class="mt-1 w-full" />
        </div>
      </div>

      <!-- <DTaskForm v-if="isTeacherView" :chunks="[]" :initial-task="editingTask
        ? {
          type: editingTask.type,
          question: editingTask.question || '',
          chunkId: editingTask.chunk_id || '',
          options: editingTask.answer_options?.map(option => option.answer) || [],
          correctAnswer: editingTask.answer_options?.find(option => option.is_correct)?.answer || '',
        }
        : undefined
        " @save="handleSaveTask" /> -->

      <div v-if="loading" class="py-20 text-center">
        <div class="text-xl">Loading tasks...</div>
      </div>

      <div v-else-if="filteredTasks.length === 0" class="bg-white p-6 rounded-lg shadow text-center mt-4">
        <p class="text-gray-500">
          No tasks available for the selected filters.
        </p>
      </div>

      <div v-else-if="!isTeacherView" class="space-y-6 my-4">
        <DTaskAnswer v-for="(task, index) in filteredTasks" :key="task.id" :task="task" :index="index" :model-value="''"
          :disabled="true" :is-evaluated="false" :is-correct="false" />
      </div>
      <div v-else class="space-y-6 my-4">
        <DTaskCard v-for="task in filteredTasks" :key="task.id" :task="task" :is-teacher-view="isTeacherView"
          @delete="deleteTask" @update="handleUpdateTask" />
      </div>
    </div>
  </div>
</template>
