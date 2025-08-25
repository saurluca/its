<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from "vue";
import { PlusIcon, UploadIcon, ChevronDownIcon, ChevronRightIcon, PencilIcon, TrashIcon, BookOpenIcon, ClipboardList } from "lucide-vue-next";
import type { Repository, Document } from "~/types/models";
import { useNotificationsStore } from "~/stores/notifications";

const { $authFetch } = useAuthenticatedFetch();

// View state
const repositories = ref<Repository[]>([]);
const loading = ref(true);
const editingRepository = ref<Repository | null>(null);
const expandedRepositories = ref<Set<string>>(new Set());

// Create repository modal state
const showCreateRepositoryModal = ref(false);
const newRepositoryName = ref("");

// Modal state for repository editing
const showEditTitleModal = ref(false);
const editingRepositoryId = ref<string | null>(null);
const editingTitle = ref("");
const showDeleteModal = ref(false);
const deleteRepositoryId = ref<string | null>(null);
const deleteRepositoryName = ref<string | null>(null);

// HTML viewer state
const showHtmlViewer = ref(false);
const htmlContent = ref("");
const loadingHtml = ref(false);
const htmlError = ref("");
const selectedDocumentId = ref<string | null>(null);

// Upload state
const uploading = ref(false);
const selectedRepositories = ref<string[]>([]);
const fileInput = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);
const showUploadModal = ref(false);
const flattenPdf = ref(false);

// Computed property to check if upload is allowed
const canUpload = computed(() => {
    return selectedRepositories.value.length > 0;
});

const notifications = useNotificationsStore();

type AccessLevel = "read" | "write" | "owner";

function hasWriteAccess(repository: Repository & { access_level?: AccessLevel }) {
    const level = repository.access_level;
    return level === "write" || level === "owner";
}

// Load repositories on component mount
onMounted(async () => {
    await fetchRepositories();
    window.addEventListener("keydown", handleKeyDown);
});

onBeforeUnmount(() => {
    window.removeEventListener("keydown", handleKeyDown);
});

async function fetchRepositories() {
    loading.value = true;
    try {
        const response = await $authFetch("/repositories/") as { repositories?: Repository[] } | Repository[];
        repositories.value = ('repositories' in response ? response.repositories : response) as Repository[];
    } catch (error) {
        console.error("Error fetching repositories:", error);
        notifications.error("Failed to load repositories. Please try again. " + error);
    } finally {
        loading.value = false;
    }
}

async function createRepository(repositoryName: string) {
    try {
        const newRepository = await $authFetch("/repositories/", {
            method: "POST",
            body: { name: repositoryName },
        }) as Repository;

        // Insert the new repository in alphabetical order by name
        const compareByName = (a: Repository, b: Repository) =>
            a.name.localeCompare(b.name, undefined, { sensitivity: "base" });

        const insertIndex = repositories.value.findIndex((r) => compareByName(newRepository, r) < 0);
        if (insertIndex === -1) {
            repositories.value.push(newRepository);
        } else {
            repositories.value.splice(insertIndex, 0, newRepository);
        }
        closeCreateRepositoryModal();
    } catch (error) {
        console.error("Error creating repository:", error);
        notifications.error("Failed to create repository. Please try again. " + error);
    }
}

async function deleteRepository(id: string) {
    try {
        await $authFetch(`/repositories/${id}/`, {
            method: "DELETE",
        });

        repositories.value = repositories.value.filter((r) => r.id !== id);
    } catch (error) {
        console.error("Error deleting repository:", error);
        notifications.error("Failed to delete repository. Please try again. " + error);
    }
}

function cancelEdit() {
    editingRepository.value = null;
}

// Create repository modal functions
function openCreateRepositoryModal() {
    showCreateRepositoryModal.value = true;
    newRepositoryName.value = "";
}

function closeCreateRepositoryModal() {
    showCreateRepositoryModal.value = false;
    newRepositoryName.value = "";
}

function confirmCreateRepository() {
    if (!newRepositoryName.value.trim()) {
        notifications.warning("Please enter a repository name.");
        return;
    }
    createRepository(newRepositoryName.value.trim());
}

function handleKeyDown(event: KeyboardEvent) {
    if (event.key === "Escape" && editingRepository.value) {
        cancelEdit();
    }
}

