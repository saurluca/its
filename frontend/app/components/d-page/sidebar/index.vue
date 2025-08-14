<script setup lang="ts">
import { useSessionStorage } from "@vueuse/core";
import { MenuIcon } from "lucide-vue-next";

const route = useRoute();

const collapsed = useSessionStorage("collapsed", false);

const isPublicRoute = computed(() => {
  return ["/login", "/logout"].includes(route.path);
});

const mobileMenu = ref(false);

function toggleMobileMenu() {
  collapsed.value = false;
  mobileMenu.value = !mobileMenu.value;
}

watch(() => route.path, () => {
  mobileMenu.value = false;
});
</script>

<template>
  <div class="flex">
    <header v-if="!isPublicRoute" class="flex w-full border-b border-gray-200 bg-gray-100 sm:hidden">
      <div
        class="group flex h-14 w-full cursor-default items-center justify-between gap-2 rounded-md p-2 px-2 text-sm text-gray-800">
        <NuxtLink to="/" v-show="!collapsed" class="flex items-center gap-2 px-2 py-1.5">
          <div class="line-clamp-1 flex-1">ITS</div>
        </NuxtLink>
        <div class="p-1" @click="toggleMobileMenu">
          <menu-icon class="size-4" />
        </div>
      </div>
    </header>

    <div v-if="mobileMenu"
      class="fixed top-0 left-0 z-50 flex h-full w-full flex-col justify-between bg-gray-100 sm:hidden">
      <d-page-sidebar-content @close="toggleMobileMenu" />
    </div>

    <header v-if="!isPublicRoute" class="hidden flex-col justify-between border-r border-gray-200 bg-gray-100 sm:flex"
      :class="collapsed ? 'w-fit' : 'w-[230px]'">
      <d-page-sidebar-content />
    </header>
  </div>
</template>
