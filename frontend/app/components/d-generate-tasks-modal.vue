<script setup lang="ts">
import { ref, watch, computed } from "vue";
import type { Repository, Document } from "~/types/models";
import { useNotificationsStore } from "~/stores/notifications";

const props = defineProps<{
    repository: Repository | null;
    unitId?: string;
}>();

const emit = defineEmits<{
    (e: "close" | "success"): void;
}>();

const { $authFetch } = useAuthenticatedFetch();
const notifications = useNotificationsStore();

const loadingDocuments = ref(false);
const repositoryDocuments = ref<Document[]>([]);
const selectedDocuments = ref<Set<string>>(new Set());
const numTasksToGenerate = ref<number>(3);
const taskType = ref<"multiple_choice" | "free_text">("multiple_choice");

const hasRepository = computed(() => !!props.repository?.id);

async function fetchRepositoryDocuments() {
    if (!props.repository?.id) {
        repositoryDocuments.value = [];
        return;
    }
    loadingDocuments.value = true;
    try {
        const data = await $authFetch(`/repositories/${props.repository.id}/documents`) as Document[];
        repositoryDocuments.value = data.map((doc: Document) => ({
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
        notifications.error("Failed to load repository documents. Please try again.");
    } finally {
        loadingDocuments.value = false;
    }
}

watch(
    () => props.repository?.id,
    async () => {
        selectedDocuments.value.clear();
        numTasksToGenerate.value = 3;
        taskType.value = "multiple_choice";
        await fetchRepositoryDocuments();
    },
    { immediate: true }
);

function closeModal() {
    emit("close");
}

async function confirmGenerateTasks() {
    if (!props.repository?.id || !props.unitId || selectedDocuments.value.size === 0) {
        notifications.warning("Please select at least one document to generate tasks from.");
        return;
    }

    const repositoryName = props.repository.name;
    const taskTypeText = taskType.value === "multiple_choice" ? "multiple choice" : "free text";
    const processingId = notifications.loading(
        `Generating ${numTasksToGenerate.value} ${taskTypeText} tasks for "${repositoryName}" from ${selectedDocuments.value.size} document${selectedDocuments.value.size === 1 ? "" : "s"}. This may take a while.`
    );

    try {
        await $authFetch("/tasks/generate_for_documents", {
            method: "POST",
            body: {
                unit_id: props.unitId,
                document_ids: Array.from(selectedDocuments.value),
                num_tasks: numTasksToGenerate.value,
                task_type: taskType.value,
            },
        });

        notifications.remove(processingId);
        notifications.success(`Successfully generated ${numTasksToGenerate.value} ${taskTypeText} tasks for "${repositoryName}"!`);
        emit("success");
    } catch (error) {
        console.error("Error generating tasks:", error);
        notifications.remove(processingId);
        notifications.error(`Failed to generate tasks for "${repositoryName}". Please try again. ${error}`);
    }
}
</script>

<template>
    <DModal v-if="hasRepository" titel="Generate Tasks" confirm-text="Generate Tasks" :wide="true" @close="closeModal"
        @confirm="confirmGenerateTasks">
        <div class="p-4 space-y-4">
            <div class="text-sm text-gray-600">
                <p>
                    Generating tasks for repository
                    <span class="font-medium">"{{ props.repository?.name }}"</span>
                </p>
            </div>

            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label for="num-tasks" class="block mb-2 font-medium">Number of tasks:</label>
                    <input id="num-tasks" type="number" min="1" max="50" v-model.number="numTasksToGenerate"
                        class="w-full border rounded-lg px-3 py-2 text-sm border-gray-200" />
                </div>
                <div>
                    <label for="task-type" class="block mb-2 font-medium">Task type:</label>
                    <select id="task-type" v-model="taskType"
                        class="w-full border rounded-lg px-3 py-2 text-sm border-gray-200">
                        <option value="multiple_choice">Multiple Choice</option>
                        <option value="free_text">Free Text</option>
                    </select>
                </div>
            </div>

            <div>
                <label class="block mb-2 font-medium">Select documents to generate tasks from:</label>
                <div class="space-y-2 max-h-60 overflow-y-auto border rounded-lg border-gray-200 p-2">
                    <div v-if="loadingDocuments" class="text-center text-gray-500 py-4">
                        Loading documents…
                    </div>
                    <div v-else-if="repositoryDocuments.length === 0" class="text-center text-gray-500 py-4">
                        No documents found in this repository.
                    </div>
                    <label v-for="document in repositoryDocuments" :key="document.id"
                        class="flex items-start gap-2 cursor-pointer hover:bg-gray-100 p-1 rounded-lg text-black">
                        <input type="checkbox" :value="document.id" v-model="selectedDocuments"
                            class="w-5 h-5 accent-black flex-shrink-0 mt-0.5" style="accent-color: black;" />
                        <span>{{ document.title }}</span>
                    </label>
                </div>
            </div>

            <div v-if="selectedDocuments.size > 0" class="text-sm text-gray-600">
                <p>
                    Will generate {{ numTasksToGenerate }} {{ taskType === 'multiple_choice' ? 'multiple choice' :
                        'freetext' }} tasks
                </p>
                <p>
                    From {{ selectedDocuments.size }} selected document{{ selectedDocuments.size
                        === 1 ?
                        '' : 's' }}

                </p>
                <p>Tasks will be linked to the repository "{{ props.repository?.name }}".</p>
            </div>
        </div>
    </DModal>
</template>
