<script setup>
import { computed } from "vue";
import { XIcon } from "lucide-vue-next";
import DOMPurify from "dompurify";

defineProps({
  htmlContent: {
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

// Emit close event to parent
const emit = defineEmits(["close"]);

function handleClose() {
  emit("close");
}

const sanitizedHtml = computed(() => DOMPurify.sanitize(props.htmlContent));
</script>

<template>
  <div class="h-full w-full border border-gray-200 rounded-lg overflow-hidden relative">
    <button @click="handleClose" aria-label="Close"
      class="absolute top-6 right-6 z-10 rounded text-gray-500 hover:text-gray-700 text-xl leading-none px-2">
      <XIcon />
    </button>
    <div class="h-full">
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

      <div v-else class="h-full w-full overflow-auto">
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div class="p-4 prose max-w-none" v-html="sanitizedHtml"></div>
      </div>
    </div>
  </div>

</template>
