<script setup lang="ts">
import { computed } from 'vue';
import type { Task } from '~/types/models';

const props = defineProps<{
  task: Task;
  index: number;
  modelValue: string;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
}>();

// Create a computed property with getter and setter
const answer = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value)
});

console.log("task",props.task)
</script>

<template>
  <div class="bg-white p-6 rounded-lg shadow">
    <div class="flex justify-between">
      <h3 class="text-lg font-medium">Task {{ index + 1 }}</h3>
      <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
        {{ task.type === 'true_false' ? 'True/False' : task.type === 'multiple_choice' ? 'Multiple Choice' : 'Free Text' }}
      </span>
    </div>
    <p class="mt-2 text-gray-700">{{ task.question }}</p>
    
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
      <DButtonRadio
        v-model="answer"
        :name="`answer-${task.id}`"
        :options="task.options || []"
      />
    </div>
    
    <!-- Free Text Answer -->
    <div v-else class="mt-4">
      <DInputArea 
        v-model="answer"
        rows="4"
        placeholder="Enter your answer"
      />
    </div>
  </div>
</template> 