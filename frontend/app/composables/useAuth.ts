
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

  const baseURL = config.public.apiBase;

  const $authFetch = async (url: string, options: any = {}) => {
    let finalUrl = url;

    // Prepare headers - don't set Content-Type for FormData
    const headers: Record<string, string> = { ...options.headers };
    
    // Only set Content-Type to application/json if:
    // 1. Not already set by caller
    // 2. Body is not FormData
    // 3. Body exists and is not undefined
    if (!headers['Content-Type'] && 
        !(options.body instanceof FormData) && 
        options.body !== undefined) {
      headers['Content-Type'] = 'application/json';
    }

    return await $fetch(finalUrl, {
      baseURL: baseURL,
      credentials: "include",
      ...options,
      headers,
    });
  };

  return {
    $authFetch: $authFetch as any,
  };
};