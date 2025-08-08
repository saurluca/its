<script setup lang="ts">
import { ref, onMounted } from "vue";
import { PlusIcon, UploadIcon, ChevronDownIcon, ChevronRightIcon, PencilIcon, TrashIcon, BookOpenIcon, EyeIcon, FileTextIcon } from "lucide-vue-next";
import type { Repository, Document } from "~/types/models";

const { $authFetch } = useAuthenticatedFetch();

// View state
const repositories = ref<Repository[]>([]);
const loading = ref(true);
const showForm = ref(false);
const editingRepository = ref<Repository | null>(null);
const showUploadModal = ref(false);
const expandedRepositories = ref<Set<string>>(new Set());

// Modal state for repository editing
const showEditTitleModal = ref(false);
const editingRepositoryId = ref<string | null>(null);
const editingTitle = ref("");
const showDeleteModal = ref(false);
const deleteRepositoryId = ref<string | null>(null);
const deleteRepositoryName = ref<string | null>(null);

// Generate tasks modal state
const showGenerateTasksModal = ref(false);
const generatingTasks = ref(false);
const selectedRepositoryForTasks = ref<Repository | null>(null);
const repositoryDocuments = ref<Document[]>([]);
const selectedDocuments = ref<Set<string>>(new Set());
const numTasksToGenerate = ref(5);
const taskType = ref<"multiple_choice" | "free_text">("multiple_choice");

// HTML viewer state
const showHtmlViewer = ref(false);
const htmlContent = ref("");
const loadingHtml = ref(false);
const htmlError = ref("");
const selectedDocumentId = ref<string | null>(null);

// Load repositories on component mount
onMounted(async () => {
    await fetchRepositories();
});

async function fetchRepositories() {
    loading.value = true;
    try {
        console.log("fetching repositories");
        const response = await $authFetch("/repositories/") as any;
        console.log("response", response);
        repositories.value = (response.repositories || response) as Repository[];
    } catch (error) {
        console.error("Error fetching repositories:", error);
        alert("Failed to load repositories. Please try again. " + error);
    } finally {
        loading.value = false;
    }
}

async function createRepository(repositoryData: Partial<Repository>) {
    try {
        const newRepository = await $authFetch("/repositories/", {
            method: "POST",
            body: repositoryData,
        }) as Repository;

        repositories.value.push(newRepository);
        showForm.value = false;
    } catch (error) {
        console.error("Error creating repository:", error);
        alert("Failed to create repository. Please try again. " + error);
    }
}

async function updateRepository(repositoryData: Repository) {
    try {
        const updatedRepository = await $authFetch(`/repositories/${repositoryData.id}/`, {
            method: "PUT",
            body: repositoryData,
        }) as Repository;

        const index = repositories.value.findIndex((r) => r.id === updatedRepository.id);
        if (index !== -1) {
            repositories.value[index] = updatedRepository;
        }

        editingRepository.value = null;
    } catch (error) {
        console.error("Error updating repository:", error);
        alert("Failed to update repository. Please try again. " + error);
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
        alert("Failed to delete repository. Please try again. " + error);
    }
}

function handleSave(repositoryData: Partial<Repository>) {
    if (editingRepository.value) {
        updateRepository({ ...editingRepository.value, ...repositoryData });
    } else {
        createRepository(repositoryData);
    }
}

function editRepository(repository: Repository) {
    editingRepository.value = repository;
    showForm.value = true;
}

function cancelEdit() {
    editingRepository.value = null;
    showForm.value = false;
}

