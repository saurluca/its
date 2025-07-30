<script setup>
import { ref, onMounted, watch } from "vue";
import stringSimilarity from "string-similarity";

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
    },
    highlightedChunkText: {
        type: String,
        default: ""
    },
    questionText: {
        type: String,
        default: ""
    },
    answerText: {
        type: String,
        default: ""
    }
});

const iframeSrc = ref("");
const shouldScrollToHighlight = ref(false);

// Function to handle iframe load event
function onIframeLoad() {
    if (shouldScrollToHighlight.value) {
        setTimeout(() => {
            scrollToHighlightedContent();
            shouldScrollToHighlight.value = false;
        }, 100);
    }
}

// Function to scroll to highlighted content in the iframe
function scrollToHighlightedContent() {
    const iframe = document.querySelector('iframe');
    if (!iframe || !iframe.contentDocument) {
        return;
    }

    try {
        const iframeDoc = iframe.contentDocument;
        const highlightedElements = iframeDoc.querySelectorAll('mark, p[style*="background-color: #fef3c7"]');

        if (highlightedElements.length > 0) {
            const firstHighlighted = highlightedElements[0];
            firstHighlighted.scrollIntoView({
                behavior: 'smooth',
                block: 'center',
                inline: 'nearest'
            });

            // Add a subtle animation
            firstHighlighted.style.transition = 'all 0.3s ease';
            firstHighlighted.style.transform = 'scale(1.02)';

            setTimeout(() => {
                firstHighlighted.style.transform = 'scale(1)';
            }, 300);
        }
    } catch (error) {
        console.log("Error accessing iframe content:", error);
    }
}

// Function to normalize text
function normalizeText(text) {
    return text
        .replace(/\s+/g, ' ')
        .trim();
}

// Function to extract text content from HTML
function extractTextFromHtml(htmlContent) {
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = htmlContent;
    return tempDiv.textContent || tempDiv.innerText || '';
}

// Function to find the best matching paragraph
function findBestMatchingParagraph(htmlContent, chunkText, questionText = "", answerText = "") {
    const normalizedChunk = normalizeText(chunkText);
    const normalizedQuestion = normalizeText(questionText);
    const normalizedAnswer = normalizeText(answerText);

    // Combine all text sources for better matching
    const combinedSearchText = [normalizedChunk, normalizedQuestion, normalizedAnswer]
        .filter(text => text.length > 0)
        .join(" ");

    const paragraphRegex = /<p[^>]*>([^<]*(?:<[^>]*>[^<]*)*?)<\/p>/gi;

    let bestMatch = { score: 0, match: null, content: null };
    let currentMatch;

    // Find all paragraphs and compare with chunk text
    while ((currentMatch = paragraphRegex.exec(htmlContent)) !== null) {
        const paragraphContent = currentMatch[1];
        const paragraphText = normalizeText(extractTextFromHtml(paragraphContent));

        // Calculate multiple similarity scores
        const chunkSimilarity = stringSimilarity.compareTwoStrings(paragraphText, normalizedChunk);
        const questionSimilarity = normalizedQuestion ? stringSimilarity.compareTwoStrings(paragraphText, normalizedQuestion) : 0;
        const answerSimilarity = normalizedAnswer ? stringSimilarity.compareTwoStrings(paragraphText, normalizedAnswer) : 0;
        const combinedSimilarity = stringSimilarity.compareTwoStrings(paragraphText, combinedSearchText);

        // Use weighted combination - chunk text is most important, then question, then answer
        const weightedScore = (chunkSimilarity * 0.6) + (questionSimilarity * 0.25) + (answerSimilarity * 0.15) + (combinedSimilarity * 0.1);

        if (weightedScore > bestMatch.score) {
            bestMatch = {
                score: weightedScore,
                match: currentMatch[0], // Full paragraph HTML
                content: paragraphContent // Paragraph content
            };
        }
    }

    return bestMatch.score > 0.15 ? bestMatch : null;
}

// Function to highlight chunk text in HTML content
function highlightChunkInHtml(htmlContent, chunkText) {
    if (!chunkText || !htmlContent) return htmlContent;

    // Find the best matching paragraph using chunk, question, and answer
    const bestParagraph = findBestMatchingParagraph(
        htmlContent,
        chunkText,
        props.questionText,
        props.answerText
    );

    if (bestParagraph) {
        // Highlight the entire paragraph that best matches the chunk
        return htmlContent.replace(
            bestParagraph.match,
            `<p style="background-color: #fef3c7; padding: 15px; margin: 10px; border-radius: 8px; border-left: 4px solid #f59e0b; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">${bestParagraph.content}</p>`
        );
    }

    // If no good paragraph match found, add an indicator
    const normalizedChunk = normalizeText(chunkText);
    const indicator = `
        <div style="background-color: #fef3c7; border: 2px solid #f59e0b; padding: 15px; margin: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <strong style="color: #92400e;">Content Not Found in Document:</strong><br><br>
            <div style="background-color: #fefcf0; padding: 10px; border-radius: 4px; font-style: italic; color: #451a03;">
                <strong>Chunk:</strong> ${normalizedChunk}<br><br>
                ${props.questionText ? `<strong>Question:</strong> ${normalizeText(props.questionText)}<br><br>` : ''}
                ${props.answerText ? `<strong>Answer:</strong> ${normalizeText(props.answerText)}` : ''}
            </div>
        </div>
    `;
    return htmlContent.replace(/<body[^>]*>/i, `$&${indicator}`);
}

// Watch for changes in htmlContent and highlightedChunkText and update iframe
watch([() => props.htmlContent, () => props.highlightedChunkText], ([newContent, newChunkText]) => {
    if (newContent) {
        let processedContent = newContent;

        // If we have chunk text to highlight, process the content
        if (newChunkText) {
            processedContent = highlightChunkInHtml(newContent, newChunkText);
        }

        const blob = new Blob([processedContent], { type: 'text/html' });
        iframeSrc.value = URL.createObjectURL(blob);

        // Set flag to scroll to highlighted content
        if (newChunkText) {
            shouldScrollToHighlight.value = true;
        }
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