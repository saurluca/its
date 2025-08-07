<script setup lang="ts">
import { ref, onMounted } from "vue";
import { PlusIcon, UploadIcon, ChevronDownIcon, ChevronRightIcon, PencilIcon, TrashIcon, BookOpenIcon } from "lucide-vue-next";
import type { Repository } from "~/types/models";

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
</script>

<template>
    <div class="max-w-6xl mx-auto px-4 py-8">
        <div class="flex justify-between items-center mb-8">
            <h1 class="text-3xl font-bold">Repositories</h1>
        </div>

        <div v-if="loading" class="py-20 text-center">
            <div class="text-xl">Loading repositories...</div>
        </div>

        <div v-else class="space-y-8">
            <div v-if="!showForm" class="flex gap-4">
                <DButton @click="showForm = true" variant="primary" :iconLeft="PlusIcon">
                    New Repository
                </DButton>
                <DButton @click="openUploadModal" variant="secondary" :iconLeft="UploadIcon">
                    Upload Document
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
                                <ChevronDownIcon v-if="expandedRepositories.has(repository.id)" class="h-4 w-4" />
                                <ChevronRightIcon v-else class="h-4 w-4" />
                            </button>
                            <div class="flex items-center gap-2">
                                <h3 class="text-lg font-medium cursor-pointer"
                                    @click="toggleRepositoryExpansion(repository.id)">
                                    {{ repository.name }}
                                </h3>
                                <span v-if="repository.task_count !== undefined" 
                                      class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                    {{ repository.task_count }} {{ repository.task_count === 1 ? 'task' : 'tasks' }}
                                </span>
                            </div>
                        </div>
                        <div class="flex gap-2">
                            <DButton @click="navigateToStudy(repository.id)" variant="primary" :iconLeft="BookOpenIcon">
                                Study
                            </DButton>

                            <DHamburgerMenu>
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

                    <!-- Repository info section -->
                    <div v-if="repository.task_count !== undefined" class="mt-3 pt-3 border-t border-gray-100">
                        <div class="flex items-center gap-4 text-sm text-gray-600">
                            <div class="flex items-center gap-1">
                                <BookOpenIcon class="h-4 w-4" />
                                <span>{{ repository.task_count }} {{ repository.task_count === 1 ? 'task' : 'tasks' }} available</span>
                            </div>
                        </div>
                    </div>

                    <!-- Expanded documents view -->
                    <DRepositoryDocuments v-if="expandedRepositories.has(repository.id)" :repository-id="repository.id"
                        :repository-name="repository.name" @refresh-repositories="fetchRepositories" />
                </div>
            </div>

            <div v-else class="bg-white p-6 rounded-lg shadow text-center">
                <p class="text-gray-500">No repositories have been created yet.</p>
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
</template>