function navigateToStudy(repositoryId: string) {
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

function closeUploadModal() {
    showUploadModal.value = false;
}

function handleUploadComplete() {
    fetchRepositories();
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
        await $authFetch(`/repositories/${editingRepositoryId.value}/`, {
            method: "PUT",
            body: { name: editingTitle.value.trim() },
        });

        // Refresh the repository list to show the updated title
        await fetchRepositories();
        closeEditTitleModal();
    } catch (error) {
        console.error("Error updating title:", error);
        alert("Failed to update title. Please try again. " + error);
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

// Generate tasks functions
async function openGenerateTasksModal(repository: Repository) {
    selectedRepositoryForTasks.value = repository;
    selectedDocuments.value.clear();
    numTasksToGenerate.value = 5;
    taskType.value = "multiple_choice";

    // Fetch documents for this repository
    try {
        const data = await $authFetch(`/repositories/${repository.id}/documents/`) as any;
        repositoryDocuments.value = data.map((doc: any) => ({
            id: doc.id,
            title: doc.title,
            content: doc.content,
            created_at: new Date(doc.created_at),
            deleted_at: doc.deleted_at ? new Date(doc.deleted_at) : null,
            repository_ids: doc.repository_ids || [],
            source_file: doc.source_file,
        }));
    } catch (error) {
        console.error("Error fetching repository documents:", error);
        alert("Failed to load repository documents. Please try again.");
        return;
    }

    showGenerateTasksModal.value = true;
}

function closeGenerateTasksModal() {
    showGenerateTasksModal.value = false;
    selectedRepositoryForTasks.value = null;
    repositoryDocuments.value = [];
    selectedDocuments.value.clear();
}


async function confirmGenerateTasks() {
    if (!selectedRepositoryForTasks.value || selectedDocuments.value.size === 0) {
        alert("Please select at least one document to generate tasks from.");
        return;
    }

    generatingTasks.value = true;
    try {
        const documentIds = Array.from(selectedDocuments.value);

        await $authFetch("/tasks/generate_for_multiple_documents", {
            method: "POST",
            body: {
                repository_id: selectedRepositoryForTasks.value.id,
                document_ids: documentIds,
                num_tasks: numTasksToGenerate.value,
                task_type: taskType.value,
            },
        });

        closeGenerateTasksModal();
        // Refresh repositories to show updated task counts
        await fetchRepositories();
        alert("Tasks generated successfully!");
    } catch (error) {
        console.error("Error generating tasks:", error);
        alert("Failed to generate tasks. Please try again. " + error);
    } finally {
        generatingTasks.value = false;
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
        const data = await $authFetch(`/documents/${documentId}/`) as any;

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
        <div :class="showHtmlViewer ? 'w-1/2 p-4 overflow-y-auto ml-2' : 'w-full p-4 ml-2'">
            <div class="max-w-4xl mx-auto">
                <div class="flex justify-between items-center mb-8">
                    <h1 class="text-3xl font-bold">Repositories</h1>
                </div>

                <div v-if="loading" class="py-20 text-center">
                    <div class="text-xl">Loading repositories...</div>
                </div>

                <div v-else class="space-y-6">
                    <div v-if="!showForm" class="flex gap-3">
                        <DButton @click="openUploadModal" variant="primary" :iconLeft="UploadIcon">
                            Document
                        </DButton>
                        <DButton @click="showForm = true" variant="secondary" :iconLeft="PlusIcon">
                            Repository
                        </DButton>
                    </div>

                    <DItemForm v-if="showForm" :title="editingRepository ? 'Edit Repository' : 'Create New Repository'"
                        :item="editingRepository || undefined" :is-edit="!!editingRepository" @save="handleSave"
                        @cancel="cancelEdit" />

                    <div v-if="repositories.length > 0" class="space-y-4">
                        <div v-for="repository in repositories" :key="repository.id"
                            class="bg-white p-4 rounded-lg shadow border border-gray-100">
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
                                    <DButton @click="navigateToStudy(repository.id)" variant="primary"
                                        :iconLeft="BookOpenIcon">
                                        Study
                                    </DButton>
                                    <DButton @click="openGenerateTasksModal(repository)" variant="tertiary"
                                        :iconLeft="PlusIcon" class="!p-2" />
                                    <DHamburgerMenu>
                                        <template #default="{ close }">
                                            <button @click="
                                                navigateToTasks(repository.id);
                                            close();
                                            "
                                                class="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                                <EyeIcon class="h-4 w-4" />
                                                View Tasks
                                            </button>
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
        <div v-if="showHtmlViewer" class="w-1/2 ">
            <div class="h-full p-4">
                <DHtmlViewer :html-content="htmlContent" :loading="loadingHtml" :error="htmlError" />
            </div>
        </div>
    </div>

    <!-- Document Upload Modal -->
    <DDocumentUploadModal v-if="showUploadModal" :repositories="repositories" @close="closeUploadModal"
        @upload-complete="handleUploadComplete" />

    <!-- Edit Title Modal -->
    <DModal v-if="showEditTitleModal" titel="Edit Repository Name" confirmText="Save" @close="closeEditTitleModal"
        @confirm="confirmEditTitle">
        <div class="p-4">
            <label for="edit-title" class="block mb-2 font-medium">Repository Name:</label>
            <input id="edit-title" type="text" v-model="editingTitle" class="w-full border rounded px-3 py-2 text-sm"
                placeholder="Enter new name" @keyup.enter="confirmEditTitle" />
        </div>
    </DModal>

    <!-- Delete Modal -->
    <DModal v-if="showDeleteModal" titel="Delete Repository" confirmText="Delete" @close="closeDeleteModal"
        @confirm="confirmDelete">
        <div class="p-4">
            <p>
                Are you sure you want to delete the repository "{{ deleteRepositoryName }}"?
            </p>
            <p class="mt-2 text-sm text-gray-500">This action cannot be undone.</p>
        </div>
    </DModal>

    <!-- Generate Tasks Modal -->
    <DModal v-if="showGenerateTasksModal" titel="Generate Tasks"
        :confirmText="generatingTasks ? 'Generating...' : 'Generate Tasks'" :wide="true"
        @close="closeGenerateTasksModal" @confirm="confirmGenerateTasks">
        <div class="p-4 space-y-4">
            <!-- Task Generation Settings -->
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label for="num-tasks" class="block mb-2 font-medium">Number of tasks:</label>
                    <input id="num-tasks" type="number" min="1" max="50" v-model.number="numTasksToGenerate"
                        class="w-full border rounded px-3 py-2 text-sm" />
                </div>
                <div>
                    <label for="task-type" class="block mb-2 font-medium">Task type:</label>
                    <select id="task-type" v-model="taskType" class="w-full border rounded px-3 py-2 text-sm">
                        <option value="multiple_choice">Multiple Choice</option>
                        <option value="free_text">Free Text</option>
                    </select>
                </div>
            </div>

            <!-- Document Selection -->
            <div>
                <label class="block mb-2 font-medium">Select documents to generate tasks from:</label>
                <div class="space-y-2 max-h-60 overflow-y-auto border rounded p-2">
                    <div v-if="repositoryDocuments.length === 0" class="text-center text-gray-500 py-4">
                        No documents found in this repository.
                    </div>
                    <label v-for="document in repositoryDocuments" :key="document.id"
                        class="flex items-center gap-2 cursor-pointer hover:bg-gray-100 p-1 rounded text-black">
                        <input type="checkbox" :value="document.id" v-model="selectedDocuments"
                            class="w-4 h-4 accent-black" style="accent-color: black;" />
                        <span>{{ document.title }}</span>
                    </label>
                </div>
            </div>

            <!-- Summary -->
            <div v-if="selectedDocuments.size > 0" class="text-sm text-gray-600">
                <p>Will generate {{ numTasksToGenerate }} {{ taskType === 'multiple_choice' ? 'multiple choice' :
                    'free text' }} tasks from {{ selectedDocuments.size }} selected document
                    {{ selectedDocuments.size === 1 ? '' : 's' }}.</p>
                <p>Tasks will be linked to the repository "{{ selectedRepositoryForTasks?.name }}".</p>
            </div>
        </div>
    </DModal>
</template>