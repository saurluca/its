<script setup lang="ts">
import { ref, onMounted } from "vue";
import {
  TrashIcon,
  PencilIcon,
  UploadIcon,
  EyeIcon,
  BookOpenIcon,
  PlusIcon,
  FileTextIcon,
  FolderIcon,
} from "lucide-vue-next";
import type { Document, Repository } from "~/types/models";
import { useNotificationsStore } from "~/stores/notifications";

const { $authFetch } = useAuthenticatedFetch();

const documents = ref<Document[]>([]);
const repositories = ref<Repository[]>([]);
const loadingDocuments = ref(true);
const loadingRepositories = ref(true);

const uploadedDocumentId = ref<string | null>(null);
const deletingDocument = ref(false);
const generatingTasks = ref(false);
const showGenerateTasksModal = ref(false);
const showDeleteModal = ref(false);
const showRepositoryModal = ref(false);
const generateTasksDocumentId = ref<string | null>(null);
const numTasksToGenerate = ref(1);
const deleteDocumentId = ref<string | null>(null);
const deleteDocumentTitle = ref<string | null>(null);
const showEditTitleModal = ref(false);
const editingDocumentId = ref<string | null>(null);
const editingTitle = ref("");
const selectedRepositoryId = ref<string>("");
const selectedRepositoryName = ref<string>("");

// HTML viewer state
const showHtmlViewer = ref(false);
const htmlContent = ref("");
const loadingHtml = ref(false);
const htmlError = ref("");
const selectedDocumentId = ref<string | null>(null);
const notifications = useNotificationsStore();

async function fetchDocuments() {
  loadingDocuments.value = true;
  try {
    const data = await $authFetch("/documents/") as Document[];
    // Transform the API response to match our Document interface
    documents.value = data.map((doc: Document) => ({
      id: doc.id,
      title: doc.title,
      content: doc.content,
      created_at: new Date(doc.created_at),
      deleted_at: doc.deleted_at ? new Date(doc.deleted_at) : null,
      repository_ids: doc.repository_ids || [],
      source_file: doc.source_file,
    }));
  } catch (error) {
    console.error("Error fetching documents:", error);
    notifications.error("Failed to load documents. Please try again. " + error);
  } finally {
    loadingDocuments.value = false;
  }
}

async function fetchRepositories() {
  loadingRepositories.value = true;
  try {
    const data = await $authFetch("/repositories/") as Repository[];
    repositories.value = data;
  } catch (error) {
    console.error("Error fetching repositories:", error);
    notifications.error("Failed to load repositories. Please try again. " + error);
  } finally {
    loadingRepositories.value = false;
  }
}

onMounted(async () => {
  await Promise.all([fetchDocuments(), fetchRepositories()]);
});

async function uploadDocumentFromInput(event: Event) {

  const input = event.target as HTMLInputElement;
  if (!input.files || input.files.length === 0) {
    return;
  }

  // Capture file data before proceeding
  const file = input.files[0];
  if (!file) {
    return;
  }
  const fileName = file.name || 'Unknown file';

  // Show processing notification
  const processingId = notifications.warning(`Processing document "${fileName}"... This may take a while.`);

  try {
    const formData = new FormData();
    formData.append("file", file);

    const data = await $authFetch("/documents/upload/", {
      method: "POST",
      body: formData,
    }) as { id: string };
    uploadedDocumentId.value = data.id;
    // Refresh the document list
    await fetchDocuments();

    // Remove processing notification and show success
    notifications.remove(processingId);
    notifications.success(`Document "${fileName}" uploaded successfully!`);
  } catch (error) {
    // Remove processing notification and show error
    notifications.remove(processingId);
    notifications.error(`Failed to upload "${fileName}". Please try again. ${error}`);
  }
}

