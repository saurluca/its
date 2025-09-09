<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import { useRoute } from "vue-router";
import { ClipboardList, PencilIcon, TrashIcon, PlusIcon, BookOpenIcon, UploadIcon } from "lucide-vue-next";
import { SUPPORTED_MIME_TYPES, MAX_FILE_SIZE_MB, MAX_FILE_SIZE_BYTES } from "~/constans/constants";
import { useNotificationsStore } from "~/stores/notifications";

const { $authFetch } = useAuthenticatedFetch();
const notifications = useNotificationsStore();

type UUID = string;

interface RepositoryDetail {
    id: UUID;
    name: string;
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
        repo.value = repoResp;
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

// Upload actions
function openUploadModal() {
    showUploadModal.value = true;
}

function closeUploadModal() {
    showUploadModal.value = false;
    selectedFile.value = null;
    flattenPdf.value = false;
}

function triggerFilePicker() {
    if (uploading.value) return;
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
        handleUpload();
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

// Skills actions
function openAddSkillModal() {
    showAddSkillModal.value = true;
    newSkillName.value = "";
}

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
        await $authFetch(`/skills/repository/${repositoryId.value}/skills/${skill.id}`, {
            method: "POST",
        });

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

function openRenameSkillModal(skill: SkillItem) {
    renamingSkillId.value = skill.id;
    renamingSkillName.value = skill.name;
    showRenameSkillModal.value = true;
}

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

function openRemoveSkillModal(skill: SkillItem) {
    removingSkillId.value = skill.id;
    removingSkillName.value = skill.name;
    showRemoveSkillModal.value = true;
}

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
        <!-- Left side - content -->
        <div :class="showHtmlViewer ? 'w-1/2 overflow-y-auto mr-2 ml-6 my-8' : 'w-full mt-8'">
            <div class="max-w-4xl mx-auto">
                <DPageHeader :title="repo?.name ? repo.name : 'Repository'" />

                <div v-if="loading" class="py-20 text-center">
                    <div class="text-xl">Loading repository...</div>
                </div>

                <div v-else class="space-y-10">
                    <!-- Units Section -->
                    <section>
                        <div class="flex items-center justify-between mr-4">
                            <h2 class="text-xl font-semibold">Units</h2>
                            <div class="flex gap-2">
                                <DButton variant="primary" :icon-left="PlusIcon" @click="openCreateUnitModal">
                                    Create Unit
                                </DButton>
                            </div>
                        </div>
                        <div class="border-t border-gray-200 my-3"></div>

                        <div v-if="units.length > 0" class="space-y-4">
                            <div v-for="unit in units" :key="unit.id"
                                class="bg-white p-4 rounded-lg shadow border border-gray-200">
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
                                    <div class="flex gap-2">
                                        <DButton @click="navigateToTasksForUnit(unit.id)" variant="primary"
                                            :icon-left="ClipboardList">
                                            Tasks
                                        </DButton>
                                        <DButton @click="navigateToStudyForUnit(unit.id)" variant="tertiary"
                                            :icon-left="BookOpenIcon">
                                            Study
                                        </DButton>

                                    </div>
                                </div>
                            </div>
                        </div>

                        <div v-else class="bg-white p-6 rounded-lg shadow text-center">
                            <p class="text-gray-500">No units in this repository.</p>
                        </div>
                    </section>

                    <!-- Documents Section -->
                    <section>
                        <div class="flex items-center justify-between mr-4">
                            <h2 class="text-xl font-semibold">Documents</h2>
                            <DButton :icon-left="UploadIcon" variant="primary" @click="openUploadModal">
                                Upload Document
                            </DButton>
                        </div>
                        <div class="border-t border-gray-200 my-3"></div>

                        <div v-if="documents.length > 0" class="space-y-2">
                            <div v-for="doc in documents" :key="doc.id" @click="viewDocument(doc.id)"
                                class="bg-white p-3 rounded-lg shadow border border-gray-200 cursor-pointer hover:bg-gray-50">
                                <div class="flex items-center justify-between">
                                    <div class="truncate">
                                        <span class="font-medium">{{ doc.title }}</span>
                                    </div>
                                    <div class="text-xs text-gray-400">ID: {{ doc.id.slice(0, 8) }}</div>
                                </div>
                            </div>
                        </div>

                        <div v-else class="bg-white p-6 rounded-lg shadow text-center">
                            <p class="text-gray-500">No documents in this repository.</p>
                        </div>
                    </section>

                    <!-- Skills Section -->
                    <section>
                        <div class="flex items-center justify-between mr-4">
                            <h2 class="text-xl font-semibold">Skills</h2>
                            <DButton :icon-left="PlusIcon" variant="primary" @click="openAddSkillModal">
                                Add Skill
                            </DButton>
                        </div>
                        <div class="border-t border-gray-200 my-3"></div>

                        <div v-if="skills.length > 0" class="space-y-2">
                            <div v-for="skill in skills" :key="skill.id"
                                class="bg-white p-3 rounded-lg shadow border border-gray-200">
                                <div class="flex items-center justify-between">
                                    <div class="truncate">
                                        <span class="font-medium">{{ skill.name }}</span>
                                    </div>
                                    <div class="flex gap-1">
                                        <DButton variant="tertiary" class="!p-2" :icon-left="PencilIcon"
                                            @click="openRenameSkillModal(skill)" />
                                        <DButton variant="tertiary" class="!p-2" :icon-left="TrashIcon"
                                            @click="openRemoveSkillModal(skill)" />
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div v-else class="bg-white p-6 rounded-lg shadow text-center">
                            <p class="text-gray-500">No skills are defined for this repository yet.</p>
                        </div>
                    </section>
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

        <!-- Document Upload Modal -->
        <DModal v-if="showUploadModal" titel="Upload Document"
            :confirm-text="uploading ? 'Uploading...' : 'Select File & Upload'" :confirm-icon="UploadIcon"
            @close="closeUploadModal" @confirm="triggerFilePicker">
            <div class="p-4 space-y-4">
                <!-- PDF Flattening Option and File Selection -->
                <div class="text-sm">
                    <label class="flex items-center gap-2 cursor-pointer select-none">
                        <input type="checkbox" v-model="flattenPdf" class="w-3 h-3 accent-black"
                            style="accent-color: black;" />
                        <span>Flatten PDF before text extraction</span>
                    </label>
                    <p class="text-xs text-gray-500">
                        Hint: Enable this if there are problems extracting text from a PDF. It may take longer to
                        process.
                    </p>
                    <p class="text-xs text-gray-500">
                        Supported formats: {{ SUPPORTED_MIME_TYPES.join(', ') }} • Max size: {{ MAX_FILE_SIZE_MB }}MB
                    </p>
                    <input ref="fileInput" type="file" :accept="SUPPORTED_MIME_TYPES.map(ext => '.' + ext).join(',')"
                        class="hidden" @change="handleFileSelect" />
                    <div v-if="selectedFile" class="text-sm text-gray-600 bg-gray-50 p-2 rounded">
                        Selected: {{ selectedFile.name }}
                    </div>
                </div>
            </div>
        </DModal>
    </div>
</template>
