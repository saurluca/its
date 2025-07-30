<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from "vue";

interface Option {
    value: string;
    label: string;
}

interface Props {
    options: Option[];
    placeholder?: string;
    searchPlaceholder?: string;
}

const props = defineProps<Props>();
const model = defineModel<string>();

const isOpen = ref(false);
const searchQuery = ref("");
const selectedOption = ref<Option | null>(null);
const searchInputRef = ref<HTMLInputElement>();
const highlightedIndex = ref(-1);

// Filter options based on search query
const filteredOptions = computed(() => {
    if (!searchQuery.value) return props.options;

    return props.options.filter(option =>
        option.label.toLowerCase().includes(searchQuery.value.toLowerCase())
    );
});

// Find the selected option based on model value
const findSelectedOption = computed(() => {
    return props.options.find(option => option.value === model.value) || null;
});

// Update selected option when model changes
const updateSelectedOption = () => {
    selectedOption.value = findSelectedOption.value;
};

// Handle option selection
const selectOption = (option: Option) => {
    model.value = option.value;
    selectedOption.value = option;
    searchQuery.value = option.label;
    isOpen.value = false;
    highlightedIndex.value = -1;
};

// Handle dropdown toggle
const toggleDropdown = () => {
    isOpen.value = !isOpen.value;
    if (isOpen.value) {
        searchQuery.value = "";
        highlightedIndex.value = -1;
        // Focus the search input after a brief delay to ensure the dropdown is rendered
        nextTick(() => {
            searchInputRef.value?.focus();
        });
    }
};

// Handle click outside to close dropdown
const dropdownRef = ref<HTMLDivElement>();

const handleClickOutside = (event: Event) => {
    if (dropdownRef.value && !dropdownRef.value.contains(event.target as Node)) {
        isOpen.value = false;
    }
};

onMounted(() => {
    document.addEventListener('click', handleClickOutside);
    document.addEventListener('keydown', handleKeydown);
    updateSelectedOption();
});

onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside);
    document.removeEventListener('keydown', handleKeydown);
});

// Handle keyboard navigation
const handleKeydown = (event: KeyboardEvent) => {
    if (!isOpen.value) return;

    switch (event.key) {
        case 'ArrowDown':
            event.preventDefault();
            highlightedIndex.value = Math.min(highlightedIndex.value + 1, filteredOptions.value.length - 1);
            break;
        case 'ArrowUp':
            event.preventDefault();
            highlightedIndex.value = Math.max(highlightedIndex.value - 1, -1);
            break;
        case 'Enter':
            event.preventDefault();
            if (highlightedIndex.value >= 0 && filteredOptions.value[highlightedIndex.value]) {
                const option = filteredOptions.value[highlightedIndex.value];
                if (option) {
                    selectOption(option);
                }
            }
            break;
        case 'Escape':
            event.preventDefault();
            isOpen.value = false;
            highlightedIndex.value = -1;
            break;
    }
};

// Watch for model changes
watch(() => model.value, updateSelectedOption);
</script>

<template>
    <div ref="dropdownRef" class="relative w-full">
        <!-- Selected value display -->
        <button type="button" @click="toggleDropdown"
            class="w-full rounded-md bg-gray-100 px-3 py-2 text-sm leading-normal ring-blue-600 outline-none placeholder:text-gray-400 focus:border-transparent focus:ring-2 appearance-none text-left flex justify-between items-center">
            <span v-if="selectedOption" class="text-gray-900">
                {{ selectedOption.label }}
            </span>
            <span v-else class="text-gray-400">
                {{ placeholder || "Select an option" }}
            </span>
            <svg class="w-4 h-4 text-gray-400" :class="{ 'rotate-180': isOpen }" fill="none" stroke="currentColor"
                viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
        </button>

        <!-- Dropdown menu -->
        <div v-if="isOpen"
            class="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-60 overflow-auto">
            <!-- Search input -->
            <div class="p-2 border-b border-gray-200">
                <input ref="searchInputRef" v-model="searchQuery" type="text"
                    :placeholder="searchPlaceholder || 'Search...'"
                    class="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    @click.stop />
            </div>

            <!-- Options list -->
            <div class="max-h-48 overflow-auto">
                <button v-for="(option, index) in filteredOptions" :key="option.value" type="button"
                    @click="selectOption(option)"
                    class="w-full px-3 py-2 text-sm text-left hover:bg-gray-100 focus:bg-gray-100 focus:outline-none"
                    :class="{
                        'bg-blue-50 text-blue-900': option.value === model,
                        'bg-blue-100 text-blue-900': index === highlightedIndex
                    }">
                    {{ option.label }}
                </button>

                <div v-if="filteredOptions.length === 0" class="px-3 py-2 text-sm text-gray-500 text-center">
                    No options found
                </div>
            </div>
        </div>
    </div>
</template>