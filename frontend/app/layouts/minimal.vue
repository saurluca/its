<script setup lang="ts">
// Minimal layout without sidebar
</script>

<template>
  <div class="h-full bg-gray-100">
    <main class="h-full">
      <slot></slot>
    </main>
    <DSnackbar />
  </div>
</template>
