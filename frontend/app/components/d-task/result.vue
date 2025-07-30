<script setup lang="ts">
import type { Task } from "~/types/models";

const props = defineProps<{
  task: Task;
  index: number;
  userAnswer: string;
  isCorrect: boolean;
  feedback: string;
}>();
</script>

<template>
  <div class="bg-white p-6 rounded-lg shadow">
    <div class="flex justify-between">
      <h3 class="text-lg font-medium">Task {{ index + 1 }}</h3>
      <span
        class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
        :class="
          isCorrect ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        "
      >
        {{ isCorrect ? "Correct" : "Incorrect" }}
      </span>
    </div>
    <!-- <p class="mt-2 text-gray-700">{{ task.question }}</p> -->

    <div class="mt-4">
      <p class="text-gray-700">
        <span class="font-semibold">Your answer: </span>
        <span
          :class="{
            'font-semibold': true,
            'text-green-600': isCorrect,
            'text-red-600': !isCorrect,
          }"
          >{{ userAnswer || "Not answered" }}</span
        >
      </p>
      <p v-if="!isCorrect" class="text-gray-700 mt-1">
        <span class="font-semibold">Correct answer: </span>
        <span class="">{{ task.correct_answer }}</span>
      </p>
      <p v-if="!isCorrect" class="text-gray-700 mt-4">
        <span class="font-semibold">Explanation: </span>
        <span class="">{{ feedback }}</span>
      </p>
    </div>
  </div>
</template>
