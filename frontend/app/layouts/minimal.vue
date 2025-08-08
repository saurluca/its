<script setup lang="ts">
// Minimal layout without sidebar
</script>

<template>
  <div class="h-full">
    <main class="h-full">
      <slot></slot>
    </main>
    <DSnackbar />
  </div>
</template>
