<script setup lang="ts">
import type { Task } from '~/types/models';
import { ref } from 'vue';

const props = defineProps<{
  task: Task;
  isTeacherView: boolean;
}>();

const emit = defineEmits<{
  (e: 'delete', id: string): void;
  (e: 'edit', task: Task): void;
}>();

// Modal state
const showDeleteModal = ref(false);

function openDeleteModal() {
  showDeleteModal.value = true;
}

function closeDeleteModal() {
  showDeleteModal.value = false;
}

function confirmDelete() {
  emit('delete', props.task.id);
  closeDeleteModal();
}

function editTask() {
  emit('edit', props.task);
}
</script>

<template>
  <div class="bg-white p-4 rounded-lg shadow">
    <div class="flex justify-between">
      <h3 class="text-lg font-medium">{{ task.question }}</h3>
      <div class="flex space-x-3 items-center">
        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
          {{ task.type === 'true_false' ? 'True/False' : task.type === 'multiple_choice' ? 'Multiple Choice' : 'Free Text' }}
        </span>
        
        <div v-if="isTeacherView" class="flex space-x-2">
          <DButton 
            @click="editTask"
            title="Edit"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
            </svg>
          </DButton>
          <DButton 
            @click="openDeleteModal"
            variant="danger"
            title="Delete"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
          </DButton>
        </div>
      </div>
    </div>
    <div class="mt-4 text-sm text-gray-500">
      <p v-if="task.type === 'true_false'">Correct answer: {{ task.correctAnswer }}</p>
      <p v-else-if="task.type === 'multiple_choice'">
        Options: {{ task.options?.join(', ') }}<br>
        Correct answer: {{ task.correctAnswer }}
      </p>
      <p v-else>Sample answer: {{ task.correctAnswer }}</p>
    </div>
    
    <slot></slot>
    
    <!-- Delete Confirmation Modal -->
    <DModal
      v-if="showDeleteModal"
      titel="Confirm Task Deletion"
      confirmText="Delete"
      @close="closeDeleteModal"
      @confirm="confirmDelete"
    >
      <div class="p-4">
        <p>Are you sure you want to delete the task "{{ task.name }}"?</p>
        <p class="mt-2 text-sm text-gray-500">This action cannot be undone.</p>
      </div>
    </DModal>
  </div>
</template> 