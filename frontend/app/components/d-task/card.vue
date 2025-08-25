<script setup lang="ts">
import type { Task } from "~/types/models";
import { ref, computed, onMounted, onUnmounted } from "vue";
import { TrashIcon, PencilIcon, CheckIcon, PlusIcon, FlaskConical, XIcon } from "lucide-vue-next";
import { useNotificationsStore } from "~/stores/notifications";

const { $authFetch } = useAuthenticatedFetch();
const notifications = useNotificationsStore();

const props = defineProps<{
  task: Task;
  isTeacherView: boolean;
}>();

const emit = defineEmits<{
  (e: "delete", id: string): void;
  (e: "edit" | "update", task: Task): void;
  (e: "preview-task", task: Task): void;
}>();

// Modal state
const showDeleteModal = ref(false);
const isEditing = ref(false);
const isSaving = ref(false);

// Editable task data
const editableTask = ref<Task>({ ...props.task });

// Keyboard event handler
function handleKeyDown(event: KeyboardEvent) {
  if (!isEditing.value || isSaving.value) return;

  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    saveTask();
  }

  if (event.key === 'Escape') {
    event.preventDefault();
    cancelEdit();
  }
}

// Set up and clean up event listeners
onMounted(() => {
  document.addEventListener('keydown', handleKeyDown);
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown);
});

function openDeleteModal() {
  showDeleteModal.value = true;
}

function closeDeleteModal() {
  showDeleteModal.value = false;
}

async function confirmDelete() {
  try {
    emit("delete", props.task.id);
    notifications.success("Task deleted successfully");
  } catch (error) {
    console.error("Error deleting task:", error);
    notifications.error("Failed to delete task. Please try again.");
  }
  closeDeleteModal();
}

function editTask() {
  isEditing.value = true;
  editableTask.value = { ...props.task };

  // Ensure answer_options exists for free text questions
  if (editableTask.value.type === 'free_text' && (!editableTask.value.answer_options || editableTask.value.answer_options.length === 0)) {
    editableTask.value.answer_options = [{
      id: `temp-${Date.now()}`,
      answer: '',
      is_correct: true,
      task_id: editableTask.value.id
    }];
  }
}

function validateTask(): boolean {
  // Check if question is not empty
  if (!editableTask.value.question.trim()) {
    notifications.error("Question cannot be empty");
    return false;
  }

  // For multiple choice, ensure at least one option is correct
  if (editableTask.value.type === 'multiple_choice') {
    if (!editableTask.value.answer_options || editableTask.value.answer_options.length === 0) {
      notifications.error("At least one answer option is required");
      return false;
    }

    const hasCorrectAnswer = editableTask.value.answer_options.some(option => option.is_correct);
    if (!hasCorrectAnswer) {
      notifications.error("At least one answer option must be marked as correct");
      return false;
    }

    // Check if all options have content
    const hasEmptyOptions = editableTask.value.answer_options.some(option => !option.answer.trim());
    if (hasEmptyOptions) {
      notifications.error("All answer options must have content");
      return false;
    }
  }

  // For free text, ensure correct answer is provided
  if (editableTask.value.type === 'free_text') {
    if (!editableTask.value.answer_options || editableTask.value.answer_options.length === 0 || !editableTask.value.answer_options[0]?.answer.trim()) {
      notifications.error("Correct answer is required for free text questions");
      return false;
    }
  }

  return true;
}

async function saveTask() {
  if (!validateTask()) {
    return;
  }

  isSaving.value = true;
  try {
    // Prepare answer options for backend
    const answer_options = editableTask.value.answer_options?.map((option) => ({
      answer: option.answer,
      is_correct: option.is_correct
    })) || [];

    // Update the task via API
    const updatedTask = await $authFetch(`/tasks/${editableTask.value.id}`, {
      method: "PUT",
      body: {
        type: editableTask.value.type,
        question: editableTask.value.question,
        answer_options: answer_options,
        repository_id: editableTask.value.repository_id,
      },
    });

    // Update the local task data
    const updatedTaskWithOptions = {
      ...updatedTask,
      answer_options: editableTask.value.answer_options
    };

    emit("update", updatedTaskWithOptions);
    isEditing.value = false;
    notifications.success("Task updated successfully");
  } catch (error) {
    console.error("Error updating task:", error);
    notifications.error("Failed to update task. Please try again.");
  } finally {
    isSaving.value = false;
  }
}

