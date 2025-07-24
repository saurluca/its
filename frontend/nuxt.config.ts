import tailwindcss from "@tailwindcss/vite"

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: "2025-01-23",
  future: { compatibilityVersion: 4 },
  vite: { plugins: [tailwindcss()] },
  ssr: false,

  devtools: { enabled: false },

  css: ["@/app.css"],
  modules: ["@vueuse/nuxt", "nuxt-auth-utils", "@nuxt/fonts", "@pinia/nuxt"],

  fonts: { experimental: { processCSSVariables: true } },

  runtimeConfig: {
    // Postmark credentials
    postmarkServerToken: "temp",
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
})
