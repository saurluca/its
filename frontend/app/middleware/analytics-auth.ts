export default defineNuxtRouteMiddleware((_to) => {
  // List of emails that are allowed to access analytics dashboard
   const allowedEmails = [
    'daniel.odhiambo@gess.ethz.ch',
    'adtoth@ethz.ch',
  ];
  
  try {
    const authStore = useAuthStore();
    
    if (!authStore.isLoggedIn) {
      return navigateTo('/login');
    }
    
    const userEmail = authStore.user?.email;
    if (!userEmail || !allowedEmails.includes(userEmail)) {
      return navigateTo('/unauthorized');
    }
  } catch {
    return navigateTo('/login');
  }
});