function cancelEdit() {
  isEditing.value = false;
  editableTask.value = { ...props.task };
}

function updateAnswerOption(index: number, field: 'answer' | 'is_correct', value: string | boolean) {
  if (editableTask.value.answer_options && editableTask.value.answer_options[index]) {
    // If setting is_correct to true, first set all others to false
    if (field === 'is_correct' && value === true) {
      editableTask.value.answer_options.forEach((option, i) => {
        if (i !== index) {
          option.is_correct = false;
        }
      });
    }

    editableTask.value.answer_options[index] = {
      ...editableTask.value.answer_options[index]!,
      [field]: value
    };
  }
}

function addAnswerOption() {
  if (!editableTask.value.answer_options) {
    editableTask.value.answer_options = [];
  }
  editableTask.value.answer_options.push({
    id: `temp-${Date.now()}`,
    answer: '',
    is_correct: false,
    task_id: editableTask.value.id
  });
}

function removeAnswerOption(index: number) {
  if (editableTask.value.answer_options) {
    // Don't allow removing if it's the only option or if it's the correct one and there are other options
    const isCorrect = editableTask.value.answer_options[index]?.is_correct;
    const hasOtherCorrectOptions = editableTask.value.answer_options.some((option, i) => i !== index && option.is_correct);

    if (editableTask.value.answer_options.length === 1) {
      notifications.error("Cannot remove the last answer option");
      return;
    }

    if (isCorrect && !hasOtherCorrectOptions) {
      notifications.error("Cannot remove the only correct answer. Please mark another option as correct first.");
      return;
    }

    editableTask.value.answer_options.splice(index, 1);
  }
}

// Computed properties for displaying task information
const correctAnswer = computed(() => {
  return props.task.answer_options?.find(option => option.is_correct)?.answer || '';
});

const freeTextAnswer = computed({
  get: () => editableTask.value.answer_options?.[0]?.answer || '',
  set: (value: string) => {
    if (editableTask.value.answer_options && editableTask.value.answer_options[0]) {
      editableTask.value.answer_options[0].answer = value;
    }
  }
});
</script>

