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
  if (process.server) return

  const authStore = useAuthStore()

  // Initialize auth if not already done
  if (!authStore.isAuthenticated) {
    await authStore.initializeAuth()
  }

  // Check if route requires authentication
  const isPublicRoute = publicRoutes.includes(to.path)

  // Redirect to login if not authenticated and trying to access protected route
  if (!isPublicRoute && !authStore.isLoggedIn) {
    return navigateTo('/login')
  }

  // Redirect authenticated users away from login/register pages
  if (isPublicRoute && authStore.isLoggedIn && ['/login', '/register'].includes(to.path)) {
    return navigateTo('/documents')
  }

  // Redirect root to documents
  if (to.path === "/") {
    return navigateTo("/documents");
  }
});
