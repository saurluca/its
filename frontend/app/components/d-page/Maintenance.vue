<script setup lang="ts">
import { ConstructionIcon } from "lucide-vue-next";
</script>

<template>
  <div class="flex h-full w-full items-center justify-center p-4">
    <div
      class="mx-auto max-w-96 rounded-md border border-orange-100 bg-orange-200/60 p-8"
    >
      <div
        class="mb-2 flex items-center gap-3 text-lg font-medium text-orange-900"
      >
        <ConstructionIcon class="size-6 text-orange-900" />
        Maintenance
      </div>
      <div class="mb-2 text-sm text-orange-800">
        We are currently performing system maintenance. Please try again
        shortly.
      </div>
      <div class="text-sm text-orange-800">
        In urgent cases, please contact the support team at
        <a
          href="mailto:support@its.org"
          class="font-medium text-orange-900 hover:underline"
          >support@its.org</a
        >.
      </div>
    </div>
  </div>
</template>
