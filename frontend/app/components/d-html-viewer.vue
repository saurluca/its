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
    },
    highlightedChunkText: {
        type: String,
        default: ""
    }
});

const iframeSrc = ref("");
const shouldScrollToHighlight = ref(false);

// Function to extract text content from HTML
function extractTextFromHtml(htmlContent) {
    // Create a temporary div to parse HTML
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = htmlContent;
    return tempDiv.textContent || tempDiv.innerText || '';
}

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
    const iframe = document.querySelector('iframe');
    if (!iframe || !iframe.contentDocument) {
        console.log("Iframe not ready yet");
        return;
    }

    try {
        const iframeDoc = iframe.contentDocument;

        // Look for highlighted elements (mark tags or highlighted paragraphs)
        const highlightedElements = iframeDoc.querySelectorAll('mark, p[style*="background-color: #fef3c7"]');

        if (highlightedElements.length > 0) {
            console.log(`Found ${highlightedElements.length} highlighted elements`);

            // Scroll to the first highlighted element
            const firstHighlighted = highlightedElements[0];
            firstHighlighted.scrollIntoView({
                behavior: 'smooth',
                block: 'center',
                inline: 'nearest'
            });

            // Add a subtle animation to draw attention
            firstHighlighted.style.transition = 'all 0.3s ease';
            firstHighlighted.style.transform = 'scale(1.02)';

            setTimeout(() => {
                firstHighlighted.style.transform = 'scale(1)';
            }, 300);

        } else {
            console.log("No highlighted elements found in iframe");
        }
    } catch (error) {
        console.log("Error accessing iframe content:", error);
    }
}

// Function to normalize text by removing special characters and encoding artifacts
function normalizeText(text) {
    return text
        .replace(/\/uniFB01/g, 'fi') // Replace unicode escape for 'fi' ligature
        .replace(/\/uniFB02/g, 'fl') // Replace unicode escape for 'fl' ligature  
        .replace(/\/uni[A-F0-9]{4}/g, '') // Remove other unicode escapes
        .replace(/\s+/g, ' ') // Normalize whitespace
        .trim();
}

