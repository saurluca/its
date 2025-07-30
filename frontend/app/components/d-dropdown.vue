<script setup lang="ts">
import { computed } from "vue";

interface Option {
  value: string;
  label: string;
}

interface Props {
  options: Option[] | string[];
  placeholder?: string;
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
</script>

<template>
  <select
    v-model="model"
    class="w-full rounded-md bg-gray-100 px-2 py-2 text-sm leading-normal ring-blue-600 outline-none placeholder:text-gray-400 focus:border-transparent focus:ring-2 appearance-none"
  >
    <option v-if="placeholder" value="" disabled>{{ placeholder }}</option>
    <option
      v-for="option in normalizedOptions"
      :key="option.value"
      :value="option.value"
    >
      {{ option.label }}
    </option>
  </select>
</template>
