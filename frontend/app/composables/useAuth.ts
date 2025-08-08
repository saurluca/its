export const useAuth = () => {
  const authStore = useAuthStore();

  return {
    // State
    user: computed(() => authStore.user),
    isAuthenticated: computed(() => authStore.isLoggedIn),

    // Actions
    login: authStore.login,
    register: authStore.register,
    logout: authStore.logout,
    fetchUser: authStore.fetchUser,
    initializeAuth: authStore.initializeAuth,
  };
};

export const useAuthenticatedFetch = () => {
  const authStore = useAuthStore();
  const config = useRuntimeConfig();

  const $authFetch = $fetch.create({
    baseURL: config.public.apiBase,
    onRequest({ options }) {
      // Include credentials (cookies) in all requests
      options.credentials = "include";
    },
    onResponseError({ response }) {
      if (response.status === 401) {
        authStore.logout();
      }
    },
  });

  return {
    $authFetch: $authFetch as any,
  };
};
