<script setup lang="ts">
import { ref } from "vue";
import { UploadIcon } from "lucide-vue-next";
import type { Repository } from "~/types/models";

const { $authFetch } = useAuthenticatedFetch();

interface Props {
    repositories: Repository[];
}

const props = defineProps<Props>();
const emit = defineEmits<{
    (e: "close"): void;
    (e: "upload-complete"): void;
}>();

const uploading = ref(false);
const selectedRepositories = ref<string[]>([]);
const fileInput = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);

function triggerFilePicker() {
    if (uploading.value) return;
    fileInput.value?.click();
}

function handleFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
        selectedFile.value = input.files[0] || null;
    }
}

async function handleUpload() {
    if (uploading.value || !selectedFile.value) return;

    uploading.value = true;
    try {
        const formData = new FormData();
        formData.append("file", selectedFile.value);

        // Upload the document
        const uploadResponse = await $authFetch("/documents/upload/", {
            method: "POST",
            body: formData,
        }) as any;

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
        alert("Failed to upload document. Please try again. " + error);
    } finally {
        uploading.value = false;
    }
}

function toggleRepository(repositoryId: string) {
    const index = selectedRepositories.value.indexOf(repositoryId);
    if (index > -1) {
        selectedRepositories.value.splice(index, 1);
    } else {
        selectedRepositories.value.push(repositoryId);
    }
}

function close() {
    selectedRepositories.value = [];
    selectedFile.value = null;
    emit("close");
}
</script>

<template>
    <DModal titel="Upload Document" :confirmText="uploading ? 'Uploading...' : 'Upload Document'" @close="close"
        @confirm="handleUpload">
        <div class="p-4 space-y-4">
            <div>
                <label class="block mb-2 font-medium">Select Document:</label>
                <DButton @click="triggerFilePicker" :loading="uploading" :iconLeft="UploadIcon" variant="primary">
                    Choose File
                </DButton>
                <input ref="fileInput" type="file" accept="*/*" class="hidden" @change="handleFileSelect" />
                <div v-if="selectedFile" class="mt-2 text-sm text-gray-600">
                    Selected: {{ selectedFile.name }}
                </div>
            </div>

            <div v-if="repositories.length > 0">
                <label class="block mb-2 font-medium">Add to Repositories:</label>
                <div class="space-y-2 max-h-40 overflow-y-auto">
                    <label v-for="repository in repositories" :key="repository.id"
                        class="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-2 rounded">
                        <input type="checkbox" :value="repository.id" v-model="selectedRepositories"
                            @change="toggleRepository(repository.id)" class="rounded border-gray-300" />
                        <span>{{ repository.name }}</span>
                    </label>
                </div>
                <p class="text-sm text-gray-500 mt-1">
                    Select repositories where you want to add this document
                </p>
            </div>

            <div v-else class="text-sm text-gray-500">
                No repositories available. Create a repository first.
            </div>
        </div>
    </DModal>
</template>