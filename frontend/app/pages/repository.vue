<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from "vue";
import { useRoute } from "vue-router";
import { ClipboardList, PencilIcon, TrashIcon, PlusIcon, BookOpenIcon, UploadIcon } from "lucide-vue-next";
import { SUPPORTED_MIME_TYPES, MAX_FILE_SIZE_MB, MAX_FILE_SIZE_BYTES } from "~/constans/constants";
import { useNotificationsStore } from "~/stores/notifications";
import { useSessionStorage, useLocalStorage } from "@vueuse/core";

const { $authFetch } = useAuthenticatedFetch();
const notifications = useNotificationsStore();
const collapsed = useSessionStorage("collapsed", false);
const repositoryAccessLevels = useLocalStorage<Record<string, AccessLevel>>("repository_access_levels", {});

type UUID = string;

type AccessLevel = "read" | "write" | "owner";

interface RepositoryDetail {
    id: UUID;
    name: string;
    access_level?: AccessLevel;
}

interface UnitListItem {
    id: UUID;
    title: string;
    task_count?: number;
}

interface DocumentItem {
    id: UUID;
    title: string;
    content?: string;
}

interface SkillItem {
    id: UUID;
    name: string;
}

// Route / query
const route = useRoute();
const repositoryId = computed(() => (route.query.repositoryId as string) || "");

// Page state
const loading = ref(true);
const repo = ref<RepositoryDetail | null>(null);

const currentAccessLevel = computed<AccessLevel | undefined>(() => {
    const level = (repo.value as RepositoryDetail | null)?.access_level;
    if (level) return level;
    const id = repositoryId.value;
    console.log("id", id);
    console.log("repositoryAccessLevels.value", repositoryAccessLevels.value);
    return id ? repositoryAccessLevels.value[id] : undefined;
});

const hasWriteAccess = computed(() => {
    const level = currentAccessLevel.value;
    console.log("level", level);
    return level === "write" || level === "owner";
});

// Units state
const units = ref<UnitListItem[]>([]);
const showCreateUnitModal = ref(false);
const newUnitTitle = ref("");

// Documents state & HTML viewer
const documents = ref<DocumentItem[]>([]);
const showHtmlViewer = ref(false);
const htmlContent = ref("");
const loadingHtml = ref(false);
const htmlError = ref("");
const selectedDocumentId = ref<string | null>(null);

// Upload state
const uploading = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);
const showUploadModal = ref(false);
const flattenPdf = ref(false);

// Skills state
const skills = ref<SkillItem[]>([]);
const showAddSkillModal = ref(false);
const newSkillName = ref("");
const showRenameSkillModal = ref(false);
const renamingSkillId = ref<string | null>(null);
const renamingSkillName = ref("");
const showRemoveSkillModal = ref(false);
const removingSkillId = ref<string | null>(null);
const removingSkillName = ref<string | null>(null);

// Units management modals
const showRenameUnitModal = ref(false);
const renamingUnitId = ref<string | null>(null);
const renamingUnitTitle = ref("");
const showDeleteUnitModal = ref(false);
const deletingUnitId = ref<string | null>(null);
const deletingUnitTitle = ref<string | null>(null);

// Documents management modals
const showRenameDocumentModal = ref(false);
const renamingDocumentId = ref<string | null>(null);
const renamingDocumentTitle = ref("");
const showDeleteDocumentModal = ref(false);
const deletingDocumentId = ref<string | null>(null);
const deletingDocumentTitle = ref<string | null>(null);

onMounted(async () => {
    if (!repositoryId.value) {
        notifications.error("Missing repositoryId in URL.");
        return;
    }
    await fetchAll();
});

// React to repositoryId changes when staying on the same route
watch(repositoryId, async (newId, oldId) => {
    if (!newId || newId === oldId) return;
    // Reset view-specific state
    showHtmlViewer.value = false;
    selectedDocumentId.value = null;
    htmlContent.value = "";
    await fetchAll();
});