<template>
  <div class="bg-white p-6 rounded-lg shadow max-w-4xl">
    <div class="flex justify-between items-center">
      <span class="px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
        {{
          task.type === "multiple_choice"
            ? "Multiple Choice"
            : "Free Text"
        }}
      </span>

      <!-- Action buttons -->
      <div v-if="isTeacherView" class="flex space-x-2 ml-4">
        <button v-if="!isEditing" @click="() => emit('preview-task', task)"
          class="p-2 text-gray-600 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
          title="Preview Task">
          <FlaskConical class="h-5 w-5" />
        </button>
        <button v-if="!isEditing" @click="editTask"
          class="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors" title="Edit Task">
          <PencilIcon class="h-5 w-5" />
        </button>
        <button v-if="!isEditing" @click="openDeleteModal"
          class="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors" title="Delete Task">
          <TrashIcon class="h-5 w-5" />
        </button>

        <!-- Save/Cancel buttons when editing -->
        <button v-if="isEditing" @click="saveTask" :disabled="isSaving"
          class="p-2 text-green-600 hover:text-green-700 hover:bg-green-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          title="Save Changes (Enter)">
          <CheckIcon class="h-5 w-5" />
        </button>
        <button v-if="isEditing" @click="cancelEdit" :disabled="isSaving"
          class="px-3 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          title="Cancel Edit (Escape)">
          <XIcon class="h-5 w-5" />
        </button>
      </div>
    </div>

    <!-- Question -->
    <div class="mt-3">
      <label v-if="isEditing" class="block text-md font-medium text-gray-700 mb-2">Question:</label>
      <textarea v-if="isEditing" v-model="editableTask.question" rows="3"
        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        placeholder="Enter the question..."></textarea>
      <p v-else class="mt-2">{{ task.question }}</p>
    </div>

    <!-- Multiple Choice Answer Options -->
    <div v-if="task.type === 'multiple_choice'" class="mt-1">
      <div v-if="isEditing" class="space-y-3">
        <div class="flex items-center justify-between">
          <label class="block text-md font-medium text-gray-700">Answer Options</label>
          <DButton @click="addAnswerOption" variant="tertiary" :icon-left="PlusIcon">
            Add Option
          </DButton>
        </div>

        <div v-for="(option, index) in editableTask.answer_options" :key="option.id"
          class="flex items-center space-x-3">
          <input v-model="option.answer" type="text"
            class="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Enter answer option..." />
          <label class="flex items-center space-x-2">
            <input type="radio" :name="`correct-${task.id}`" :checked="option.is_correct"
              @change="updateAnswerOption(index, 'is_correct', true)"
              class="h-4 w-4 text-blue-600 focus:ring-blue-500" />
            <span class="text-md text-gray-700">Correct</span>
          </label>
          <button @click="removeAnswerOption(index)"
            class="p-1 text-red-600 hover:text-red-800 hover:bg-red-50 rounded transition-colors" title="Remove option">
            <TrashIcon class="h-4 w-4" />
          </button>
        </div>

        <!-- Keyboard hint -->
        <div v-if="isEditing" class="text-xs text-gray-500 mt-2">
          Tip: Press <kbd class="px-1 py-0.5 bg-gray-100 rounded text-xs">Enter</kbd> to save changes or <kbd
            class="px-1 py-0.5 bg-gray-100 rounded text-xs">Escape</kbd> to cancel
        </div>
      </div>

      <!-- Display mode for multiple choice -->
      <div v-else class="space-y-2">
        <div v-for="option in task.answer_options" :key="option.id" class="flex items-center space-x-3">
          <div class="flex-1 px-3 py-2 border rounded-md flex items-center justify-between" :class="option.is_correct
            ? 'border-green-500 bg-green-50 text-green-800'
            : 'border-gray-300 bg-gray-50 text-gray-700'">
            {{ option.answer }}
            <div v-if="option.is_correct" class="text-green-600">
              <CheckIcon class="h-5 w-5" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Free Text Answer -->
    <div v-else class="mt-4">
      <div v-if="isEditing">
        <label class="block text-sm font-medium text-gray-700 mb-2">Correct Answer:</label>
        <textarea v-model="freeTextAnswer" rows="4"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="Enter the correct answer..."></textarea>

        <!-- Keyboard hint -->
        <div class="text-xs text-gray-500 mt-2">
          Tip: Press <kbd class="px-1 py-0.5 bg-gray-100 rounded text-xs">Enter</kbd> to save changes or <kbd
            class="px-1 py-0.5 bg-gray-100 rounded text-xs">Escape</kbd> to cancel
        </div>
      </div>
      <div v-else>
        <div class="px-3 py-2 border border-green-500 bg-green-50 text-green-800 rounded-md">
          <strong>Correct Answer:</strong> {{ correctAnswer }}
        </div>
      </div>
    </div>
  </div>

  <!-- Delete Confirmation Modal -->
  <DModal v-if="showDeleteModal" titel="Confirm Task Deletion" confirm-text="Delete" @close="closeDeleteModal"
    @confirm="confirmDelete">
    <div class="p-4">
      <p>Are you sure you want to delete the task "{{ task.question }}"?</p>
      <p class="mt-2 text-sm text-gray-500">This action cannot be undone.</p>
    </div>
  </DModal>
</template>
