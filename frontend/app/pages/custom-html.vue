<script setup>
import { ref, onMounted } from "vue";

const route = useRoute();
const runtimeConfig = useRuntimeConfig();
const apiUrl = runtimeConfig.public.apiBase;

const htmlContent = ref("");
const loading = ref(true);
const error = ref("");
const iframeSrc = ref("");

async function fetchDocumentContent() {
    const documentId = route.query.documentId;

    if (!documentId) {
        error.value = "No document ID provided";
        loading.value = false;
        return;
    }

    try {
        const response = await fetch(`${apiUrl}/documents/${documentId}/`);
        const data = await response.json();

        if (data.content) {
            htmlContent.value = data.content;
            // Create a blob URL for the iframe
            const blob = new Blob([data.content], { type: 'text/html' });
            iframeSrc.value = URL.createObjectURL(blob);
        } else {
            error.value = "Document content not found";
        }
    } catch (err) {
        console.error("Error fetching document content:", err);
        error.value = "Failed to load document content";
    } finally {
        loading.value = false;
    }
}

onMounted(() => {
    fetchDocumentContent();
});

definePageMeta({
    layout: 'minimal',
});
</script>

<template>
    <div class="h-full w-full">
        <div v-if="loading" class="text-center py-8">
            <p>Loading document content...</p>
        </div>

        <div v-else-if="error" class="text-center py-8">
            <p class="text-red-600">{{ error }}</p>
        </div>

        <div v-else-if="iframeSrc" class="h-full w-full">
            <iframe :src="iframeSrc" class="w-full h-full border-0" frameborder="0" allowfullscreen></iframe>
        </div>

        <div v-else class="text-center py-8">
            <p>No content available</p>
        </div>
    </div>
</template>
