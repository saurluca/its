import { defineStore } from 'pinia'
import type { User } from '~/types/models'


interface AuthState {
    user: User | null;
    isAuthenticated: boolean;
}

export const useAuthStore = defineStore('auth', {
    state: (): AuthState => ({
        user: null,
        isAuthenticated: false,
    }),

    getters: {
        getUser: (state: AuthState) => state.user,
        isLoggedIn: (state: AuthState) => state.isAuthenticated && !!state.user,
    },

    actions: {
        async login(email: string, password: string) {
            const config = useRuntimeConfig()
            const apiUrl = config.public.apiBase

            try {
                // Create form data for OAuth2PasswordRequestForm
                const formData = new FormData()
                formData.append('username', email)
                formData.append('password', password)

                const response = await $fetch<{ message: string }>(`${apiUrl}/auth/token`, {
                    method: 'POST',
                    body: formData,
                    credentials: 'include', // Include cookies in the request
                })

                // Set authentication state
                this.isAuthenticated = true

                // Fetch user info
                await this.fetchUser()

                return { success: true }
            } catch (error: any) {
                console.error('Login error:', error)
                return {
                    success: false,
                    error: error?.data?.detail || 'Login failed'
                }
            }
        },

        async register(userData: {
            email: string;
            password: string;
            full_name?: string;
        }) {
            const config = useRuntimeConfig()
            const apiUrl = config.public.apiBase

            try {
                await $fetch(`${apiUrl}/auth/users/`, {
                    method: 'POST',
                    body: userData,
                })

                return { success: true }
            } catch (error: any) {
                console.error('Registration error:', error)
                return {
                    success: false,
                    error: error?.data?.detail || 'Registration failed'
                }
            }
        },

        async fetchUser() {
            const config = useRuntimeConfig()
            const apiUrl = config.public.apiBase

            try {
                const user = await $fetch<User>(`${apiUrl}/auth/users/me/`, {
                    credentials: 'include', // Include cookies in the request
                })

                this.user = user
            } catch (error) {
                console.error('Fetch user error:', error)
                // If fetching user fails, logout
                this.logout()
            }
        },

        async logout() {
            const config = useRuntimeConfig()
            const apiUrl = config.public.apiBase

            try {
                // Call logout endpoint to clear cookie
                await $fetch(`${apiUrl}/auth/logout`, {
                    method: 'POST',
                    credentials: 'include',
                })
            } catch (error) {
                console.error('Logout error:', error)
            }

            // Clear local state
            this.user = null
            this.isAuthenticated = false

            // Redirect to login
            await navigateTo('/login')
        },

        async initializeAuth() {
            // Check if user is authenticated by trying to fetch user info
            try {
                await this.fetchUser()
                this.isAuthenticated = true
            } catch (error) {
                // User is not authenticated
                this.isAuthenticated = false
                this.user = null
            }
        },
    },
})