export default defineNuxtPlugin(async () => {
    const authStore = useAuthStore()

    // Initialize authentication state on app start
    await authStore.initializeAuth()
})