function triggerFilePicker() {
  console.log("Triggering file picker");
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
    await $authFetch(`/documents/${documentId}/`, {
      method: "DELETE",
    });
    // Refresh the document list
    await fetchDocuments();
  } catch (error) {
    console.error("Error deleting document:", error);
    notifications.error("Failed to delete document. Please try again. " + error);
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

function openDeleteModal(documentId: string, documentTitle: string) {
  showDeleteModal.value = true;
  deleteDocumentId.value = documentId;
  deleteDocumentTitle.value = documentTitle;
}

function closeDeleteModal() {
  showDeleteModal.value = false;
  deleteDocumentId.value = null;
  deleteDocumentTitle.value = null;
}

function openRepositoryModal(documentId: string) {
  selectedDocumentId.value = documentId;
  showRepositoryModal.value = true;
}

function closeRepositoryModal() {
  showRepositoryModal.value = false;
  selectedDocumentId.value = null;
  selectedRepositoryId.value = "";
  selectedRepositoryName.value = "";
}

async function confirmGenerateTasks() {
  if (!generateTasksDocumentId.value) return;
  generatingTasks.value = true;
  try {
    // Call the API to generate tasks
    await $authFetch(
      `/tasks/generate/${generateTasksDocumentId.value}/?num_tasks=${numTasksToGenerate.value}`,
      {
        method: "POST",
      },
    );
    closeGenerateTasksModal();
    // Optionally refresh documents or show a success message
  } catch (error) {
    notifications.error("Failed to generate tasks. Please try again. " + error);
  } finally {
    generatingTasks.value = false;
  }
}

async function confirmDelete() {
  if (!deleteDocumentId.value) return;
  await deleteDocument(deleteDocumentId.value);
  closeDeleteModal();
}

async function confirmAddToRepository() {
  if (!selectedDocumentId.value || !selectedRepositoryId.value) return;

  try {
    await $authFetch("/repositories/links/", {
      method: "POST",
      body: {
        repository_id: selectedRepositoryId.value,
        document_id: selectedDocumentId.value,
      },
    });

    closeRepositoryModal();
    // Refresh repositories to show updated document lists
    await fetchRepositories();
  } catch (error) {
    console.error("Error adding document to repository:", error);
    notifications.error("Failed to add document to repository. Please try again. " + error);
  }
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
    await $authFetch(
      `/documents/${editingDocumentId.value}/?title=${encodeURIComponent(editingTitle.value.trim())}`,
      {
        method: "PATCH",
      },
    );

    // Refresh the document list to show the updated title
    await fetchDocuments();
    closeEditTitleModal();
  } catch (error) {
    console.error("Error updating title:", error);
    notifications.error("Failed to update title. Please try again. " + error);
  }
}

async function viewDocument(documentId: string) {
  if (selectedDocumentId.value === documentId && showHtmlViewer.value) {
    // If clicking the same document, toggle the viewer off
    showHtmlViewer.value = false;
    selectedDocumentId.value = null;
    htmlContent.value = "";
    return;
  }

  loadingHtml.value = true;
  htmlError.value = "";
  selectedDocumentId.value = documentId;
  showHtmlViewer.value = true;

  try {
    const data = await $authFetch(`/documents/${documentId}/`) as Document;

    if (data.content) {
      htmlContent.value = data.content;
    } else {
      htmlError.value = "Document content not found";
    }
  } catch (err) {
    console.error("Error fetching document content:", err);
    htmlError.value = "Failed to load document content";
  } finally {
    loadingHtml.value = false;
  }
}
</script>

