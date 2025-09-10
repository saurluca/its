<script setup lang="ts">
// code here
</script>

<template>
  <div class="flex h-full max-h-screen flex-col sm:flex-row bg-gray-50">
    <DPageSidebar />
    <main class="flex-1 overflow-y-auto p-2 sm:p-4">
      <slot></slot>
    </main>
    <DSnackbar />
  </div>
</template>
