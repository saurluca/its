<script setup>
import { ref, computed } from "vue";

const props = defineProps({
    textContent: {
        type: String,
        default: "",
    },
    loading: {
        type: Boolean,
        default: false,
    },
    error: {
        type: String,
        default: "",
    },
});

// Computed property for processed content
const processedContent = computed(() => {
    if (!props.textContent) {
        return "";
    }

    // Just escape HTML to prevent XSS
    const div = document.createElement('div');
    div.textContent = props.textContent;
    return div.innerHTML;
});

// Reference to the text viewer container
const textViewerRef = ref(null);
</script>

<!-- eslint-disable vue/no-v-html -->
<template>
    <div class="h-full w-full border border-gray-200 rounded-lg overflow-hidden">
        <div v-if="loading" class="flex items-center justify-center h-full">
            <div class="text-center">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-2"></div>
                <p class="text-gray-600">Loading text content...</p>
            </div>
        </div>

        <div v-else-if="error" class="flex items-center justify-center h-full">
            <div class="text-center">
                <p class="text-red-600">{{ error }}</p>
            </div>
        </div>

        <div v-else-if="textContent" class="h-full w-full overflow-y-auto">
            <div ref="textViewerRef" class="bg-gray-50 p-4 rounded text-sm leading-7 whitespace-pre-wrap"
                v-html="processedContent"></div>
        </div>

        <div v-else class="flex items-center justify-center h-full">
            <div class="text-center">
                <p class="text-gray-500">No content available</p>
            </div>
        </div>
    </div>
</template>