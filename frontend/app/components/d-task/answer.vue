<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
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

// Shuffle function for randomizing options (Fisher–Yates)
function shuffleArray<T>(items: T[]): T[] {
  const array = [...items];
  for (let i = array.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    const temp = array[i]!;
    array[i] = array[j]!;
    array[j] = temp;
  }
  return array;
}

// Keep a stable shuffled order for the current question until it changes
const shuffledOptions = ref<string[]>([]);

function computeShuffledOptions() {
  if (props.task.type === 'multiple_choice' && props.task.answer_options) {
    const options = props.task.answer_options.map((option) => option.answer);
    shuffledOptions.value = shuffleArray(options);
  } else {
    shuffledOptions.value = [];
  }
}

onMounted(() => {
  computeShuffledOptions();
});

// Recompute when the question changes (use id as a stable switch)
watch(
  () => props.task.id,
  () => {
    computeShuffledOptions();
  }
);

// Hotkey handler function
function handleKeyPress(event: KeyboardEvent) {
  // Only handle hotkeys if not disabled and task is multiple choice
  if (props.disabled || props.task.type !== 'multiple_choice') {
    return;
  }

  const key = event.key;
  // Only digits 1..N without modifiers
  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
  if (!/^\d$/.test(key)) return;

  const optionIndex = parseInt(key, 10) - 1; // Convert 1..N to 0..N-1
  if (optionIndex >= 0 && optionIndex < shuffledOptions.value.length) {
    event.preventDefault();
    answer.value = shuffledOptions.value[optionIndex]!;
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
      <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
        {{
          task.type === "multiple_choice"
            ? "Multiple Choice"
            : "Free Text"
        }}
      </span>
    </div>
    <p class="mt-2">{{ task.question }}</p>

    <!-- Multiple Choice Answer -->
    <div v-if="task.type === 'multiple_choice'" class="mt-4">
      <div class="space-y-2">
        <DButtonRadio v-model="answer" :name="`answer-${task.id}`" :options="shuffledOptions" :disabled="disabled" />
        <!-- Hotkey hint -->
        <div class="text-xs text-gray-500 mt-2">
          💡 Tip: Press <kbd class="px-1 py-0.5 bg-gray-100 rounded text-xs">1</kbd> - <kbd
            class="px-1 py-0.5 bg-gray-100 rounded text-xs">{{ shuffledOptions.length }}</kbd> to quickly select and
          evaluate answers
        </div>
      </div>
    </div>

    <!-- Free Text Answer -->
    <div v-else class="mt-4">
      <DInputArea v-model="answer" rows="4" placeholder="Enter your answer" :disabled="disabled" />
    </div>
  </div>
</template>
