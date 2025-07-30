<script setup lang="ts">
import { computed } from "vue";

interface Option {
  value: string;
  label: string;
}

interface Props {
  options: Option[] | string[];
  name: string;
  direction?: "horizontal" | "vertical";
  disabled?: boolean;
}

const props = defineProps<Props>();
const model = defineModel<string>();

// Process options to ensure they're in the correct format
const normalizedOptions = computed(() => {
  if (props.options.length === 0) return [];

  // If the first item is a string, convert all items to Option format
  if (typeof props.options[0] === "string") {
    return (props.options as string[]).map((option) => ({
      value: option,
      label: option,
    }));
  }

  // Otherwise, assume they're already in Option format
  return props.options as Option[];
});

const containerClass = computed(() => {
  return props.direction === "horizontal"
    ? "flex flex-row gap-4"
    : "flex flex-col gap-2";
});
</script>

<template>
  <div :class="containerClass">
    <label
      v-for="option in normalizedOptions"
      :key="option.value"
      class="flex items-center gap-2 cursor-pointer"
    >
      <input
        type="radio"
        :name="name"
        :value="option.value"
        v-model="model"
        class="size-4 text-gray-900 border-gray-300 focus:ring-blue-600"
        :disabled="disabled"
      />
      <span class="text-sm text-gray-700">{{ option.label }}</span>
    </label>
  </div>
</template>
