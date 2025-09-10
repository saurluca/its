<script setup lang="ts">
import { useNotificationsStore } from "~/stores/notifications";
import { onMounted } from "vue";
definePageMeta({
  layout: "minimal",
});

const email = ref("");
const password = ref("");
const loading = ref(false);

const authStore = useAuthStore();
const notifications = useNotificationsStore();

onMounted(() => {
  const route = useRoute();
  if (route.query.registered === "1") {
    notifications.success("Registration successful. You can now log in.");
  }
});

async function login() {
  try {
    loading.value = true;

    const result = await authStore.login(email.value, password.value);

    if (result.success) {
      notifications.success("Welcome back!");
      await navigateTo("/");
    } else {
      notifications.error(result.error || "Invalid credentials");
    }
  } catch {
    notifications.error("Login failed");
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="h-full px-8 pt-24">
    <div class="mx-auto max-w-sm rounded-lg border border-gray-50 bg-white p-8 shadow">
      <h1 class="mb-4 text-center text-2xl font-semibold text-gray-900">ITS</h1>

      <form @submit.prevent="login" class="flex flex-col gap-4">
        <div class="flex flex-col gap-1">
          <d-label for="email">Email</d-label>
          <d-input v-model="email" type="email" id="email" name="email" required placeholder="Your email address" />
        </div>

        <div class="flex flex-col gap-1">
          <d-label for="password">Password</d-label>
          <d-input v-model="password" type="password" id="password" name="password" required
            placeholder="Your password" />
        </div>

        <div class="flex flex-col gap-2">
          <DButton :loading="loading" type="submit" text-center>Login</DButton>
          <DButton to="/register" variant="secondary" text-center>No account yet?</DButton>
          <DButton to="/forgot-password" variant="secondary" text-center>Forgot Password?</DButton>
        </div>
      </form>
    </div>
  </div>
</template>
