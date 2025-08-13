<script setup lang="ts">
import { ref, computed } from "vue";
import { UploadIcon } from "lucide-vue-next";
import type { Repository } from "~/types/models";
import { useNotificationsStore } from "~/stores/notifications";

const { $authFetch } = useAuthenticatedFetch();

interface Props {
    repositories: Repository[];
}

defineProps<Props>();
const emit = defineEmits<{
    (e: "close" | "upload-complete"): void;
}>();

const uploading = ref(false);
const selectedRepositories = ref<string[]>([]);
const fileInput = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);

const notifications = useNotificationsStore();

// Computed property to check if upload is allowed
const canUpload = computed(() => {
    return selectedRepositories.value.length > 0;
});

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

    uploading.value = true;
    try {
        const formData = new FormData();
        formData.append("file", selectedFile.value);

        // Upload the document
        const uploadResponse = await $authFetch("/documents/upload/", {
            method: "POST",
            body: formData,
        }) as { id: string };

        // Add document to selected repositories
        if (selectedRepositories.value.length > 0) {
            const documentId = uploadResponse.id;

            for (const repositoryId of selectedRepositories.value) {
                await $authFetch("/repositories/links/", {
                    method: "POST",
                    body: {
                        repository_id: repositoryId,
                        document_id: documentId,
                    },
                });
            }
        }

        emit("upload-complete");
        close();
    } catch (error) {
        console.error("Error uploading document:", error);
        notifications.error("Failed to upload document. Please try again. " + error);
    } finally {
        uploading.value = false;
    }
}

function close() {
    selectedRepositories.value = [];
    selectedFile.value = null;
    emit("close");
}
</script>

<template>
    <DModal titel="Upload Document" :confirmText="uploading ? 'Uploading...' : 'Select File & Upload'"
        :confirmIcon="UploadIcon" :disabled="!canUpload" @close="close" @confirm="triggerFilePicker">
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
                <p class="text-sm text-gray-500 mt-2">
                    You must select at least one repository to upload a document
                </p>
                <p v-if="selectedRepositories.length > 0" class="text-sm text-green-600 mt-1">
                    ✓ {{ selectedRepositories.length }} repository{{ selectedRepositories.length === 1 ? '' : 'ies' }}
                    selected
                </p>
            </div>

            <div v-else class="text-sm text-gray-500 bg-yellow-50 p-3 rounded border border-yellow-200">
                <strong>No repositories available.</strong> Create a repository first before uploading documents.
            </div>

            <!-- File Selection -->
            <div v-if="canUpload">
                <input ref="fileInput" type="file" accept="*/*" class="hidden" @change="handleFileSelect" />
                <div v-if="selectedFile" class="text-sm text-gray-600 bg-gray-50 p-2 rounded">
                    Selected: {{ selectedFile.name }}
                </div>
            </div>
        </div>
    </DModal>
</template>