async function fetchAll() {
    loading.value = true;
    try {
        const [repoResp, unitsResp, docsResp, skillsResp] = await Promise.all([
            $authFetch(`/repositories/${repositoryId.value}`) as Promise<RepositoryDetail>,
            $authFetch(`/repositories/${repositoryId.value}/units`) as Promise<UnitListItem[]>,
            $authFetch(`/repositories/${repositoryId.value}/documents`) as Promise<DocumentItem[]>,
            $authFetch(`/skills/repository/${repositoryId.value}`) as Promise<SkillItem[]>,
        ]);
        // Merge in access level from list endpoint (detail endpoint does not include it)
        let mergedAccessLevel: AccessLevel | undefined = repoResp?.access_level;
        if (repoResp?.id) {
            const levelFromList = await fetchAccessLevelForRepository(repoResp.id);
            mergedAccessLevel = mergedAccessLevel || levelFromList;
            if (mergedAccessLevel) {
                repositoryAccessLevels.value = {
                    ...repositoryAccessLevels.value,
                    [repoResp.id]: mergedAccessLevel,
                };
            }
        }
        repo.value = { ...repoResp, access_level: mergedAccessLevel } as RepositoryDetail;
        units.value = unitsResp || [];
        documents.value = docsResp || [];
        skills.value = (skillsResp || []).sort((a, b) => a.name.localeCompare(b.name));
    } catch (error) {
        console.error("Error loading repository page:", error);
        notifications.error("Failed to load repository data. " + error);
    } finally {
        loading.value = false;
    }
}

onUnmounted(() => {
});

async function fetchAccessLevelForRepository(id: string): Promise<AccessLevel | undefined> {
    try {
        type RepoListItem = { id: string; access_level?: AccessLevel };
        const response = (await $authFetch(`/repositories`)) as RepoListItem[] | { repositories?: RepoListItem[] };
        const list: RepoListItem[] = Array.isArray(response)
            ? response
            : (response?.repositories ?? []);
        const match = list.find((r) => r.id === id);
        return match?.access_level as AccessLevel | undefined;
    } catch (err) {
        console.warn("Failed to fetch repositories list for access level:", err);
        return repositoryAccessLevels.value[id];
    }
}

async function refreshDocuments() {
    try {
        const docsResp = (await $authFetch(`/repositories/${repositoryId.value}/documents`)) as DocumentItem[];
        documents.value = docsResp || [];
    } catch (error) {
        console.error("Error refreshing documents:", error);
    }
}

function navigateToTasksForUnit(unitId: string) {
    navigateTo(`/tasks?unitId=${unitId}`);
}

function navigateToStudyForUnit(unitId: string) {
    navigateTo(`/study?unitId=${unitId}`);
}

function openCreateUnitModal() {
    showCreateUnitModal.value = true;
    newUnitTitle.value = "";
}

function closeCreateUnitModal() {
    showCreateUnitModal.value = false;
    newUnitTitle.value = "";
}

async function refreshUnits() {
    try {
        const unitsResp = (await $authFetch(`/repositories/${repositoryId.value}/units`)) as UnitListItem[];
        units.value = unitsResp || [];
    } catch (error) {
        console.error("Error refreshing units:", error);
    }
}

async function confirmCreateUnit() {
    const title = newUnitTitle.value.trim();
    if (!title) {
        notifications.warning("Please enter a unit title.");
        return;
    }
    try {
        await $authFetch(`/units`, {
            method: "POST",
            body: { title, repository_id: repositoryId.value },
        });
        notifications.success("Unit created.");
        closeCreateUnitModal();
        await refreshUnits();
    } catch (error) {
        console.error("Error creating unit:", error);
        notifications.error("Failed to create unit. " + error);
    }
}

// Unit actions
function openRenameUnitModal(unit: UnitListItem) {
    renamingUnitId.value = unit.id;
    renamingUnitTitle.value = unit.title;
    showRenameUnitModal.value = true;
}

function closeRenameUnitModal() {
    showRenameUnitModal.value = false;
    renamingUnitId.value = null;
    renamingUnitTitle.value = "";
}

async function confirmRenameUnit() {
    if (!renamingUnitId.value || !renamingUnitTitle.value.trim()) return;
    try {
        await $authFetch(`/units/${renamingUnitId.value}`, {
            method: "PUT",
            body: { title: renamingUnitTitle.value.trim() },
        });
        notifications.success("Unit renamed.");
        closeRenameUnitModal();
        await refreshUnits();
    } catch (error) {
        console.error("Error renaming unit:", error);
        notifications.error("Failed to rename unit. " + error);
    }
}

function openDeleteUnitModal(unit: UnitListItem) {
    deletingUnitId.value = unit.id;
    deletingUnitTitle.value = unit.title;
    showDeleteUnitModal.value = true;
}

