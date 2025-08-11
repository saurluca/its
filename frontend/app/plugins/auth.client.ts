import { useAuthStore } from "~/stores/auth";

export default defineNuxtPlugin(async () => {
  const authStore = useAuthStore();

  // Initialize authentication state on app start only if not already done
  if (authStore.isAuthenticated === null) {
    await authStore.initializeAuth();
  }
});
