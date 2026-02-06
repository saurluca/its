import type { RouteLocationNormalized } from "vue-router";

const publicRoutes = [
  "/login",
  "/logout",
  "/offline",
  "/register",
  "/up",
  "/forgot-password",
  "/reset-password",
];

export default defineNuxtRouteMiddleware(
  async (to: RouteLocationNormalized, _from: RouteLocationNormalized) => {
    // Skip middleware on server-side during SSR
    if (import.meta.server) return;
    // Check if route requires authentication
    const isPublicRoute = publicRoutes.includes(to.path);
    
    // For public routes, allow navigation without auth check
    if (isPublicRoute) {
      try {
        const authStore = useAuthStore();
        if (
          authStore.isLoggedIn &&
          ["/login", "/register"].includes(to.path)
        ) {
          return navigateTo("/");
        }
      } catch {
        // Pinia not ready yet, allow navigation
        return;
      }
      return;
    }
    
    // For protected routes, ensure auth is initialized
    try {
      const authStore = useAuthStore();
      
      // Only initialize auth if we haven't checked yet
      if (authStore.isAuthenticated === null) {
        await authStore.initializeAuth();
      }
      
      // Redirect to login if not authenticated
      if (!authStore.isLoggedIn) {
        return navigateTo("/login");
      }
    } catch {
      // If Pinia isn't ready, redirect to login as safe fallback
      return navigateTo("/login");
    }
  }
);