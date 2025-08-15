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
      <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-medium" :class="{
        'bg-green-100 text-green-800': status === 'correct',
        'bg-yellow-100 text-yellow-800': status === 'partial',
        'bg-red-100 text-red-800': status === 'incorrect',
      }">
        {{ status === 'correct' ? 'Correct' : (status === 'partial' ? 'Partially correct' : 'Incorrect') }}
      </span>
    </div>

    <div class="mt-4">
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
