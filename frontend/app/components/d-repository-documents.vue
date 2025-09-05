<script setup lang="ts">
import { ref, onMounted } from "vue";
import { TrashIcon, PencilIcon, PlusIcon } from "lucide-vue-next";
import type { Document, Repository } from "~/types/models";
import { useNotificationsStore } from "~/stores/notifications";

const { $authFetch } = useAuthenticatedFetch();

type SimpleFetch = <T>(input: string, init?: { method?: string; body?: unknown; headers?: Record<string, string> }) => Promise<T>;
const fetchJson = $authFetch as SimpleFetch;

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

const deletingDocument = ref(false);
const showDeleteModal = ref(false);
const deleteDocumentId = ref<string | null>(null);
const deleteDocumentTitle = ref<string | null>(null);
const showEditTitleModal = ref(false);
const editingDocumentId = ref<string | null>(null);
const editingTitle = ref("");

// Link/unlink state
const showAddToRepoModal = ref(false);
const linkDocumentId = ref<string | null>(null);
const linkDocumentTitle = ref<string | null>(null);
const allRepositories = ref<Repository[]>([]);
const availableTargetRepositories = ref<Repository[]>([]);
const selectedTargetRepositoryId = ref<string | null>(null);

const notifications = useNotificationsStore();

onMounted(async () => {
    await fetchDocuments();
    await fetchAllRepositories();
});

async function fetchDocuments() {
    loading.value = true;
    try {
        const data = await fetchJson<Document[]>(`/repositories/${props.repositoryId}/documents/`);
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
    } finally {
        loading.value = false;
    }
}

async function fetchAllRepositories() {
    try {
        const response = await fetchJson<Repository[]>(`/repositories/`);
        allRepositories.value = response;
    } catch (error) {
        console.error("Error fetching repositories:", error);
        notifications.error("Failed to load repositories. Please try again. " + error);
    }
}

async function deleteDocument(documentId: string) {
    try {
        await $authFetch(`/documents/${documentId}`, {
            method: "DELETE",
        });
        await fetchDocuments();
        emit("refresh-repositories");
    } catch (error) {
        console.error("Error deleting document:", error);
        notifications.error("Failed to delete document. Please try again. " + error);
    }
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

async function confirmDelete() {
    if (!deleteDocumentId.value) return;
    await deleteDocument(deleteDocumentId.value);
    closeDeleteModal();
}

function viewDocument(documentId: string) {
    emit("view-document", documentId);
}

async function openAddToRepoModal(documentId: string, documentTitle: string, repositoryIds: string[]) {
    linkDocumentId.value = documentId;
    linkDocumentTitle.value = documentTitle;
    // Refresh repositories to include newly created ones
    try {
        await fetchAllRepositories();
    } catch (error) {
        console.error("Error fetching repositories:", error);
        notifications.error("Failed to load repositories. Please try again. " + error);
    }
    // Filter out current repository and repositories the document is already in
    availableTargetRepositories.value = allRepositories.value.filter(
        (repo) => repo.id !== props.repositoryId && !repositoryIds.includes(repo.id)
    );
    const firstRepo = availableTargetRepositories.value[0];
    selectedTargetRepositoryId.value = firstRepo ? firstRepo.id : null;
    showAddToRepoModal.value = true;
}

function closeAddToRepoModal() {
    showAddToRepoModal.value = false;
    linkDocumentId.value = null;
    linkDocumentTitle.value = null;
    availableTargetRepositories.value = [];
    selectedTargetRepositoryId.value = null;
}

async function confirmAddToRepo() {
    if (!linkDocumentId.value || !selectedTargetRepositoryId.value) {
        notifications.warning("Please select a repository.");
        return;
    }
    try {
        await $authFetch(`/repositories/links`, {
            method: "POST",
            body: {
                repository_id: selectedTargetRepositoryId.value,
                document_id: linkDocumentId.value,
            },
        });
        notifications.success("Document added to repository successfully.");
        closeAddToRepoModal();
        // No need to refresh current list; linking elsewhere doesn't affect it.
    } catch (error) {
        console.error("Error linking document to repository:", error);
        notifications.error("Failed to add document to repository. Please try again. " + error);
    }
}

async function removeFromThisRepository(documentId: string) {
    try {
        await $authFetch(`/repositories/links/${props.repositoryId}/${documentId}`, {
            method: "DELETE",
        });
        notifications.success("Removed document from this repository.");
        await fetchDocuments();
        emit("refresh-repositories");
    } catch (error) {
        console.error("Error unlinking document from repository:", error);
        notifications.error("Failed to remove document from repository. Please try again. " + error);
    }
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
                                <!--          <button @click="
                                    navigateToTasks(document.id);
                                close();
                                "
                                    class="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                    <EyeIcon class="h-4 w-4" />
                                    View Tasks
                                </button> -->
                                <button @click="
                                    openEditTitleModal(document.id, document.title);
                                close();
                                "
                                    class="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                    <PencilIcon class="h-4 w-4" />
                                    Edit Title
                                </button>
                                <button @click="
                                    openAddToRepoModal(document.id, document.title, document.repository_ids || []);
                                close();
                                "
                                    class="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                    <PlusIcon class="h-4 w-4" />
                                    Add to other repository
                                </button>
                                <button @click="
                                    removeFromThisRepository(document.id);
                                close();
                                "
                                    class="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                    <TrashIcon class="h-4 w-4" />
                                    Remove from repository
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
    <DModal v-if="showDeleteModal" titel="Delete Document" :confirm-text="deletingDocument ? 'Deleting...' : 'Delete'"
        @close="closeDeleteModal" @confirm="confirmDelete">
        <div class="p-4">
            <p>
                Are you sure you want to delete the document "{{ deleteDocumentTitle }}"?
            </p>
            <p class="mt-2 text-sm text-gray-500">This action cannot be undone.</p>
        </div>
    </DModal>

    <!-- Edit Title Modal -->
    <DModal v-if="showEditTitleModal" titel="Edit Document Title" confirm-text="Save" @close="closeEditTitleModal"
        @confirm="confirmEditTitle">
        <div class="p-4">
            <label for="edit-title" class="block mb-2 font-medium">Document Title:</label>
            <input id="edit-title" type="text" v-model="editingTitle" class="w-full border rounded px-3 py-2 text-sm"
                placeholder="Enter new title" @keyup.enter="confirmEditTitle" />
        </div>
    </DModal>

    <!-- Add to Repository Modal -->
    <DModal v-if="showAddToRepoModal" titel="Add to different repository" confirm-text="Add"
        @close="closeAddToRepoModal" @confirm="confirmAddToRepo">
        <div class="p-4 space-y-3">
            <p class="text-sm">Select a repository to add "{{ linkDocumentTitle }}" to:</p>
            <div v-if="availableTargetRepositories.length > 0">
                <select v-model="selectedTargetRepositoryId" class="w-full border rounded px-3 py-2 text-sm">
                    <option v-for="repo in availableTargetRepositories" :key="repo.id" :value="repo.id">
                        {{ repo.name }}
                    </option>
                </select>
            </div>
            <div v-else class="text-sm text-gray-500">
                No other repositories available.
            </div>
        </div>
    </DModal>
</template>