<script setup lang="ts">
definePageMeta({
  layout: "minimal",
});

const authStore = useAuthStore();

// Automatically logout when this page is accessed
onMounted(() => {
  authStore.logout();
});
</script>

<template>
  <div class="h-full bg-gray-100 flex items-center justify-center">
    <div class="bg-white p-8 rounded-lg shadow-md text-center">
      <h1 class="text-2xl font-semibold text-gray-900 mb-4">Logging out...</h1>
      <p class="text-gray-600">You will be redirected to the login page.</p>
    </div>
  </div>
</template>
