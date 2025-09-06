import { defineStore } from "pinia";
import type { User } from "~/types/models";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean | null; // null = not checked, false = checked but not authenticated, true = authenticated
}

export const useAuthStore = defineStore("auth", {
  state: (): AuthState => ({
    user: null,
    isAuthenticated: null,
  }),

  getters: {
    getUser: (state: AuthState) => state.user,
    isLoggedIn: (state: AuthState) =>
      state.isAuthenticated === true && !!state.user,
  },

  actions: {
    async login(email: string, password: string) {
      const config = useRuntimeConfig();
      const apiUrl = config.public.apiBase;

      try {
        // Create form data for OAuth2PasswordRequestForm
        const formData = new FormData();
        formData.append("username", email);
        formData.append("password", password);

        await $fetch<{ message: string }>(`${apiUrl}/auth/token`, {
          method: "POST",
          body: formData,
          credentials: "include", // Include cookies in the request
        });

        // Set authentication state
        this.isAuthenticated = true;

        // Fetch user info
        await this.fetchUser();

        return { success: true };
      } catch (error: unknown) {
        console.error("Login error:", error);
        this.isAuthenticated = false;
        return {
          success: false,
          error:
            error &&
            typeof error === "object" &&
            "data" in error &&
            error.data &&
            typeof error.data === "object" &&
            "detail" in error.data
              ? String(error.data.detail)
              : "Login failed",
        };
      }
    },

    async register(userData: {
      email: string;
      password: string;
      full_name?: string;
    }) {
      const config = useRuntimeConfig();
      const apiUrl = config.public.apiBase;

      try {
        await $fetch(`${apiUrl}/auth/users/`, {
          method: "POST",
          body: userData,
        });

        return { success: true };
      } catch (error: unknown) {
        console.error("Registration error:", error);
        return {
          success: false,
          error:
            error &&
            typeof error === "object" &&
            "data" in error &&
            error.data &&
            typeof error.data === "object" &&
            "detail" in error.data
              ? String(error.data.detail)
              : "Registration failed",
        };
      }
    },

    async fetchUser() {
      const config = useRuntimeConfig();
      const apiUrl = config.public.apiBase;

      try {
        const user = await $fetch<User>(`${apiUrl}/auth/users/me`, {
          credentials: "include", // Include cookies in the request
        });

        this.user = user;
      } catch (error: unknown) {
        if (
          error &&
          typeof error === "object" &&
          "status" in error &&
          error.status !== 401
        ) {
          console.error("Fetch user error:", error);
        }
        // If fetching user fails, clear state but don't call logout
        this.user = null;
        this.isAuthenticated = false;
        throw error; // Re-throw so initializeAuth can handle it
      }
    },

    async logout() {
      const config = useRuntimeConfig();
      const apiUrl = config.public.apiBase;

      try {
        // Call logout endpoint to clear cookie
        await $fetch(`${apiUrl}/auth/logout`, {
          method: "POST",
          credentials: "include",
        });
      } catch {
        console.error("Logout error");
        // Continue with logout even if the API call fails
      }

      // Clear local state
      this.user = null;
      this.isAuthenticated = false;

      // Redirect to login
      await navigateTo("/login");
    },

    async initializeAuth() {
      // Check if user is authenticated by trying to fetch user info
      try {
        await this.fetchUser();
        this.isAuthenticated = true;
      } catch {
        // User is not authenticated
        this.isAuthenticated = false;
        this.user = null;
      }
    },
  },
});
