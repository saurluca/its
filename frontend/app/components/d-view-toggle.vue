<script setup lang="ts">
import { ref, onMounted, watch } from "vue";

const props = defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
}>();

const isTeacherView = ref(props.modelValue);

// Load from localStorage on component mount
onMounted(() => {
  const savedView = localStorage.getItem("viewMode");
  if (savedView !== null) {
    const parsedValue = savedView === "teacher";
    isTeacherView.value = parsedValue;
    emit("update:modelValue", parsedValue);
  }
});

// Watch for changes and save to localStorage
watch(isTeacherView, (newValue) => {
  localStorage.setItem("viewMode", newValue ? "teacher" : "student");
  emit("update:modelValue", newValue);
});

function toggleView() {
  isTeacherView.value = !isTeacherView.value;
}
</script>

<template>
  <div class="flex items-center space-x-4">
    <span
      :class="{ 'font-bold': isTeacherView, 'text-gray-500': !isTeacherView }"
      >Teacher</span
    >
    <button
      @click="toggleView"
      class="relative h-6 w-12 rounded-full bg-gray-200 transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
      :class="{ 'bg-gray-900': isTeacherView, 'bg-gray-200': !isTeacherView }"
      type="button"
      aria-pressed="false"
    >
      <span
        class="absolute inset-y-0.5 left-0.5 flex h-5 w-5 transform items-center justify-center rounded-full bg-white transition-transform duration-200 ease-in-out"
        :class="isTeacherView ? 'translate-x-6' : 'translate-x-0'"
      ></span>
    </button>
    <span
      :class="{ 'font-bold': !isTeacherView, 'text-gray-500': isTeacherView }"
      >Student</span
    >
  </div>
</template>
