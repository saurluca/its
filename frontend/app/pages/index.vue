<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";
import { useLocalStorage } from "@vueuse/core";
import { PlusIcon, PencilIcon, TrashIcon, LogOutIcon, UsersIcon } from "lucide-vue-next";
import type { Repository } from "~/types/models";
import { useNotificationsStore } from "~/stores/notifications";

const { $authFetch } = useAuthenticatedFetch();

// View state
const repositories = ref<Repository[]>([]);
const loading = ref(true);
const editingRepository = ref<Repository | null>(null);

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


// Leave repository modal state
const showLeaveModal = ref(false);
const leaveRepositoryId = ref<string | null>(null);
const leaveRepositoryName = ref<string | null>(null);

// HTML viewer and document expansion removed from index page

// (Upload to repository is handled in repository.vue)

const notifications = useNotificationsStore();

type AccessLevel = "read" | "write" | "owner";

function hasWriteAccess(repository: Repository & { access_level?: AccessLevel }) {
    const level = repository.access_level;
    return level === "write" || level === "owner";
}

function isOwner(repository: Repository & { access_level?: AccessLevel }) {
    return repository.access_level === "owner";
}

// Cache access levels for quick lookups in other views (e.g., repository.vue)
const repositoryAccessLevels = useLocalStorage<Record<string, AccessLevel>>("repository_access_levels", {});

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
        const response = await $authFetch("/repositories") as { repositories?: Repository[] } | Repository[];
        const list = ('repositories' in response ? response.repositories : response) as (Repository & { access_level?: AccessLevel })[];
        repositories.value = list;
        // Persist access levels for use by other views before their own fetch completes
        const levels: Record<string, AccessLevel> = { ...repositoryAccessLevels.value };
        for (const r of list) {
            if (r.id && r.access_level) {
                levels[r.id] = r.access_level;
            }
        }
        repositoryAccessLevels.value = levels;
    } catch (error) {
        console.error("Error fetching repositories:", error);
        notifications.error("Failed to load repositories. Please try again. " + error);
    } finally {
        loading.value = false;
    }
}

async function createRepository(repositoryName: string) {
    try {
        const newRepository = await $authFetch("/repositories", {
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
        // Notify other components (e.g., sidebar) that repositories changed
        if (typeof window !== "undefined") {
            window.dispatchEvent(new CustomEvent("repositories:updated"));
        }
    } catch (error) {
        console.error("Error creating repository:", error);
        notifications.error("Failed to create repository. Please try again. " + error);
    }
}

async function deleteRepository(id: string) {
    try {
        await $authFetch(`/repositories/${id}`, {
            method: "DELETE",
        });

        repositories.value = repositories.value.filter((r) => r.id !== id);
        // Notify other components (e.g., sidebar) that repositories changed
        if (typeof window !== "undefined") {
            window.dispatchEvent(new CustomEvent("repositories:updated"));
        }
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

function navigateToRepository(repositoryId: string) {
    navigateTo(`/repository?repositoryId=${repositoryId}`);
}

function navigateToManagement(repositoryId: string) {
    navigateTo(`/management?repositoryId=${repositoryId}`);
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
        // Notify other components (e.g., sidebar) that repositories changed
        if (typeof window !== "undefined") {
            window.dispatchEvent(new CustomEvent("repositories:updated"));
        }
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

// Leave repository functions
function openLeaveModal(repositoryId: string, repositoryName: string) {
    leaveRepositoryId.value = repositoryId;
    leaveRepositoryName.value = repositoryName;
    showLeaveModal.value = true;
}

function closeLeaveModal() {
    showLeaveModal.value = false;
    leaveRepositoryId.value = null;
    leaveRepositoryName.value = null;
}

async function confirmLeave() {
    if (!leaveRepositoryId.value) return;
    try {
        const response = await $authFetch(`/repositories/${leaveRepositoryId.value}/leave`, {
            method: "DELETE",
        }) as { ok: boolean; repository_deleted: boolean };

        if (response.repository_deleted) {
            notifications.success("Repository was deleted as you were the last member.");
        } else {
            notifications.success("You have left the repository.");
        }

        closeLeaveModal();
        await fetchRepositories();

        // Notify other components (e.g., sidebar) that repositories changed
        if (typeof window !== "undefined") {
            window.dispatchEvent(new CustomEvent("repositories:updated"));
        }
    } catch (error) {
        console.error("Error leaving repository:", error);
        notifications.error("Failed to leave repository. Please try again.");
    }
}

// Document viewing and HTML panel logic removed
</script>

<template>
    <div class="h-full flex">
        <!-- Repositories list -->
        <div class="w-full mt-8">
            <div class="max-w-4xl mx-auto">
                <DPageHeader title="Repositories" />

                <div v-if="loading" class="py-20 text-center">
                    <div class="text-xl">Loading repositories...</div>
                </div>

                <div v-else class="space-y-6">
                    <div class="flex flex-col gap-3 mr-4">
                        <DButtonLabelled title="Repository" :icon="PlusIcon" @click="openCreateRepositoryModal">
                            Create new repository to organize documents and tasks; similar to a folder.
                        </DButtonLabelled>
                        <div class="border-t border-gray-200"></div>
                        <!-- Document upload moved to repository.vue -->
                    </div>
                    <div v-if="repositories.length > 0" class="space-y-4">
                        <div v-for="repository in repositories" :key="repository.id"
                            class="bg-white p-4 rounded-lg shadow border border-gray-200">
                            <div class="flex justify-between items-center">
                                <div class="flex items-center gap-2">
                                    <div class="flex flex-col">
                                        <h3 class="text-lg font-medium cursor-pointer"
                                            @click="navigateToRepository(repository.id)">
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
                                    <!-- Manage Users button - visible to users with write or owner access -->
                                    <DButton v-if="hasWriteAccess(repository)"
                                        @click="navigateToManagement(repository.id)" variant="tertiary"
                                        :icon-left="UsersIcon">
                                        Manage
                                    </DButton>

                                    <!-- Owner-only options -->
                                    <template v-if="isOwner(repository)">
                                        <DButton @click="openEditTitleModal(repository.id, repository.name)"
                                            variant="secondary" :icon-left="PencilIcon">

                                        </DButton>
                                        <DButton @click="openDeleteModal(repository.id, repository.name)"
                                            variant="danger-light" :icon-left="TrashIcon">

                                        </DButton>
                                    </template>

                                    <!-- Non-owner option -->
                                    <template v-else>
                                        <DButton @click="openLeaveModal(repository.id, repository.name)"
                                            variant="danger-light" :icon-left="LogOutIcon">

                                        </DButton>
                                    </template>
                                </div>
                            </div>

                            <!-- Documents expansion removed on index page -->
                        </div>
                    </div>

                    <div v-else class="bg-white p-6 rounded-lg shadow text-center">
                        <p class="text-gray-500">No repositories have been created yet.</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- HTML viewer removed on index page -->

        <!-- Document upload modal moved to repository.vue -->

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

        <!-- Leave Repository Modal -->
        <DModal v-if="showLeaveModal" titel="Leave Repository" confirm-text="Leave" @close="closeLeaveModal"
            @confirm="confirmLeave">
            <div class="p-4">
                <p>
                    Are you sure you want to leave the repository "{{ leaveRepositoryName }}"?
                </p>
                <p class="mt-2 text-sm text-gray-500">
                    If you are the last person with access, the repository will be deleted.
                </p>
            </div>
        </DModal>
    </div>
</template>