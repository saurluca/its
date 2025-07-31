<script setup lang="ts">
import { computed, onMounted, onUnmounted } from "vue";
import type { Task } from "~/types/models";

const props = defineProps<{
  task: Task;
  index: number;
  modelValue: string;
  disabled: boolean;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void;
  (e: "evaluate"): void;
}>();

// Create a computed property with getter and setter
const answer = computed({
  get: () => props.modelValue,
  set: (value: string) => emit("update:modelValue", value),
});

// Shuffle function for randomizing options
function shuffleArray<T>(array: T[]): T[] {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

// Computed property for shuffled multiple choice options
const shuffledOptions = computed(() => {
  if (props.task.type === 'multiple_choice' && props.task.options) {
    return shuffleArray(props.task.options);
  }
  return props.task.options || [];
});

// Hotkey handler function
function handleKeyPress(event: KeyboardEvent) {
  // Only handle hotkeys if not disabled and task is multiple choice
  if (props.disabled || props.task.type !== 'multiple_choice') {
    return;
  }

  const key = event.key;
  const optionIndex = parseInt(key) - 1; // Convert 1-4 to 0-3

  // Check if it's a valid number key (1-4) and within range of available options
  if (key >= '1' && key <= '4' && optionIndex < shuffledOptions.value.length) {
    // Select the answer
    answer.value = shuffledOptions.value[optionIndex];
    
    // Automatically evaluate the answer
    emit("evaluate");
  }
}

// Set up and clean up event listeners
onMounted(() => {
  document.addEventListener('keydown', handleKeyPress);
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyPress);
});

console.log("task", props.task);
</script>

<template>
  <div class="bg-white p-6 rounded-lg shadow w-2xl">
    <div class="flex justify-between">
      <h3 class="text-lg font-medium">Task {{ index + 1 }}</h3>
      <span
        class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
      >
        {{
          task.type === "true_false"
            ? "True/False"
            : task.type === "multiple_choice"
              ? "Multiple Choice"
              : "Free Text"
        }}
      </span>
    </div>
    <p class="mt-2">{{ task.question }}</p>

    <!-- True/False Answer -->
    <div v-if="task.type === 'true_false'" class="mt-4">
      <DButtonRadio
        v-model="answer"
        :name="`answer-${task.id}`"
        :options="['True', 'False']"
      />
    </div>

    <!-- Multiple Choice Answer -->
    <div v-else-if="task.type === 'multiple_choice'" class="mt-4">
      <div class="space-y-2">
        <DButtonRadio
          v-model="answer"
          :name="`answer-${task.id}`"
          :options="shuffledOptions"
          :disabled="disabled"
        />
        <!-- Hotkey hint -->
        <div class="text-xs text-gray-500 mt-2">
          💡 Tip: Press <kbd class="px-1 py-0.5 bg-gray-100 rounded text-xs">1</kbd> - <kbd class="px-1 py-0.5 bg-gray-100 rounded text-xs">{{ shuffledOptions.length }}</kbd> to quickly select and evaluate answers
        </div>
      </div>
    </div>

    <!-- Free Text Answer -->
    <div v-else class="mt-4">
      <DInputArea v-model="answer" rows="4" placeholder="Enter your answer" />
    </div>
  </div>
</template>