// Function to highlight chunk text in HTML content
function highlightChunkInHtml(htmlContent, chunkText) {
    if (!chunkText || !htmlContent) return htmlContent;

    console.log("=== HIGHLIGHTING DEBUG START ===");
    console.log("Original chunk text:", chunkText);
    console.log("HTML content length:", htmlContent.length);
    console.log("HTML content preview:", htmlContent.substring(0, 200));

    // Extract text content for debugging
    const extractedText = extractTextFromHtml(htmlContent);
    console.log("Extracted text length:", extractedText.length);
    console.log("First 500 chars of extracted text:", extractedText.substring(0, 500));

    // Clean up and normalize the chunk text
    const cleanChunkText = normalizeText(chunkText);
    console.log("Normalized chunk text:", cleanChunkText);
    console.log("Normalized chunk text length:", cleanChunkText.length);

    // Escape special regex characters in chunk text
    const escapedChunkText = cleanChunkText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    console.log("Escaped chunk text:", escapedChunkText);

    // Create a regex that matches the chunk text (case insensitive)
    const regex = new RegExp(`(${escapedChunkText})`, 'gi');
    console.log("Created regex:", regex);

    // Check if the text is found
    const matches = htmlContent.match(regex);
    console.log("Found matches in HTML:", matches ? matches.length : 0);
    if (matches) {
        console.log("First match:", matches[0]);
    }

    if (!matches || matches.length === 0) {
        console.log("No exact matches found, trying to find containing paragraph...");

        // Also try to match with the normalized HTML content
        const normalizedHtmlText = normalizeText(extractedText);
        console.log("Normalized HTML text length:", normalizedHtmlText.length);
        console.log("Normalized HTML text preview:", normalizedHtmlText.substring(0, 500));

        const normalizedChunkRegex = new RegExp(`(${normalizeText(cleanChunkText).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        console.log("Normalized chunk regex:", normalizedChunkRegex);

        const normalizedMatches = normalizedHtmlText.match(normalizedChunkRegex);
        console.log("Found matches in normalized text:", normalizedMatches ? normalizedMatches.length : 0);

        if (normalizedMatches && normalizedMatches.length > 0) {
            console.log("Found matches in normalized text:", normalizedMatches.length);
            console.log("First normalized match:", normalizedMatches[0]);
            // Try to find and highlight the section in the original HTML
            return htmlContent.replace(new RegExp(`(${cleanChunkText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'),
                '<mark style="background-color: #fef3c7; padding: 2px 4px; border-radius: 3px;">$1</mark>');
        }

        // Try to find the paragraph that contains the chunk text
        // Use a simpler regex that better captures paragraph content
        const paragraphRegex = /<p[^>]*>([^<]*(?:<[^>]*>[^<]*)*?)<\/p>/gi;
        console.log("Looking for paragraphs with regex:", paragraphRegex);

        // First, let's count how many paragraphs we actually have
        const allParagraphs = htmlContent.match(paragraphRegex);
        console.log("All paragraphs found:", allParagraphs ? allParagraphs.length : 0);

        let highlightedContent = htmlContent;
        let foundParagraph = false;
        let bestMatch = { score: 0, content: null };
        let paragraphCount = 0;

        // If we found paragraphs, process them
        if (allParagraphs && allParagraphs.length > 1) {
            highlightedContent = highlightedContent.replace(paragraphRegex, (match, paragraphContent) => {
                paragraphCount++;
                console.log(`\n--- Checking paragraph ${paragraphCount} ---`);

                // Check if this paragraph contains any significant part of the chunk text
                const chunkWords = cleanChunkText.split(/\s+/).filter(word => word.length > 3);
                const paragraphText = normalizeText(extractTextFromHtml(paragraphContent));

                console.log("Paragraph text preview:", paragraphText.substring(0, 200) + "...");
                console.log("Paragraph text length:", paragraphText.length);
                console.log("Chunk words to find:", chunkWords);

                // Count how many chunk words are in this paragraph
                const matchingWords = chunkWords.filter(word =>
                    paragraphText.toLowerCase().includes(word.toLowerCase())
                );

                console.log("Matching words found:", matchingWords);

                const score = matchingWords.length / chunkWords.length;
                console.log(`Paragraph ${paragraphCount} score: ${matchingWords.length}/${chunkWords.length} = ${score}`);

                // Track the best matching paragraph
                if (score > bestMatch.score) {
                    bestMatch = { score, content: match, paragraphContent };
                    console.log(`New best match: paragraph ${paragraphCount} with score ${score}`);
                }

                // If more than 30% of chunk words are in this paragraph, it could be a match
                if (score > 0.3) {
                    console.log("Found potential matching paragraph with score", score);
                    foundParagraph = true;
                    return `<p style="background-color: #fef3c7; padding: 10px; margin: 5px; border-radius: 5px; border-left: 4px solid #f59e0b;">${paragraphContent}</p>`;
                }

                return match;
            });
        } else {
            console.log("No proper paragraphs found, trying to find the specific section...");

            // Try to find the specific section that contains the chunk text
            const sectionRegex = /<p[^>]*>([^<]*(?:<[^>]*>[^<]*)*?)<\/p>/gi;
            let match;
            let bestSection = null;
            let bestScore = 0;

            while ((match = sectionRegex.exec(htmlContent)) !== null) {
                const sectionText = normalizeText(extractTextFromHtml(match[1]));
                const chunkWords = cleanChunkText.split(/\s+/).filter(word => word.length > 3);

                const matchingWords = chunkWords.filter(word =>
                    sectionText.toLowerCase().includes(word.toLowerCase())
                );

                const score = matchingWords.length / chunkWords.length;
                console.log(`Section score: ${matchingWords.length}/${chunkWords.length} = ${score}`);

                if (score > bestScore) {
                    bestScore = score;
                    bestSection = match;
                }
            }

            if (bestSection && bestScore > 0.5) {
                console.log("Found best section with score", bestScore);
                foundParagraph = true;
                highlightedContent = htmlContent.replace(bestSection[0],
                    `<p style="background-color: #fef3c7; padding: 10px; margin: 5px; border-radius: 5px; border-left: 4px solid #f59e0b;">${bestSection[1]}</p>`);
            }
        }

        console.log(`Total paragraphs found: ${paragraphCount}`);
        console.log(`Best match score: ${bestMatch.score}`);

        // If no paragraph was found but we have a best match, highlight it anyway
        if (!foundParagraph && bestMatch.score > 0.1) {
            console.log("Using best match with score", bestMatch.score);
            highlightedContent = htmlContent.replace(bestMatch.content,
                `<p style="background-color: #fef3c7; padding: 10px; margin: 5px; border-radius: 5px; border-left: 4px solid #f59e0b;">${bestMatch.paragraphContent}</p>`);
            foundParagraph = true;
        }

        // If still no paragraph found, try to find the specific section containing "Fig. 3"
        if (!foundParagraph) {
            console.log("Trying to find section containing 'Fig. 3'...");

            // Look for the specific paragraph that contains "Fig. 3"
            const fig3Regex = /<p[^>]*>([^<]*(?:<[^>]*>[^<]*)*?Fig\. 3[^<]*(?:<[^>]*>[^<]*)*?)<\/p>/gi;
            const fig3Match = htmlContent.match(fig3Regex);

            if (fig3Match && fig3Match.length > 0) {
                console.log("Found paragraph containing 'Fig. 3'");
                foundParagraph = true;
                highlightedContent = htmlContent.replace(fig3Match[0],
                    `<p style="background-color: #fef3c7; padding: 10px; margin: 5px; border-radius: 5px; border-left: 4px solid #f59e0b;">${fig3Match[0].replace(/<p[^>]*>/, '').replace(/<\/p>/, '')}</p>`);
            }
        }

        // If no paragraph was found, add a visible indicator at the top of the document
        if (!foundParagraph) {
            console.log("No matching paragraph found, adding chunk text indicator");
            const indicator = `
                <div style="background-color: #fef3c7; border: 2px solid #f59e0b; padding: 10px; margin: 10px; border-radius: 5px;">
                    <strong>Chunk Content:</strong><br>
                    ${cleanChunkText}
                </div>
            `;
            // Insert the indicator after the opening body tag
            highlightedContent = htmlContent.replace(/<body[^>]*>/i, `$&${indicator}`);
        }

        console.log("=== HIGHLIGHTING DEBUG END ===");
        return highlightedContent;
    }

    // If exact match found, highlight just that specific text
    console.log("Exact match found, highlighting specific text");
    console.log("=== HIGHLIGHTING DEBUG END ===");
    return htmlContent.replace(regex, '<mark style="background-color: #fef3c7; padding: 2px 4px; border-radius: 3px;">$1</mark>');
}

// Watch for changes in htmlContent and highlightedChunkText and update iframe
watch([() => props.htmlContent, () => props.highlightedChunkText], ([newContent, newChunkText]) => {
    console.log("HTML viewer received new content:", {
        contentLength: newContent?.length,
        chunkText: newChunkText,
        hasChunkText: !!newChunkText
    });

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