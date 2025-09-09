<script setup>
import { ref, onMounted, watch } from "vue";

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
  highlightedChunkText: {
    type: String,
    default: "",
  },
});

const iframeSrc = ref("");
const shouldScrollToHighlight = ref(false);

// Function to handle iframe load event
function onIframeLoad() {
  console.log("Iframe loaded");
  if (shouldScrollToHighlight.value) {
    setTimeout(() => {
      scrollToHighlightedContent();
      shouldScrollToHighlight.value = false;
    }, 100);
  }
}

// Function to scroll to highlighted content in the iframe
function scrollToHighlightedContent() {
  const iframe = document.querySelector("iframe");
  if (!iframe || !iframe.contentDocument) {
    console.log("Iframe not ready yet");
    return;
  }

  try {
    const iframeDoc = iframe.contentDocument;

    // Look for highlighted elements (mark tags or highlighted paragraphs)
    const highlightedElements = iframeDoc.querySelectorAll(
      'mark, p[style*="background-color: #fef3c7"]',
    );

    if (highlightedElements.length > 0) {
      console.log(`Found ${highlightedElements.length} highlighted elements`);

      // Scroll to the first highlighted element
      const firstHighlighted = highlightedElements[0];
      firstHighlighted.scrollIntoView({
        behavior: "smooth",
        block: "center",
        inline: "nearest",
      });

      // Add a subtle animation to draw attention
      firstHighlighted.style.transition = "all 0.3s ease";
      firstHighlighted.style.transform = "scale(1.02)";

      setTimeout(() => {
        firstHighlighted.style.transform = "scale(1)";
      }, 300);
    } else {
      console.log("No highlighted elements found in iframe");
    }
  } catch (error) {
    console.log("Error accessing iframe content:", error);
  }
}

// Watch for changes in htmlContent and highlightedChunkText and update iframe
watch(
  [() => props.htmlContent, () => props.highlightedChunkText],
  ([newContent, newChunkText]) => {
    console.log("HTML viewer received new content:", {
      contentLength: newContent?.length,
      chunkText: newChunkText,
      hasChunkText: !!newChunkText,
    });

    if (newContent) {
      const processedContent = newContent;

      // If we have chunk text to highlight, process the content
      if (newChunkText) {
        // processedContent = highlightChunkInHtml(newContent, newChunkText);
      }

      const blob = new Blob([processedContent], { type: "text/html" });
      iframeSrc.value = URL.createObjectURL(blob);

      // Set flag to scroll to highlighted content
      if (newChunkText) {
        shouldScrollToHighlight.value = true;
      }
    }
  },
  { immediate: true },
);

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
      <iframe :src="iframeSrc" class="w-full h-full border-0" frameborder="0" allowfullscreen
        @load="onIframeLoad"></iframe>
    </div>

    <div v-else class="flex items-center justify-center h-full">
      <div class="text-center">
        <p class="text-gray-500">No content available</p>
      </div>
    </div>
  </div>
</template>