<template>
  <div>
    <div class="h-full flex">
      <!-- Left side - Documents list -->
      <div class="w-1/2 p-6 overflow-y-auto">
        <div class="max-w-4xl mx-auto">
          <div class="flex justify-between items-center mb-8">
            <h1 class="text-3xl font-bold">Documents</h1>
          </div>

          <div class="flex items-center gap-4 mb-8">
            <DButton @click="triggerFilePicker" :icon-left='UploadIcon'>
              New Document
            </DButton>
          </div>

          <div class=" rounded-md p-4 shadow-sm">
            <div v-if="loadingDocuments" class="py-8 text-center">
              <div class="text-xl">Loading documents...</div>
            </div>

            <div v-else-if="documents.length === 0" class="py-2 text-center text-gray-500">
              <p>No documents found. Upload a document to get started.</p>
            </div>

            <div v-else class="space-y-3 w-full">
              <div v-for="document in documents" :key="document.id">
                <div class="flex justify-between items-center gap-2">
                  <div class="flex flex-col cursor-pointer" @click="viewDocument(document.id)">
                    <p>{{ document.title }}</p>
                  </div>

                  <div class="flex gap-2">
                    <DButton @click="navigateToStudy(document.id)" variant="primary" :icon-left="BookOpenIcon">
                      Study
                    </DButton>
                    <DButton @click="openGenerateTasksModal(document.id)" :disabled="generatingTasks"
                      :loading="generatingTasks" variant="tertiary" :icon-left="PlusIcon" class="!p-2" />

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
                        <button @click="
                          openRepositoryModal(document.id);
                        close();
                        " class="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                          <FolderIcon class="h-4 w-4" />
                          Add to Repository
                        </button>
                        <div class="border-t border-gray-200 my-1"></div>
                        <button @click="
                          openDeleteModal(document.id, document.title);
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
      </div>

      <!-- Right side - HTML viewer -->
      <div class="w-1/2 border-l border-gray-200">
        <div v-if="showHtmlViewer" class="h-full p-4">
          <DHtmlViewer :html-content="htmlContent" :loading="loadingHtml" :error="htmlError" />
        </div>
        <div v-else class="h-full flex items-center justify-center text-gray-500">
          <div class="text-center">
            <FileTextIcon class="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>Select a Document by clicking on it to preview its content</p>
          </div>
        </div>
      </div>
    </div>

    <DModal v-if="showGenerateTasksModal" titel="Generate Tasks"
      :confirm-text="generatingTasks ? 'Generating...' : 'Generate'" @close="closeGenerateTasksModal"
      @confirm="confirmGenerateTasks">
      <div class="p-4">
        <label for="num-tasks" class="block mb-2 font-medium">Number of tasks to generate:</label>
        <input id="num-tasks" type="number" min="1" v-model.number="numTasksToGenerate"
          class="border rounded px-2 py-1 w-24" />
      </div>
    </DModal>

    <DModal v-if="showDeleteModal" titel="Delete Document" :confirm-text="deletingDocument ? 'Deleting...' : 'Delete'"
      @close="closeDeleteModal" @confirm="confirmDelete">
      <div class="p-4">
        <p>
          Are you sure you want to delete the document "{{ deleteDocumentTitle }}"?
        </p>
        <p class="mt-2 text-sm text-gray-500">This action cannot be undone.</p>
      </div>
    </DModal>

    <DModal v-if="showEditTitleModal" titel="Edit Document Title" confirm-text="Save" @close="closeEditTitleModal"
      @confirm="confirmEditTitle">
      <div class="p-4">
        <label for="edit-title" class="block mb-2 font-medium">Document Title:</label>
        <input id="edit-title" type="text" v-model="editingTitle" class="w-full border rounded px-3 py-2 text-sm"
          placeholder="Enter new title" @keyup.enter="confirmEditTitle" />
      </div>
    </DModal>

    <DModal v-if="showRepositoryModal" titel="Add Document to Repository" confirm-text="Add"
      @close="closeRepositoryModal" @confirm="confirmAddToRepository">
      <div class="p-4">
        <label for="repository-select" class="block mb-2 font-medium">Select Repository:</label>
        <select id="repository-select" v-model="selectedRepositoryId" class="w-full border rounded px-3 py-2 text-sm">
          <option value="">Select a repository...</option>
          <option v-for="repo in repositories" :key="repo.id" :value="repo.id">
            {{ repo.name }}
          </option>
        </select>
      </div>
    </DModal>
  </div>
</template>