function navigateToStudy(repositoryId: string) {
    const repository = repositories.value.find(r => r.id === repositoryId);
    if (repository && (repository.task_count === undefined || repository.task_count === 0)) {
        notifications.warning(
            `No tasks available for "${repository.name}". Please generate tasks first by clicking the Tasks button.`,
            3000
        );
        return;
    }
    navigateTo(`/study?repositoryId=${repositoryId}`);
}

function navigateToTasks(repositoryId: string) {
    navigateTo(`/tasks?repositoryId=${repositoryId}`);
}

function toggleRepositoryExpansion(repositoryId: string) {
    if (expandedRepositories.value.has(repositoryId)) {
        expandedRepositories.value.delete(repositoryId);
    } else {
        expandedRepositories.value.add(repositoryId);
    }
}

function openUploadModal() {
    showUploadModal.value = true;
}

function openUploadModalForRepository(repository: Repository) {
    selectedRepositories.value = [repository.id];
    showUploadModal.value = true;
}

function closeUploadModal() {
    showUploadModal.value = false;
    selectedRepositories.value = [];
    selectedFile.value = null;
    flattenPdf.value = false;
}

function triggerFilePicker() {
    if (uploading.value || !canUpload.value) return;
    fileInput.value?.click();
}

function handleFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
        selectedFile.value = input.files[0] || null;
        // Automatically start upload when file is selected
        handleUpload();
    }
}

async function handleUpload() {
    if (uploading.value || !selectedFile.value || !canUpload.value) {
        if (!canUpload.value) {
            notifications.warning("Please select at least one repository before uploading a document.");
        }
        return;
    }

    // Capture file data before closing modal
    const file = selectedFile.value;
    const fileName = file.name;
    const selectedRepos = [...selectedRepositories.value];
    const shouldFlatten = flattenPdf.value;

    // Close modal immediately and show processing notification
    closeUploadModal();

    // Show processing notification
    const processingId = notifications.loading(`Processing document "${fileName}". This may take a while.`);

    try {
        const formData = new FormData();
        formData.append("file", file);

        // Upload the document
        const uploadUrl = `/documents/upload${shouldFlatten ? "?flatten_pdf=true" : ""}`;
        const uploadResponse = await $authFetch(uploadUrl, {
            method: "POST",
            body: formData,
        }) as { id: string };

        // Add document to selected repositories
        if (selectedRepos.length > 0) {
            const documentId = uploadResponse.id;

            for (const repositoryId of selectedRepos) {
                await $authFetch("/repositories/links", {
                    method: "POST",
                    body: {
                        repository_id: repositoryId,
                        document_id: documentId,
                    },
                });
            }
        }

        // Remove processing notification and show success
        notifications.remove(processingId);
        notifications.success(`Document "${fileName}" uploaded successfully!`);
        await fetchRepositories();
    } catch (error) {
        console.error("Error uploading document:", error);
        // Remove processing notification and show error
        notifications.remove(processingId);
        notifications.error(`Failed to upload "${fileName}". Please try again. ${error}`);
    }
}

// Modal functions for repository editing
function openEditTitleModal(repositoryId: string, currentTitle: string) {
    editingRepositoryId.value = repositoryId;
    editingTitle.value = currentTitle;
    showEditTitleModal.value = true;
}

function closeEditTitleModal() {
    showEditTitleModal.value = false;
    editingRepositoryId.value = null;
    editingTitle.value = "";
}

async function confirmEditTitle() {
    if (!editingRepositoryId.value || !editingTitle.value.trim()) return;

    try {
        await $authFetch(`/repositories/${editingRepositoryId.value}`, {
            method: "PUT",
            body: { name: editingTitle.value.trim() },
        });

        // Refresh the repository list to show the updated title
        await fetchRepositories();
        closeEditTitleModal();
    } catch (error) {
        console.error("Error updating title:", error);
        notifications.error("Failed to update title. Please try again. " + error);
    }
}

function openDeleteModal(repositoryId: string, repositoryName: string) {
    showDeleteModal.value = true;
    deleteRepositoryId.value = repositoryId;
    deleteRepositoryName.value = repositoryName;
}

