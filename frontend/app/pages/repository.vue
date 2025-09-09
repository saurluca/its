<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRoute } from "vue-router";
import { ChevronDownIcon, ChevronRightIcon, ClipboardList, PencilIcon, TrashIcon, PlusIcon, BookOpenIcon } from "lucide-vue-next";
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
const expandedUnits = ref<Set<string>>(new Set());
const showCreateUnitModal = ref(false);
const newUnitTitle = ref("");

// Documents state & HTML viewer
const documents = ref<DocumentItem[]>([]);
const showHtmlViewer = ref(false);
const htmlContent = ref("");
const loadingHtml = ref(false);
const htmlError = ref("");
const selectedDocumentId = ref<string | null>(null);

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

function toggleUnitExpansion(unitId: string) {
    if (expandedUnits.value.has(unitId)) {
        expandedUnits.value.delete(unitId);
    } else {
        expandedUnits.value.add(unitId);
    }
}

function navigateToTasksForUnit(unitId: string) {
    navigateTo(`/tasks?repositoryId=${repositoryId.value}&unitId=${unitId}`);
}

function navigateToStudy() {
    navigateTo(`/study?repositoryId=${repositoryId.value}`);
}

function navigateToStudyForUnit(unitId: string) {
    navigateTo(`/study?repositoryId=${repositoryId.value}&unitId=${unitId}`);
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
                                <DButton variant="tertiary" :icon-left="BookOpenIcon" @click="navigateToStudy">
                                    Study
                                </DButton>
                            </div>
                        </div>
                        <div class="border-t border-gray-200 my-3"></div>

                        <div v-if="units.length > 0" class="space-y-4">
                            <div v-for="unit in units" :key="unit.id"
                                class="bg-white p-4 rounded-lg shadow border border-gray-200">
                                <div class="flex justify-between items-center">
                                    <div class="flex items-center gap-2">
                                        <button @click="toggleUnitExpansion(unit.id)"
                                            class="p-1 hover:bg-gray-100 rounded">
                                            <ChevronDownIcon v-if="expandedUnits.has(unit.id)" class="h-4 w-4" />
                                            <ChevronRightIcon v-else class="h-4 w-4" />
                                        </button>
                                        <div class="flex flex-col">
                                            <h3 class="text-lg font-medium cursor-pointer"
                                                @click="toggleUnitExpansion(unit.id)">
                                                {{ unit.title }}
                                            </h3>
                                            <span class="text-xs font-medium text-gray-500">
                                                {{ unit.task_count || 0 }} {{ (unit.task_count || 0) === 1 ? 'task' :
                                                    'tasks' }}
                                            </span>
                                        </div>
                                    </div>
                                    <div class="flex gap-2">
                                        <DButton @click="navigateToStudyForUnit(unit.id)" variant="tertiary"
                                            :icon-left="BookOpenIcon">
                                            Study
                                        </DButton>
                                        <DButton @click="navigateToTasksForUnit(unit.id)" variant="primary"
                                            :icon-left="ClipboardList">
                                            Tasks
                                        </DButton>
                                    </div>
                                </div>

                                <!-- Expanded unit details (lightweight placeholder) -->
                                <div v-if="expandedUnits.has(unit.id)" class="mt-3 text-sm text-gray-600">
                                    <div class="bg-gray-50 border border-gray-200 rounded p-3">
                                        <p>Unit ID: <span class="font-mono">{{ unit.id }}</span></p>
                                        <p class="text-gray-500">More unit details will appear here.</p>
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
    </div>
</template>
