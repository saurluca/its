// frontend/app/middleware/analytics-auth.ts
export default defineNuxtRouteMiddleware((_to) => {
  // List of emails that are allowed to access analytics dashboard
  const allowedEmails = [
    'daniel.odhiambo@gess.ethz.ch',
    'daniel.odhiambo@gess.ethz.ch',
    'daniel.odhiambo@gess.ethz.ch'
  ];

  // Get current authenticated user from the auth store
  const authStore = useAuthStore();

  // First, ensure user is logged in
  if (!authStore.isLoggedIn) {
    return navigateTo('/login');
  }

  // Now, check if the logged-in user's email is in the allowed list.
  const userEmail = authStore.user?.email;

  if (!userEmail || !allowedEmails.includes(userEmail)) {
    // If the user is not logged in or their email is not on the allowed list,
    // redirect them to an "unauthorized" page.
    return navigateTo('/unauthorized');
  }
});