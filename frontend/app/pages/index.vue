<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from "vue";
import { PlusIcon, UploadIcon, ChevronDownIcon, ChevronRightIcon, PencilIcon, TrashIcon, BookOpenIcon, ClipboardList, UserPlusIcon } from "lucide-vue-next";
import type { Repository, Document } from "~/types/models";
import { useNotificationsStore } from "~/stores/notifications";
import { SUPPORTED_MIME_TYPES, MAX_FILE_SIZE_MB, MAX_FILE_SIZE_BYTES } from "~/constans/constants";

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

// Invite user modal state
const showInviteModal = ref(false);
const inviteRepositoryId = ref<string | null>(null);
const inviteEmail = ref("");
const inviteAccessLevel = ref<"read" | "write">("read");

// HTML viewer state
const showHtmlViewer = ref(false);
const htmlContent = ref("");
const loadingHtml = ref(false);
const htmlError = ref("");
const selectedDocumentId = ref<string | null>(null);

// (Upload to repository is handled in repository.vue)

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
        const response = await $authFetch("/repositories") as { repositories?: Repository[] } | Repository[];
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

function navigateToRepository(repositoryId: string) {
    navigateTo(`/repository?repositoryId=${repositoryId}`);
}

function toggleRepositoryExpansion(repositoryId: string) {
    if (expandedRepositories.value.has(repositoryId)) {
        expandedRepositories.value.delete(repositoryId);
    } else {
        expandedRepositories.value.add(repositoryId);
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

// Invite user functions
function openInviteModal(repositoryId: string) {
    inviteRepositoryId.value = repositoryId;
    inviteEmail.value = "";
    inviteAccessLevel.value = "read";
    showInviteModal.value = true;
}

function closeInviteModal() {
    showInviteModal.value = false;
    inviteRepositoryId.value = null;
    inviteEmail.value = "";
}

async function confirmInvite() {
    if (!inviteRepositoryId.value) return;
    const email = inviteEmail.value.trim();
    if (!email) {
        notifications.warning("Please enter an email address.");
        return;
    }
    try {
        await $authFetch(`/repositories/${inviteRepositoryId.value}/access`, {
            method: "POST",
            body: { email, access_level: inviteAccessLevel.value },
        });
        notifications.success("If the user exists, access has been granted.");
        closeInviteModal();
        await fetchRepositories();
    } catch (error) {
        console.error("Error granting access:", error);
        notifications.error("Failed to update access. Please try again.");
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
                                    <button @click="toggleRepositoryExpansion(repository.id)"
                                        class="p-1 hover:bg-gray-100 rounded">
                                        <ChevronDownIcon v-if="expandedRepositories.has(repository.id)"
                                            class="h-4 w-4" />
                                        <ChevronRightIcon v-else class="h-4 w-4" />
                                    </button>
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
                                    <DButton v-if="hasWriteAccess(repository)" @click="navigateToTasks(repository.id)"
                                        variant="primary" :icon-left="ClipboardList">
                                        Tasks
                                    </DButton>
                                    <DButton @click="navigateToStudy(repository.id)"
                                        :variant="hasWriteAccess(repository) ? 'tertiary' : 'primary'"
                                        :icon-left="BookOpenIcon">
                                        Study
                                    </DButton>
                                    <!-- Upload button moved to repository.vue -->
                                    <DHamburgerMenu v-if="hasWriteAccess(repository)">
                                        <template #default="{ close }">
                                            <button @click="
                                                openInviteModal(repository.id);
                                            close();
                                            "
                                                class="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                                <UserPlusIcon class="h-4 w-4" />
                                                Invite User
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
                                :access-level="(repository as Repository & { access_level?: AccessLevel }).access_level"
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

        <!-- Invite User Modal -->
        <DModal v-if="showInviteModal" titel="Invite User" confirm-text="Invite" @close="closeInviteModal"
            @confirm="confirmInvite">
            <div class="p-4 space-y-4">
                <div>
                    <label for="invite-email" class="block mb-2 font-medium">User Email</label>
                    <input id="invite-email" type="email" v-model="inviteEmail"
                        class="w-full border rounded px-3 py-2 text-sm border-gray-200"
                        placeholder="name@example.com" />
                </div>
                <div>
                    <label class="block mb-2 font-medium">Access Level</label>
                    <div class="flex gap-4 text-sm">
                        <label class="inline-flex items-center gap-2 cursor-pointer">
                            <input type="radio" value="read" v-model="inviteAccessLevel" class="accent-black"
                                style="accent-color: black;" />
                            <span>Read</span>
                        </label>
                        <label class="inline-flex items-center gap-2 cursor-pointer">
                            <input type="radio" value="write" v-model="inviteAccessLevel" class="accent-black"
                                style="accent-color: black;" />
                            <span>Write</span>
                        </label>
                    </div>
                    <p class="text-xs text-gray-500 mt-1">Owners are set when creating repositories and cannot be
                        invited here.</p>
                </div>
            </div>
        </DModal>
    </div>
</template>