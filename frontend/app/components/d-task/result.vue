<script setup lang="ts">
import type { Task } from "~/types/models";

defineProps<{
  task: Task;
  index: number;
  userAnswer: string;
  status: "correct" | "partial" | "incorrect";
  feedback: string;
}>();
</script>

<template>
  <div class="bg-white p-6 rounded-lg shadow">
    <div class="flex justify-between">
      <h3 class="text-lg font-medium">Task {{ index + 1 }}</h3>
      <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium" :class="{
        'bg-green-100 text-green-800': status === 'correct',
        'bg-yellow-100 text-yellow-800': status === 'partial',
        'bg-red-100 text-red-800': status === 'incorrect',
      }">
        {{ status === 'correct' ? 'Correct' : (status === 'partial' ? 'Partially correct' : 'Incorrect') }}
      </span>
    </div>

    <div class="mt-4">
      <p class="text-gray-700">
        <span class="font-semibold">Your answer: </span>
        <span :class="{
          'font-semibold': true,
          'text-green-600': status === 'correct',
          'text-yellow-700': status === 'partial',
          'text-red-600': status === 'incorrect',
        }">{{ userAnswer || "Not answered" }}</span>
      </p>
      <p v-if="status !== 'correct' && task.type === 'multiple_choice'" class="text-gray-700 mt-1">
        <span class="font-semibold">Correct answer: </span>
        <span class="">{{task.answer_options.find(option => option.is_correct)?.answer || 'Not available'}}</span>
      </p>
      <p v-if="status !== 'correct'" class="text-gray-700 mt-4">
        <span class="font-semibold">Explanation: </span>
        <span class="">{{ feedback }}</span>
      </p>
      <div class="text-xs text-gray-400 text-center mt-2">
        Press <kbd class="px-1 py-0.5 bg-gray-100 rounded text-xs">Enter</kbd> to continue
      </div>
    </div>
  </div>
</template>
