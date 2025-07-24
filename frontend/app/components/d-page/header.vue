<script setup lang="ts">
defineProps<{
  title: string;
}>();
</script>

<template>
  <div class="flex justify-between items-center mb-8">
    <h1 class="text-3xl font-bold">{{ title }}</h1>
    <slot></slot>
  </div>
</template> 