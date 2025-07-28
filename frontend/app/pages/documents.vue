<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { TrashIcon, PencilIcon, CheckIcon, UploadIcon, BookCheckIcon, FileQuestion, EyeIcon } from 'lucide-vue-next';

const runtimeConfig = useRuntimeConfig();
const apiUrl = runtimeConfig.public.apiBase;

const documents = ref<{ id: string; title: string }[]>([]);
const loadingDocuments = ref(true);
const uploadingDocument = ref(false);
const uploadedDocumentId = ref<string | null>(null);
const deletingDocument = ref(false);
const generatingTasks = ref(false);
const showGenerateTasksModal = ref(false);
const generateTasksDocumentId = ref<string | null>(null);
const numTasksToGenerate = ref(1);

async function fetchDocuments() {
  loadingDocuments.value = true;
  try {
    const response = await fetch(`${apiUrl}/documents/`);
    const data = await response.json();
    // Transform the API response to an array of objects with id and title
    documents.value = data.titles.map((title: string, idx: number) => ({
      id: data.ids[idx],
      title,
    }));
  } catch (error) {
    console.error('Error fetching documents:', error);
    alert('Failed to load documents. Please try again. ' + error);
  } finally {
    loadingDocuments.value = false;
  }
}

onMounted(async () => {
  await fetchDocuments();
});

async function uploadDocumentFromInput(event: Event) {
  if (uploadingDocument.value) return;
  uploadingDocument.value = true;
  try {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) {
      uploadingDocument.value = false;
      return;
    }
    const formData = new FormData();
    formData.append("file", input.files[0]);

    const response = await fetch(`${apiUrl}/documents/to_chunks/`, {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    uploadedDocumentId.value = data.document_id;
    // Refresh the document list
    await fetchDocuments();
  } catch (error) {
    alert('Failed to upload document. Please try again. ' + error);
  } finally {
    uploadingDocument.value = false;
  }
}

function triggerFilePicker() {
  console.log("Triggering file picker");
  if (uploadingDocument.value) return;
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '*/*';
  input.addEventListener('change', uploadDocumentFromInput, { once: true });
  input.click();
}

async function deleteDocument(documentId: string) {
  deletingDocument.value = true;
  console.log("Deleting document:", documentId);
  try {
    const response = await fetch(`${apiUrl}/documents/${documentId}/`, {
      method: "DELETE",
    });
    // Refresh the document list
    await fetchDocuments();
  } catch (error) {
    console.error('Error deleting document:', error);
    alert('Failed to delete document. Please try again. ' + error);
  } finally {
    deletingDocument.value = false;
  }
}

function openGenerateTasksModal(documentId: string) {
  generateTasksDocumentId.value = documentId;
  numTasksToGenerate.value = 1;
  showGenerateTasksModal.value = true;
}
function closeGenerateTasksModal() {
  showGenerateTasksModal.value = false;
  generateTasksDocumentId.value = null;
}

function navigateToTasks(documentId: string) {
  navigateTo(`/tasks?documentId=${documentId}`);
}

async function confirmGenerateTasks() {
  if (!generateTasksDocumentId.value) return;
  generatingTasks.value = true;
  try {
    // Call the API to generate tasks
    await fetch(`${apiUrl}/tasks/generate/${generateTasksDocumentId.value}/?num_tasks=${numTasksToGenerate.value}`, {
      method: "POST",
      headers: { 'Content-Type': 'application/json' },
    });
    closeGenerateTasksModal();
    // Optionally refresh documents or show a success message
  } catch (error) {
    alert('Failed to generate tasks. Please try again. ' + error);
  } finally {
    generatingTasks.value = false;
  }
}
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-8">
      <h1 class="text-3xl font-bold">Documents</h1>
    </div>

    <div class="flex justify-between items-center mb-8">
      <DButton @click="triggerFilePicker" :loading="uploadingDocument" :iconLeft="UploadIcon">New Document</DButton>
    </div>
    
    <div v-if="uploadedDocumentId" class="py-20 text-center">
      <div class="text-xl">Document uploaded successfully. ID: {{ uploadedDocumentId }}</div>
    </div>

    <div v-else-if="uploadingDocument" class="py-20 text-center">
      <div class="text-xl">Uploading document...</div>
    </div>
    
    <div class="border border-gray-200 rounded-md p-4">
        <div v-if="loadingDocuments" class="py-20 text-center">
            <div class="text-xl">Loading documents...</div>
        </div>

        <div v-else class="space-y-4 w-full">
            <div v-for="document in documents" :key="document.id">
                <div class="flex justify-between items-center gap-2">
                    <p>{{ document.title }} / {{ document.id }}</p>
                    <div class="flex gap-2">
                        <DButton @click="navigateToTasks(document.id)" variant="secondary" :iconLeft="EyeIcon">
                            View Tasks
                        </DButton>
                        <DButton @click="openGenerateTasksModal(document.id)" :disabled="generatingTasks" :loading="generatingTasks" variant="tertiary" :iconLeft="FileQuestion">
                            Generate Tasks
                        </DButton>
                        <DButton @click="deleteDocument(document.id)" :disabled="deletingDocument" :loading="deletingDocument" variant="danger" :iconLeft="TrashIcon"/>
                    </div>
                </div>
            </div>
        </div>
    </div>
  </div>
  <DModal
    v-if="showGenerateTasksModal"
    titel="Generate Tasks"
    :confirmText="generatingTasks ? 'Generating...' : 'Generate'"
    @close="closeGenerateTasksModal"
    @confirm="confirmGenerateTasks"
  >
    <div class="p-4">
      <label for="num-tasks" class="block mb-2 font-medium">Number of tasks to generate:</label>
      <input
        id="num-tasks"
        type="number"
        min="1"
        v-model.number="numTasksToGenerate"
        class="border rounded px-2 py-1 w-24"
      />
    </div>
  </DModal>
</template>