<script setup>
import { ref, watch } from "vue";
import { XIcon } from "lucide-vue-next";

const props = defineProps({
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

const emit = defineEmits(["close"]);

const iframeSrc = ref("");
const onIframeLoad = () => { };

// Watch for changes in htmlContent and update iframe
watch(
  [() => props.htmlContent],
  ([newContent]) => {

    if (newContent) {
      const processedContent = newContent;

      const blob = new Blob([processedContent], { type: "text/html" });
      iframeSrc.value = URL.createObjectURL(blob);
    }
  },
  { immediate: true },
);
</script>

<template>
  <!-- Full-screen overlay on small screens; inline card on md+ -->
  <div class="fixed inset-0 z-50 bg-white md:static md:h-full md:w-full md:bg-transparent">
    <!-- Close button visible only on small screens -->
    <button
      class="absolute top-3 right-3 md:hidden p-2 rounded hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-300"
      aria-label="Close" type="button" @click="emit('close')">
      <XIcon class="h-6 w-6" />
    </button>

    <div class="h-full w-full md:border md:border-gray-200 md:rounded-lg md:overflow-hidden">
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
        <iframe :src="iframeSrc" class="w-full h-full border-0" frameborder="0" allowfullscreen
          @load="onIframeLoad"></iframe>
      </div>

      <div v-else class="flex items-center justify-center h-full">
        <div class="text-center">
          <p class="text-gray-500">No content available</p>
        </div>
      </div>
    </div>
  </div>
</template>
