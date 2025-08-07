const publicRoutes = [
  "/login",
  "/logout",
  "/offline",
  "/register",
  "/up",
  "/forgot-password",
  "/reset-password",
];

export default defineNuxtRouteMiddleware(async (to, from) => {
  // Skip middleware on server-side during SSR
  if (process.server) return;

  const authStore = useAuthStore();

  // Check if route requires authentication
  const isPublicRoute = publicRoutes.includes(to.path);

  // Only initialize auth if we're not on a public route or if we haven't initialized yet
  if (!isPublicRoute && authStore.isAuthenticated === null) {
    await authStore.initializeAuth();
  }

  // Redirect to login if not authenticated and trying to access protected route
  if (!isPublicRoute && !authStore.isLoggedIn) {
    return navigateTo("/login");
  }

  // Redirect authenticated users away from login/register pages
  if (
    isPublicRoute &&
    authStore.isLoggedIn &&
    ["/login", "/register"].includes(to.path)
  ) {
    return navigateTo("/documents");
  }

  // Redirect root to documents
  if (to.path === "/") {
    return navigateTo("/documents");
  }
});