function closeDeleteModal() {
    showDeleteModal.value = false;
    deleteRepositoryId.value = null;
    deleteRepositoryName.value = null;
}

async function confirmDelete() {
    if (!deleteRepositoryId.value) return;
    await deleteRepository(deleteRepositoryId.value);
    closeDeleteModal();
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
        const data = await $authFetch(`/documents/${documentId}`) as Document;

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
    <div class="h-full flex">
        <!-- Left side - Repositories list -->
        <div :class="showHtmlViewer ? 'w-1/2 overflow-y-auto mr-2 ml-6 my-8' : 'w-full mt-8'">
            <div class="max-w-4xl mx-auto">
                <DPageHeader title="Repositories" />

                <div v-if="loading" class="py-20 text-center">
                    <div class="text-xl">Loading repositories...</div>
                </div>

                <div v-else class="space-y-6">
                    <div class="flex flex-col gap-3">
                        <DButtonLabelled title="Repository" :icon="PlusIcon" @click="openCreateRepositoryModal">
                            Create a new repository, to organize your documents and tasks in. It's similar to a folder.
                        </DButtonLabelled>
                        <div class="border-t border-gray-200"></div>
                        <DButtonLabelled title="Document" :icon="UploadIcon" @click="openUploadModal">
                            Upload a document to a repository. Its content will be extracted and can be used for
                            task generation.
                        </DButtonLabelled>
                    </div>
                    <div v-if="repositories.length > 0" class="space-y-4">
                        <div v-for="repository in repositories" :key="repository.id"
                            class="bg-white p-4 rounded-lg shadow border border-gray-200">
                            <div class="flex justify-between items-center">
                                <div class="flex items-center gap-2">
                                    <button @click="toggleRepositoryExpansion(repository.id)"
                                        class="p-1 hover:bg-gray-100 rounded">
                                        <ChevronDownIcon v-if="expandedRepositories.has(repository.id)"
                                            class="h-4 w-4" />
                                        <ChevronRightIcon v-else class="h-4 w-4" />
                                    </button>
                                    <div class="flex flex-col">
                                        <h3 class="text-lg font-medium cursor-pointer"
                                            @click="toggleRepositoryExpansion(repository.id)">
                                            {{ repository.name }}
                                        </h3>
                                        <span v-if="repository.task_count !== undefined"
                                            class="text-xs font-medium text-gray-500">
                                            {{ repository.task_count }} {{ repository.task_count === 1 ? 'task' :
                                                'tasks' }}
                                        </span>
                                    </div>
                                </div>
                                <div class="flex gap-2">
                                    <DButton v-if="hasWriteAccess(repository)" @click="navigateToTasks(repository.id)"
                                        variant="primary" :icon-left="ClipboardList">
                                        Tasks
                                    </DButton>
                                    <DButton @click="navigateToStudy(repository.id)"
                                        :variant="hasWriteAccess(repository) ? 'tertiary' : 'primary'"
                                        :icon-left="BookOpenIcon">
                                        Study
                                    </DButton>
                                    <DButton v-if="hasWriteAccess(repository)"
                                        @click="openUploadModalForRepository(repository)" variant="tertiary"
                                        :icon-left="UploadIcon" class="!p-2" />
                                    <DHamburgerMenu v-if="hasWriteAccess(repository)">
                                        <template #default="{ close }">
                                            <button @click="
                                                openEditTitleModal(repository.id, repository.name);
                                            close();
                                            "
                                                class="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                                <PencilIcon class="h-4 w-4" />
                                                Edit Name
                                            </button>
                                            <div class="border-t border-gray-200 my-1"></div>
                                            <button @click="
                                                openDeleteModal(repository.id, repository.name);
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

                            <!-- Expanded documents view -->
                            <DRepositoryDocuments v-if="expandedRepositories.has(repository.id)"
                                :repository-id="repository.id" :repository-name="repository.name"
                                @refresh-repositories="fetchRepositories" @view-document="viewDocument" />
                        </div>
                    </div>

                    <div v-else class="bg-white p-6 rounded-lg shadow text-center">
                        <p class="text-gray-500">No repositories have been created yet.</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Right side - HTML viewer -->
        <div v-if="showHtmlViewer" class="w-1/2 relative">
            <div class="h-full p-4">
                <DButtonClose @click="showHtmlViewer = false; selectedDocumentId = null; htmlContent = ''"
                    class="absolute top-2 right-2 z-10" />
                <DHtmlViewer :html-content="htmlContent" :loading="loadingHtml" :error="htmlError" />
            </div>
        </div>

        <!-- Document Upload Modal -->
        <DModal v-if="showUploadModal" titel="Upload Document"
            :confirm-text="uploading ? 'Uploading...' : 'Select File & Upload'" :confirm-icon="UploadIcon"
            :disabled="!canUpload" @close="closeUploadModal" @confirm="triggerFilePicker">
            <div class="p-4 space-y-4">
                <!-- Repository Selection (Required) -->
                <div v-if="repositories.length > 0">
                    <label class="block mb-2 font-medium">
                        Select Repositories <span class="text-red-500">*</span>
                    </label>
                    <div class="space-y-2 max-h-40 overflow-y-auto border rounded border-gray-300 p-2">
                        <label v-for="repository in repositories" :key="repository.id"
                            class="flex items-center gap-2 cursor-pointer hover:bg-gray-100 p-1 rounded text-black">
                            <input type="checkbox" :value="repository.id" v-model="selectedRepositories"
                                class="w-4 h-4 accent-black" style="accent-color: black;" />
                            <span>{{ repository.name }}</span>
                        </label>
                    </div>
                    <p v-if="selectedRepositories.length === 0" class="text-sm text-gray-500 mt-2">
                        You must select at least one repository to upload a document
                    </p>
                </div>

                <div v-else class="text-sm text-gray-500 bg-yellow-50 p-2 rounded border border-yellow-200">
                    <strong>No repositories available.</strong> Create a repository first before uploading documents.
                </div>

                <!-- PDF Flattening Option and File Selection -->
                <div v-if="canUpload" class="text-sm">
                    <label class="flex items-center gap-2 cursor-pointer select-none">
                        <input type="checkbox" v-model="flattenPdf" class="w-3 h-3 accent-black"
                            style="accent-color: black;" />
                        <span>Flatten PDF before text extraction</span>
                    </label>
                    <p class="text-xs text-gray-500">
                        Hint: Enable this if there are problems extracting text from a PDF. It may take longer to
                        process.
                    </p>
                    <input ref="fileInput" type="file" accept="*/*" class="hidden" @change="handleFileSelect" />
                    <div v-if="selectedFile" class="text-sm text-gray-600 bg-gray-50 p-2 rounded">
                        Selected: {{ selectedFile.name }}
                    </div>
                </div>
            </div>
        </DModal>

        <!-- Edit Title Modal -->
        <DModal v-if="showEditTitleModal" titel="Edit Repository Name" confirm-text="Save" @close="closeEditTitleModal"
            @confirm="confirmEditTitle">
            <div class="p-4">
                <label for="edit-title" class="block mb-2 font-medium">Repository Name:</label>
                <input id="edit-title" type="text" v-model="editingTitle"
                    class="w-full border rounded px-3 py-2 text-sm border-gray-200" placeholder="Enter new name"
                    @keyup.enter="confirmEditTitle" />
            </div>
        </DModal>

        <!-- Delete Modal -->
        <DModal v-if="showDeleteModal" titel="Delete Repository" confirm-text="Delete" @close="closeDeleteModal"
            @confirm="confirmDelete">
            <div class="p-4">
                <p>
                    Are you sure you want to delete the repository "{{ deleteRepositoryName }}"?
                </p>
                <p class="mt-2 text-sm text-gray-500">This action cannot be undone.</p>
            </div>
        </DModal>

        <!-- Create Repository Modal -->
        <DModal v-if="showCreateRepositoryModal" titel="Create New Repository" confirm-text="Create Repository"
            @close="closeCreateRepositoryModal" @confirm="confirmCreateRepository">
            <div class="p-4">
                <label for="repository-name" class="block mb-2 font-medium">Repository Name:</label>
                <input id="repository-name" type="text" v-model="newRepositoryName"
                    class="w-full border rounded-lg px-3 py-2 text-sm border-gray-200"
                    placeholder="Enter repository name" @keyup.enter="confirmCreateRepository" />
            </div>
        </DModal>
    </div>
</template>