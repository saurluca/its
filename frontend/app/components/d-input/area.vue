<script setup lang="ts">
import { computed } from "vue";

interface Props {
  placeholder?: string | undefined;
  rows?: string | number;
  cols?: string | number;
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: undefined,
  rows: 4,
  cols: 30,
  disabled: false,
});

const model = defineModel<string>();

// Convert rows and cols to numbers if they're strings
const rowsValue = computed(() =>
  typeof props.rows === "string" ? parseInt(props.rows, 10) : props.rows,
);
const colsValue = computed(() =>
  typeof props.cols === "string" ? parseInt(props.cols, 10) : props.cols,
);

// Compute textarea classes, graying out text if disabled
const textareaClass = computed(() => [
  "w-full rounded-md bg-gray-100 px-3 py-2 text-sm leading-normal ring-blue-600 outline-none placeholder:text-gray-400 focus:border-transparent focus:ring-2 resize-vertical",
  props.disabled ? "text-gray-500" : ""
]);
</script>

<template>
  <textarea v-model="model" :placeholder="props.placeholder" :rows="rowsValue" :cols="colsValue"
    :disabled="props.disabled" :class="textareaClass"></textarea>
</template>