function closeDeleteUnitModal() {
    showDeleteUnitModal.value = false;
    deletingUnitId.value = null;
    deletingUnitTitle.value = null;
}

async function confirmDeleteUnit() {
    if (!deletingUnitId.value) return;
    try {
        await $authFetch(`/units/${deletingUnitId.value}`, { method: "DELETE" });
        notifications.success("Unit deleted.");
        closeDeleteUnitModal();
        await refreshUnits();
    } catch (error) {
        console.error("Error deleting unit:", error);
        notifications.error("Failed to delete unit. " + error);
    }
}

async function viewDocument(documentId: string) {
    if (selectedDocumentId.value === documentId && showHtmlViewer.value) {
        showHtmlViewer.value = false;
        selectedDocumentId.value = null;
        htmlContent.value = "";
        return;
    }

    loadingHtml.value = true;
    htmlError.value = "";
    selectedDocumentId.value = documentId;
    collapsed.value = true;
    showHtmlViewer.value = true;

    try {
        const data = await $authFetch(`/documents/${documentId}`) as DocumentItem;
        if ("content" in data && data.content) {
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

// Document actions
function openRenameDocumentModal(doc: DocumentItem) {
    renamingDocumentId.value = doc.id;
    renamingDocumentTitle.value = doc.title;
    showRenameDocumentModal.value = true;
}

function closeRenameDocumentModal() {
    showRenameDocumentModal.value = false;
    renamingDocumentId.value = null;
    renamingDocumentTitle.value = "";
}

async function confirmRenameDocument() {
    if (!renamingDocumentId.value || !renamingDocumentTitle.value.trim()) return;
    try {
        await $authFetch(`/documents/${renamingDocumentId.value}`, {
            method: "PUT",
            body: { title: renamingDocumentTitle.value.trim() },
        });
        notifications.success("Document renamed.");
        closeRenameDocumentModal();
        await refreshDocuments();
    } catch (error) {
        console.error("Error renaming document:", error);
        notifications.error("Failed to rename document. " + error);
    }
}

function openDeleteDocumentModal(doc: DocumentItem) {
    deletingDocumentId.value = doc.id;
    deletingDocumentTitle.value = doc.title;
    showDeleteDocumentModal.value = true;
}

function closeDeleteDocumentModal() {
    showDeleteDocumentModal.value = false;
    deletingDocumentId.value = null;
    deletingDocumentTitle.value = null;
}

async function confirmDeleteDocument() {
    if (!deletingDocumentId.value) return;
    try {
        await $authFetch(`/documents/${deletingDocumentId.value}`, { method: "DELETE" });
        notifications.success("Document deleted.");
        closeDeleteDocumentModal();
        await refreshDocuments();
    } catch (error) {
        console.error("Error deleting document:", error);
        notifications.error("Failed to delete document. " + error);
    }
}

function closeUploadModal() {
    showUploadModal.value = false;
    selectedFile.value = null;
    flattenPdf.value = false;
}

function triggerFilePicker() {
    // Allow picking multiple files in sequence; do not block on ongoing upload
    fileInput.value?.click();
}

function handleFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
        const file = input.files[0];

        if (!file) {
            notifications.error("No file selected.");
            return;
        }

        const fileName = file.name.toLowerCase();
        const fileExtension = fileName.split('.').pop() || '';

        if (!SUPPORTED_MIME_TYPES.includes(fileExtension)) {
            notifications.error(`Unsupported file type. Supported formats: ${SUPPORTED_MIME_TYPES.join(', ')}`);
            input.value = '';
            return;
        }

        if (file.size > MAX_FILE_SIZE_BYTES) {
            notifications.error(`File size exceeds ${MAX_FILE_SIZE_MB}MB limit. Please choose a smaller file.`);
            input.value = '';
            return;
        }

        selectedFile.value = file;
        showUploadModal.value = true;
    }
}

async function handleUpload() {
    if (uploading.value || !selectedFile.value) return;

    const file = selectedFile.value;
    const fileName = file.name;
    const shouldFlatten = flattenPdf.value;

    closeUploadModal();

    const processingId = notifications.loading(`Processing document "${fileName}". This may take a while.`);

    try {
        uploading.value = true;
        const formData = new FormData();
        formData.append("file", file);

        const uploadUrl = `/documents/upload${shouldFlatten ? "?flatten_pdf=true" : ""}`;
        const uploadResponse = await $authFetch(uploadUrl, {
            method: "POST",
            body: formData,
        }) as { id: string };

        const documentId = uploadResponse.id;
        await $authFetch("/repositories/links", {
            method: "POST",
            body: {
                repository_id: repositoryId.value,
                document_id: documentId,
            },
        });

        notifications.remove(processingId);
        notifications.success(`Document "${fileName}" uploaded successfully!`);
        await refreshDocuments();
    } catch (error) {
        console.error("Error uploading document:", error);
        notifications.remove(processingId);
        notifications.error(`Failed to upload "${fileName}". Please try again. ${error}`);
    } finally {
        uploading.value = false;
        selectedFile.value = null;
    }
}

// Polling removed; upload is processed inline

// // Skills actions
// function openAddSkillModal() {
//     showAddSkillModal.value = true;
//     newSkillName.value = "";
// }

function closeAddSkillModal() {
    showAddSkillModal.value = false;
    newSkillName.value = "";
}

async function confirmAddSkill() {
    const name = newSkillName.value.trim();
    if (!name) {
        notifications.warning("Please enter a skill name.");
        return;
    }
    try {
        // Try to create the skill first
        let skill: SkillItem | null = null;
        try {
            skill = (await $authFetch(`/skills`, {
                method: "POST",
                body: { name },
            })) as SkillItem;
        } catch (err: unknown) {
            // If conflict, try to find existing by name
            const msg = err instanceof Error ? err.message : String(err ?? "");
            if (msg.includes("409") || msg.toLowerCase().includes("conflict")) {
                const allSkills = (await $authFetch(`/skills`)) as SkillItem[];
                const existing = allSkills.find((s) => s.name.toLowerCase() === name.toLowerCase());
                if (existing) {
                    skill = existing;
                } else {
                    throw err;
                }
            } else {
                throw err;
            }
        }

        if (!skill) throw new Error("Skill resolution failed");

        // Link to repository
        try {
            await $authFetch(`/skills/repository/${repositoryId.value}/skills/${skill.id}`, {
                method: "POST",
            });
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : String(err ?? "");
            if (msg.includes("409") || msg.toLowerCase().includes("conflict")) {
                notifications.warning(`Skill "${name}" is already in this repository.`);
                closeAddSkillModal();
                await refreshSkills();
                return;
            }
            throw err;
        }

        notifications.success(`Skill "${name}" added.`);
        closeAddSkillModal();
        await refreshSkills();
    } catch (error) {
        console.error("Error adding skill:", error);
        notifications.error("Failed to add skill. " + error);
    }
}

async function refreshSkills() {
    try {
        const skillsResp = (await $authFetch(`/skills/repository/${repositoryId.value}`)) as SkillItem[];
        skills.value = (skillsResp || []).sort((a, b) => a.name.localeCompare(b.name));
    } catch (error) {
        console.error("Error refreshing skills:", error);
    }
}

// function openRenameSkillModal(skill: SkillItem) {
//     renamingSkillId.value = skill.id;
//     renamingSkillName.value = skill.name;
//     showRenameSkillModal.value = true;
// }

function closeRenameSkillModal() {
    showRenameSkillModal.value = false;
    renamingSkillId.value = null;
    renamingSkillName.value = "";
}

async function confirmRenameSkill() {
    if (!renamingSkillId.value || !renamingSkillName.value.trim()) return;
    try {
        await $authFetch(`/skills/${renamingSkillId.value}`, {
            method: "PUT",
            body: { name: renamingSkillName.value.trim() },
        });
        notifications.success("Skill renamed.");
        closeRenameSkillModal();
        await refreshSkills();
    } catch (error) {
        console.error("Error renaming skill:", error);
        notifications.error("Failed to rename skill. " + error);
    }
}

// function openRemoveSkillModal(skill: SkillItem) {
//     removingSkillId.value = skill.id;
//     removingSkillName.value = skill.name;
//     showRemoveSkillModal.value = true;
// }

function closeRemoveSkillModal() {
    showRemoveSkillModal.value = false;
    removingSkillId.value = null;
    removingSkillName.value = null;
}

async function confirmRemoveSkill() {
    if (!removingSkillId.value) return;
    try {
        await $authFetch(`/skills/repository/${repositoryId.value}/skills/${removingSkillId.value}`, {
            method: "DELETE",
        });
        notifications.success("Skill removed from repository.");
        closeRemoveSkillModal();
        await refreshSkills();
    } catch (error) {
        console.error("Error removing skill:", error);
        notifications.error("Failed to remove skill. " + error);
    }
}
</script>

<template>
    <div class="h-full flex">
        <!-- Hidden file input (shared across the page) -->
        <input ref="fileInput" type="file" :accept="SUPPORTED_MIME_TYPES.map(ext => '.' + ext).join(',')" class="hidden"
            @change="handleFileSelect" />

        <!-- Left side - content -->
        <div :class="showHtmlViewer ? 'w-full md:w-1/2 overflow-y-auto md:mr-10 md:pr-4 ml-6 my-8' : 'w-full mt-8'">
            <div class="max-w-4xl mx-auto">
                <DPageHeader :title="repo?.name ? repo.name : 'Repository'" />

                <div v-if="loading" class="py-20 text-center">
                    <div class="text-xl">Loading repository...</div>
                </div>

                <!-- Empty State: No documents and no units -->
                <div v-else-if="documents.length === 0 && units.length === 0" class="py-20">
                    <div class="max-w-md mx-auto text-center space-y-6">
                        <div class="space-y-2">
                            <h2 class="text-2xl font-semibold text-gray-900">Repository is Empty</h2>
                            <p class="text-gray-600">
                                Get started by uploading your first document. Documents are used to generate study
                                materials and tasks.
                            </p>
                        </div>

                        <div v-if="hasWriteAccess" class="pt-1 flex justify-center">
                            <DButton :icon-left="UploadIcon" variant="primary" size="lg" @click="triggerFilePicker">
                                Upload Your First Document
                            </DButton>
                        </div>

                        <div v-else class="pt-4">
                            <p class="text-sm text-gray-500">You don't have permission to upload documents to this
                                repository.</p>
                        </div>
                    </div>
                </div>

                <div v-else class="space-y-12">
                    <!-- Units Section -->
                    <section>
                        <div class="flex items-center justify-between">
                            <h2 class="text-xl font-semibold">Units</h2>
                            <div class="flex" v-if="hasWriteAccess">
                                <DButton variant="primary" :icon-left="PlusIcon" @click="openCreateUnitModal">
                                    Create Unit
                                </DButton>
                            </div>
                        </div>
                        <div class="border-t border-gray-200 my-3"></div>

                        <div v-if="units.length > 0" class="space-y-3">
                            <div v-for="unit in units" :key="unit.id"
                                class="bg-white p-3 rounded-lg shadow border border-gray-200">
                                <div class="flex justify-between items-center">
                                    <div class="flex items-center">
                                        <div class="flex flex-col">
                                            <h3 class="text-lg font-medium">
                                                {{ unit.title }}
                                            </h3>
                                            <span class="text-xs font-medium text-gray-500">
                                                {{ unit.task_count || 0 }} {{ (unit.task_count || 0) === 1 ? 'task' :
                                                    'tasks' }}
                                            </span>
                                        </div>
                                    </div>
                                    <div class="flex gap-2 items-center">
                                        <DButton v-if="hasWriteAccess" @click="navigateToTasksForUnit(unit.id)"
                                            variant="primary" :icon-left="ClipboardList">
                                            Tasks
                                        </DButton>

                                        <!-- Study button or message based on task count and access level -->
                                        <DButton v-if="(unit.task_count || 0) > 0"
                                            @click="navigateToStudyForUnit(unit.id)" variant="tertiary"
                                            :icon-left="BookOpenIcon">
                                            Study
                                        </DButton>
                                        <span v-else-if="!hasWriteAccess" class="text-xs text-gray-500 italic">
                                            No tasks created yet
                                        </span>

                                        <DHamburgerMenu v-if="hasWriteAccess">
                                            <template #default="{ close }">
                                                <button @click="() => { openRenameUnitModal(unit); close(); }"
                                                    class="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                                    <PencilIcon class="h-4 w-4" />
                                                    Rename Unit
                                                </button>
                                                <div class="border-t border-gray-200 my-1"></div>
                                                <button @click="() => { openDeleteUnitModal(unit); close(); }"
                                                    class="flex w-full items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50">
                                                    <TrashIcon class="h-4 w-4" />
                                                    Delete Unit
                                                </button>
                                            </template>
                                        </DHamburgerMenu>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div v-else class="bg-white p-6 rounded-lg shadow text-center">
                            <p class="text-gray-500">No units in this repository. Create one to get started.</p>
                        </div>
                    </section>

                    <!-- Documents Section -->
                    <section>
                        <div class="flex items-center justify-between">
                            <h2 class="text-xl font-semibold">Documents</h2>
                            <DButton v-if="hasWriteAccess" :icon-left="UploadIcon" variant="primary"
                                @click="triggerFilePicker">
                                Upload Document
                            </DButton>
                        </div>
                        <div class="border-t border-gray-200 my-3"></div>

                        <div v-if="documents.length > 0" class="space-y-3">
                            <div v-for="doc in documents" :key="doc.id"
                                class="bg-white p-3 rounded-lg shadow border border-gray-200">
                                <div class="flex items-center justify-between">
                                    <div class="truncate cursor-pointer" @click="viewDocument(doc.id)">
                                        <span class="font-medium">{{ doc.title }}</span>
                                    </div>
                                    <div class="flex items-center gap-1" v-if="hasWriteAccess">
                                        <DButton variant="tertiary" class="!p-2" :icon-left="PencilIcon"
                                            @click="openRenameDocumentModal(doc)" />
                                        <DButton variant="danger-light" class="!p-2" :icon-left="TrashIcon"
                                            @click="openDeleteDocumentModal(doc)" />
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div v-else class="bg-white p-6 rounded-lg shadow text-center">
                            <p class="text-gray-500">No documents in this repository.</p>
                        </div>
                    </section>

                    <!-- Skills Section -->
                    <!-- <section>
                        <div class="flex items-center justify-between">
                            <h2 class="text-xl font-semibold">Skills</h2>
                            <DButton v-if="hasWriteAccess" :icon-left="PlusIcon" variant="primary"
                                @click="openAddSkillModal">
                                Add Skill
                            </DButton>
                        </div>
                        <div class="border-t border-gray-200 my-3"></div>

                        <div v-if="skills.length > 0" class="space-y-3">
                            <div v-for="skill in skills" :key="skill.id"
                                class="bg-white p-3 rounded-lg shadow border border-gray-200">
                                <div class="flex items-center justify-between">
                                    <div class="truncate">
                                        <span class="font-medium">{{ skill.name }}</span>
                                    </div>
                                    <div class="flex gap-1" v-if="hasWriteAccess">
                                        <DButton variant="tertiary" class="!p-2" :icon-left="PencilIcon"
                                            @click="openRenameSkillModal(skill)" />
                                        <DButton variant="danger-light" class="!p-2" :icon-left="TrashIcon"
                                            @click="openRemoveSkillModal(skill)" />
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div v-else class="bg-white p-6 rounded-lg shadow text-center">
                            <p class="text-gray-500">No skills are defined for this repository yet.</p>
                        </div>
                    </section> -->
                </div>
            </div>
        </div>

        <!-- Right side - HTML viewer -->
        <div v-if="showHtmlViewer" class="relative w-0 md:w-1/2">
            <div class="h-full md:p-4">
                <DHtmlViewer :html-content="htmlContent" :loading="loadingHtml" :error="htmlError"
                    @close="showHtmlViewer = false; selectedDocumentId = null; htmlContent = ''" />
            </div>
        </div>

        <!-- Create Unit Modal -->
        <DModal v-if="showCreateUnitModal" titel="Create Unit" confirm-text="Create" @close="closeCreateUnitModal"
            @confirm="confirmCreateUnit">
            <div class="p-4">
                <label for="unit-title" class="block mb-2 font-medium">Unit Title:</label>
                <input id="unit-title" type="text" v-model="newUnitTitle"
                    class="w-full border rounded px-3 py-2 text-sm border-gray-200" placeholder="Enter unit title"
                    @keyup.enter="confirmCreateUnit" />
            </div>
        </DModal>

        <!-- Add Skill Modal -->
        <DModal v-if="showAddSkillModal" titel="Add Skill" confirm-text="Add" @close="closeAddSkillModal"
            @confirm="confirmAddSkill">
            <div class="p-4">
                <label for="skill-name" class="block mb-2 font-medium">Skill Name:</label>
                <input id="skill-name" type="text" v-model="newSkillName"
                    class="w-full border rounded px-3 py-2 text-sm border-gray-200" placeholder="Enter skill name"
                    @keyup.enter="confirmAddSkill" />
            </div>
        </DModal>

        <!-- Rename Skill Modal -->
        <DModal v-if="showRenameSkillModal" titel="Rename Skill" confirm-text="Save" @close="closeRenameSkillModal"
            @confirm="confirmRenameSkill">
            <div class="p-4">
                <label for="rename-skill" class="block mb-2 font-medium">New Name:</label>
                <input id="rename-skill" type="text" v-model="renamingSkillName"
                    class="w-full border rounded px-3 py-2 text-sm border-gray-200" placeholder="Enter new name"
                    @keyup.enter="confirmRenameSkill" />
            </div>
        </DModal>

        <!-- Remove Skill Modal -->
        <DModal v-if="showRemoveSkillModal" titel="Remove Skill" confirm-text="Remove" @close="closeRemoveSkillModal"
            @confirm="confirmRemoveSkill">
            <div class="p-4">
                <p>Remove skill "{{ removingSkillName }}" from this repository?</p>
                <p class="mt-2 text-sm text-gray-500">This does not delete the skill globally.</p>
            </div>
        </DModal>

        <!-- Rename Unit Modal -->
        <DModal v-if="showRenameUnitModal" titel="Rename Unit" confirm-text="Save" @close="closeRenameUnitModal"
            @confirm="confirmRenameUnit">
            <div class="p-4">
                <label for="rename-unit" class="block mb-2 font-medium">New Title:</label>
                <input id="rename-unit" type="text" v-model="renamingUnitTitle"
                    class="w-full border rounded px-3 py-2 text-sm border-gray-200" placeholder="Enter new title"
                    @keyup.enter="confirmRenameUnit" />
            </div>
        </DModal>

        <!-- Delete Unit Modal -->
        <DModal v-if="showDeleteUnitModal" titel="Delete Unit" confirm-text="Delete" @close="closeDeleteUnitModal"
            @confirm="confirmDeleteUnit">
            <div class="p-4">
                <p>Delete unit "{{ deletingUnitTitle }}"?</p>
                <p class="mt-2 text-sm text-gray-500">This action cannot be undone.</p>
            </div>
        </DModal>

        <!-- Rename Document Modal -->
        <DModal v-if="showRenameDocumentModal" titel="Rename Document" confirm-text="Save"
            @close="closeRenameDocumentModal" @confirm="confirmRenameDocument">
            <div class="p-4">
                <label for="rename-document" class="block mb-2 font-medium">New Title:</label>
                <input id="rename-document" type="text" v-model="renamingDocumentTitle"
                    class="w-full border rounded px-3 py-2 text-sm border-gray-200" placeholder="Enter new title"
                    @keyup.enter="confirmRenameDocument" />
            </div>
        </DModal>

        <!-- Delete Document Modal -->
        <DModal v-if="showDeleteDocumentModal" titel="Delete Document" confirm-text="Delete"
            @close="closeDeleteDocumentModal" @confirm="confirmDeleteDocument">
            <div class="p-4">
                <p>Delete document "{{ deletingDocumentTitle }}"?</p>
                <p class="mt-2 text-sm text-gray-500">This action cannot be undone.</p>
            </div>
        </DModal>

        <!-- Document Upload Modal -->
        <DModal v-if="showUploadModal" titel="Upload Document" :confirm-text="uploading ? 'Uploading...' : 'Upload'"
            :confirm-icon="UploadIcon" @close="closeUploadModal" @confirm="handleUpload">
            <div class="p-4 space-y-4">
                <!-- PDF Flattening Option and File Selection -->
                <div class="text-sm">
                    <div v-if="selectedFile" class="flex items-center gap-2 mb-2">
                        <span
                            class="inline-flex items-center px-3 py-1 rounded-full bg-gray-100 border border-gray-300 text-gray-800 text-sm font-medium shadow-sm">
                            <span class="truncate max-w-xs" style="max-width: 16rem;" :title="selectedFile.name">
                                {{ selectedFile.name }}
                            </span>
                        </span>
                    </div>
                    <label class="flex items-center gap-2 cursor-pointer select-none mb-2">
                        <input type="checkbox" v-model="flattenPdf" class="w-3 h-3 accent-black"
                            style="accent-color: black;" />
                        <span>Flatten PDF before text extraction</span>
                    </label>
                    <p class="text-xs text-gray-500">
                        Hint: Enable this if there are problems extracting text from a PDF. It may take longer to
                        process.
                    </p>
                </div>
            </div>
        </DModal>
    </div>
</template>
