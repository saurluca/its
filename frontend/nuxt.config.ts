import tailwindcss from "@tailwindcss/vite";

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: "2025-01-23",
  future: { compatibilityVersion: 4 },
  vite: { plugins: [tailwindcss()] },
  ssr: false,

  devtools: { enabled: false },

  css: ["@/app.css"],
  modules: ["@vueuse/nuxt", "@nuxt/fonts", "@pinia/nuxt"],

  fonts: { experimental: { processCSSVariables: true } },

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || "http://localhost:8000", // Default for dev
    },
  },

  nitro: {
    preset: "bun",

    storage: {
      limiter: {
        driver: "memory",
      },
    },
  },

  app: {
    head: {
      title: "ITS",
    },
  },
});
