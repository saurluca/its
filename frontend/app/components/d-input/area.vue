<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  placeholder?: string | undefined
  rows?: string | number
  cols?: string | number
}

const props = defineProps<Props>()
const { placeholder = undefined, rows = 4, cols = 30 } = props

const model = defineModel<string>()

// Convert rows and cols to numbers if they're strings
const rowsValue = computed(() => typeof rows === 'string' ? parseInt(rows, 10) : rows)
const colsValue = computed(() => typeof cols === 'string' ? parseInt(cols, 10) : cols)
</script>

<template>
  <textarea
    v-model="model"
    :placeholder="placeholder"
    :rows="rowsValue"
    :cols="colsValue"
    class="w-full rounded-md bg-gray-100 px-3 py-2 text-sm leading-normal ring-blue-600 outline-none placeholder:text-gray-400 focus:border-transparent focus:ring-2 resize-vertical"
  ></textarea>
</template> 