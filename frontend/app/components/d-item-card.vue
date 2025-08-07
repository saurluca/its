<script setup lang="ts">
import { computed, ref } from "vue";

interface Item {
  id: string;
  name: string;
  description?: string;
  [key: string]: any;
}

const props = defineProps<{
  item: Item;
}>();

const emit = defineEmits<{
  (e: "delete", id: string): void;
  (e: "edit", item: Item): void;
}>();

const hasDescription = computed(() => {
  return !!props.item.description;
});

// Modal state
const showDeleteModal = ref(false);

function openDeleteModal() {
  showDeleteModal.value = true;
}

function closeDeleteModal() {
  showDeleteModal.value = false;
}

function confirmDelete() {
  emit("delete", props.item.id);
  closeDeleteModal();
}

function editItem() {
  emit("edit", props.item);
}
</script>

<template>
  <div class="bg-white p-4 rounded-lg shadow border border-gray-100">
    <div class="flex justify-between">
      <h3 class="text-lg font-medium">{{ item.name }}</h3>
      <div class="flex space-x-2">
        <DButton @click="editItem" title="Edit">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path
              d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
          </svg>
        </DButton>
        <DButton @click="openDeleteModal" variant="danger" title="Delete">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd"
              d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
              clip-rule="evenodd" />
          </svg>
        </DButton>
      </div>
    </div>
    <p v-if="hasDescription" class="mt-2 text-gray-700">
      {{ item.description }}
    </p>
    <slot></slot>

    <!-- Delete Confirmation Modal -->
    <DModal v-if="showDeleteModal" titel="Confirm Deletion" confirmText="Delete" @close="closeDeleteModal"
      @confirm="confirmDelete">
      <div class="p-4">
        <p>Are you sure you want to delete "{{ item.name }}"?</p>
        <p class="mt-2 text-sm text-gray-500">This action cannot be undone.</p>
      </div>
    </DModal>
  </div>
</template>
