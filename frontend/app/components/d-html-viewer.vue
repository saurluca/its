<script setup>
import { ref, onMounted, watch } from "vue";

const props = defineProps({
    htmlContent: {
        type: String,
        default: ""
    },
    loading: {
        type: Boolean,
        default: false
    },
    error: {
        type: String,
        default: ""
    }
});

const iframeSrc = ref("");

// Watch for changes in htmlContent and update iframe
watch(() => props.htmlContent, (newContent) => {
    if (newContent) {
        const blob = new Blob([newContent], { type: 'text/html' });
        iframeSrc.value = URL.createObjectURL(blob);
    }
}, { immediate: true });

// Clean up blob URL when component is unmounted
onMounted(() => {
    return () => {
        if (iframeSrc.value) {
            URL.revokeObjectURL(iframeSrc.value);
        }
    };
});
</script>

<template>
    <div class="h-full w-full border border-gray-200 rounded-lg overflow-hidden">
        <div v-if="loading" class="flex items-center justify-center h-full">
            <div class="text-center">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-2"></div>
                <p class="text-gray-600">Loading document content...</p>
            </div>
        </div>

        <div v-else-if="error" class="flex items-center justify-center h-full">
            <div class="text-center">
                <p class="text-red-600">{{ error }}</p>
            </div>
        </div>

        <div v-else-if="iframeSrc" class="h-full w-full">
            <iframe :src="iframeSrc" class="w-full h-full border-0" frameborder="0" allowfullscreen></iframe>
        </div>

        <div v-else class="flex items-center justify-center h-full">
            <div class="text-center">
                <p class="text-gray-500">No content available</p>
            </div>
        </div>
    </div>
</template>