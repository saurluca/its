import tailwindcss from "@tailwindcss/vite";
import type { PluginOption } from "vite";

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: "2025-01-23",
  future: { compatibilityVersion: 4 },
  vite: { plugins: [tailwindcss()] as PluginOption[] },
  ssr: false,

  devtools: { enabled: false },

  css: ["@/app.css"],
  modules: ["@vueuse/nuxt", "@nuxt/fonts", "@pinia/nuxt", "@nuxt/eslint"],

  fonts: { experimental: { processCSSVariables: true } },

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || "https://api.dodoit.net",
    },
  },

  nitro: {
    preset: "static",

    storage: {
      limiter: {
        driver: "memory",
      },
    },
  },

  typescript: {
    typeCheck: true,
  },

  app: {
    head: {
      title: "ITS",
    },
  },
});
