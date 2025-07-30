<script setup lang="ts">
import { ref, onMounted } from "vue";
import {
  TrashIcon,
  PencilIcon,
  CheckIcon,
  UploadIcon,
  BookCheckIcon,
  FileQuestion,
  EyeIcon,
  BookOpenIcon,
  PlusIcon,
} from "lucide-vue-next";

const runtimeConfig = useRuntimeConfig();
const apiUrl = runtimeConfig.public.apiBase;

const documents = ref<{ id: string; title: string }[]>([]);
const loadingDocuments = ref(true);
const uploadingDocument = ref(false);
const uploadedDocumentId = ref<string | null>(null);
const deletingDocument = ref(false);
const generatingTasks = ref(false);
const showGenerateTasksModal = ref(false);
const showDeleteModal = ref(false);
const generateTasksDocumentId = ref<string | null>(null);
const numTasksToGenerate = ref(1);
const deleteDocumentId = ref<string | null>(null);
const showEditTitleModal = ref(false);
const editingDocumentId = ref<string | null>(null);
const editingTitle = ref("");

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
    console.error("Error fetching documents:", error);
    alert("Failed to load documents. Please try again. " + error);
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
    if (input.files && input.files[0]) {
      formData.append("file", input.files[0]);
    }

    const response = await fetch(`${apiUrl}/documents/to_chunks/`, {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    uploadedDocumentId.value = data.document_id;
    // Refresh the document list
    await fetchDocuments();
  } catch (error) {
    alert("Failed to upload document. Please try again. " + error);
  } finally {
    uploadingDocument.value = false;
  }
}

function triggerFilePicker() {
  console.log("Triggering file picker");
  if (uploadingDocument.value) return;
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "*/*";
  input.addEventListener("change", uploadDocumentFromInput, { once: true });
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
    console.error("Error deleting document:", error);
    alert("Failed to delete document. Please try again. " + error);
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

function navigateToStudy(documentId: string) {
  navigateTo(`/study?documentId=${documentId}`);
}

function openDeleteModal(documentId: string) {
  showDeleteModal.value = true;
  deleteDocumentId.value = documentId;
}

function closeDeleteModal() {
  showDeleteModal.value = false;
}
async function confirmGenerateTasks() {
  if (!generateTasksDocumentId.value) return;
  generatingTasks.value = true;
  try {
    // Call the API to generate tasks
    await fetch(
      `${apiUrl}/tasks/generate/${generateTasksDocumentId.value}/?num_tasks=${numTasksToGenerate.value}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      },
    );
    closeGenerateTasksModal();
    // Optionally refresh documents or show a success message
  } catch (error) {
    alert("Failed to generate tasks. Please try again. " + error);
  } finally {
    generatingTasks.value = false;
  }
}

async function confirmDelete() {
  if (!deleteDocumentId.value) return;
  await deleteDocument(deleteDocumentId.value);
  closeDeleteModal();
}

function openEditTitleModal(documentId: string, currentTitle: string) {
  editingDocumentId.value = documentId;
  editingTitle.value = currentTitle;
  showEditTitleModal.value = true;
}

function closeEditTitleModal() {
  showEditTitleModal.value = false;
  editingDocumentId.value = null;
  editingTitle.value = "";
}

async function confirmEditTitle() {
  if (!editingDocumentId.value || !editingTitle.value.trim()) return;

  try {
    const response = await fetch(
      `${apiUrl}/documents/${editingDocumentId.value}/?title=${encodeURIComponent(editingTitle.value.trim())}`,
      {
        method: "PATCH",
      },
    );

    if (response.ok) {
      // Refresh the document list to show the updated title
      await fetchDocuments();
      closeEditTitleModal();
    } else {
      alert("Failed to update title. Please try again.");
    }
  } catch (error) {
    console.error("Error updating title:", error);
    alert("Failed to update title. Please try again. " + error);
  }
}
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-8">
      <h1 class="text-3xl font-bold">Documents</h1>
    </div>

    <div class="flex items-center gap-4 mb-8">
      <DButton @click="triggerFilePicker" :loading="uploadingDocument" :iconLeft="UploadIcon">
        New Document
      </DButton>
      <div v-if="uploadingDocument">
        <DSpinner />
        <p>Uploading document and extracting text, this may take a while...</p>
      </div>
    </div>

    <div class="border border-gray-200 rounded-md p-4">
      <div v-if="loadingDocuments" class="py-8 text-center">
        <div class="text-xl">Loading documents...</div>
      </div>

      <div v-else class="space-y-4 w-full">
        <div v-for="document in documents" :key="document.id">
          <div class="flex justify-between items-center gap-2">
            <div class="flex flex-col">
              <p>{{ document.title }}</p>
              <p class="text-md text-gray-500">{{ document.id }}</p>
            </div>
            <div class="flex gap-2">
              <DButton @click="navigateToStudy(document.id)" variant="primary" :iconLeft="BookOpenIcon">
              </DButton>
              <DButton @click="openGenerateTasksModal(document.id)" :disabled="generatingTasks"
                :loading="generatingTasks" variant="tertiary" :iconLeft="PlusIcon">
              </DButton>

              <div>
                I think
                foramting is wa ss
              </div>

              <DHamburgerMenu>
                <template #default="{ close }">
                  <button @click="
                    openEditTitleModal(document.id, document.title);
                  close();
                  " class="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                    <PencilIcon class="h-4 w-4" />
                    Edit Title
                  </button>
                  <button @click="
                    navigateToTasks(document.id);
                  close();
                  " class="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                    <EyeIcon class="h-4 w-4" />
                    View Tasks
                  </button>
                  <div class="border-t border-gray-200 my-1"></div>
                  <button @click="
                    openDeleteModal(document.id);
                  close();
                  " class="flex w-full items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50">
                    <TrashIcon class="h-4 w-4" />
                    Delete
                  </button>
                </template>
              </DHamburgerMenu>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <DModal v-if="showGenerateTasksModal" titel="Generate Tasks"
    :confirmText="generatingTasks ? 'Generating...' : 'Generate'" @close="closeGenerateTasksModal"
    @confirm="confirmGenerateTasks">
    <div class="p-4">
      <label for="num-tasks" class="block mb-2 font-medium">Number of tasks to generate:</label>
      <input id="num-tasks" type="number" min="1" v-model.number="numTasksToGenerate"
        class="border rounded px-2 py-1 w-24" />
    </div>
  </DModal>
  <DModal v-if="showDeleteModal" titel="Delete Document" :confirmText="deletingDocument ? 'Deleting...' : 'Delete'"
    @close="closeDeleteModal" @confirm="confirmDelete">
    <div class="p-4">
      <p>
        Are you sure you want to delete the document "{{ deleteDocumentId }}"?
      </p>
      <p class="mt-2 text-sm text-gray-500">This action cannot be undone.</p>
    </div>
  </DModal>

  <DModal v-if="showEditTitleModal" titel="Edit Document Title" confirmText="Save" @close="closeEditTitleModal"
    @confirm="confirmEditTitle">
    <div class="p-4">
      <label for="edit-title" class="block mb-2 font-medium">Document Title:</label>
      <input id="edit-title" type="text" v-model="editingTitle" class="w-full border rounded px-3 py-2 text-sm"
        placeholder="Enter new title" @keyup.enter="confirmEditTitle" />
    </div>
  </DModal>
</template>
