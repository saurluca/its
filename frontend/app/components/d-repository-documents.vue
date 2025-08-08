<script setup lang="ts">
import { ref, onMounted } from "vue";
import { TrashIcon, PencilIcon, EyeIcon } from "lucide-vue-next";
import type { Document } from "~/types/models";
import { useNotificationsStore } from "~/stores/notifications";

const { $authFetch } = useAuthenticatedFetch();

interface Props {
    repositoryId: string;
    repositoryName: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{
    (e: "refresh-repositories"): void;
    (e: "view-document", documentId: string): void;
}>();

const documents = ref<Document[]>([]);
const loading = ref(true);
const uploadingDocument = ref(false);
const generatingTasks = ref(false);
const deletingDocument = ref(false);
const showGenerateTasksModal = ref(false);
const showDeleteModal = ref(false);
const generateTasksDocumentId = ref<string | null>(null);
const numTasksToGenerate = ref(1);
const deleteDocumentId = ref<string | null>(null);
const deleteDocumentTitle = ref<string | null>(null);
const showEditTitleModal = ref(false);
const editingDocumentId = ref<string | null>(null);
const editingTitle = ref("");

const notifications = useNotificationsStore();

onMounted(async () => {
    await fetchDocuments();
});

async function fetchDocuments() {
    loading.value = true;
    try {
        const data = await $authFetch(`/repositories/${props.repositoryId}/documents/`) as any;
        documents.value = data.map((doc: any) => ({
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
    } finally {
        loading.value = false;
    }
}

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

        const data = await $authFetch("/documents/upload/", {
            method: "POST",
            body: formData,
        }) as any;

        // Add document to this repository
        await $authFetch("/repositories/links/", {
            method: "POST",
            body: {
                repository_id: props.repositoryId,
                document_id: data.id,
            },
        });

        await fetchDocuments();
        emit("refresh-repositories");
    } catch (error) {
        notifications.error("Failed to upload document. Please try again. " + error);
    } finally {
        uploadingDocument.value = false;
    }
}

async function deleteDocument(documentId: string) {
    try {
        await $authFetch(`/documents/${documentId}/`, {
            method: "DELETE",
        });
        await fetchDocuments();
        emit("refresh-repositories");
    } catch (error) {
        console.error("Error deleting document:", error);
        notifications.error("Failed to delete document. Please try again. " + error);
    }
}

function closeGenerateTasksModal() {
    showGenerateTasksModal.value = false;
    generateTasksDocumentId.value = null;
}

function navigateToTasks(documentId: string) {
    navigateTo(`/tasks?documentId=${documentId}`);
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

        await fetchDocuments();
        closeEditTitleModal();
    } catch (error) {
        console.error("Error updating title:", error);
        notifications.error("Failed to update title. Please try again. " + error);
    }
}

async function confirmGenerateTasks() {
    if (!generateTasksDocumentId.value) return;
    generatingTasks.value = true;
    try {
        await $authFetch(
            `/tasks/generate/${generateTasksDocumentId.value}/?num_tasks=${numTasksToGenerate.value}`,
            {
                method: "POST",
            },
        );
        closeGenerateTasksModal();
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

function viewDocument(documentId: string) {
    emit("view-document", documentId);
}
</script>

<template>
    <div class="ml-6 border-l-2 border-gray-200 pl-4 space-y-4 mt-4">
        <div v-if="loading" class="py-4 text-center">
            <div class="text-sm text-gray-500">Loading documents...</div>
        </div>

        <div v-else-if="documents.length === 0" class="py-4 text-center text-gray-500">
            <p class="text-sm">No documents in this repository yet.</p>
        </div>

        <div v-else class="space-y-3">
            <div v-for="document in documents" :key="document.id">
                <div class="flex justify-between items-center gap-3">
                    <div class="flex flex-col cursor-pointer" @click="viewDocument(document.id)">
                        <p class="text-md">{{ document.title }}</p>
                    </div>

                    <div class="flex gap-2">
                        <DHamburgerMenu>
                            <template #default="{ close }">
                                <button @click="
                                    openEditTitleModal(document.id, document.title);
                                close();
                                "
                                    class="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                    <PencilIcon class="h-4 w-4" />
                                    Edit Title
                                </button>
                                <button @click="
                                    navigateToTasks(document.id);
                                close();
                                "
                                    class="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                    <EyeIcon class="h-4 w-4" />
                                    View Tasks
                                </button>
                                <div class="border-t border-gray-200 my-1"></div>
                                <button @click="
                                    openDeleteModal(document.id, document.title);
                                close();
                                "
                                    class="flex w-full items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50">
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

    <!-- Delete Modal -->
    <DModal v-if="showDeleteModal" titel="Delete Document" :confirmText="deletingDocument ? 'Deleting...' : 'Delete'"
        @close="closeDeleteModal" @confirm="confirmDelete">
        <div class="p-4">
            <p>
                Are you sure you want to delete the document "{{ deleteDocumentTitle }}"?
            </p>
            <p class="mt-2 text-sm text-gray-500">This action cannot be undone.</p>
        </div>
    </DModal>

    <!-- Edit Title Modal -->
    <DModal v-if="showEditTitleModal" titel="Edit Document Title" confirmText="Save" @close="closeEditTitleModal"
        @confirm="confirmEditTitle">
        <div class="p-4">
            <label for="edit-title" class="block mb-2 font-medium">Document Title:</label>
            <input id="edit-title" type="text" v-model="editingTitle" class="w-full border rounded px-3 py-2 text-sm"
                placeholder="Enter new title" @keyup.enter="confirmEditTitle" />
        </div>
    </DModal>
</template>