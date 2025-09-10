<script setup lang="ts">
import {
  LogOutIcon,
  PanelLeftClose,
  PanelRightClose,
  BookOpenIcon,
  HomeIcon,
  // User
} from "lucide-vue-next";
import { useSessionStorage } from "@vueuse/core";
import type { Repository } from "~/types/models";

const route = useRoute();
const { $authFetch } = useAuthenticatedFetch();

const emit = defineEmits<{ (e: 'close'): void }>();

const links = [
  {
    name: "Overview",
    to: "/",
    icon: HomeIcon,
  },
  // {
  //   name: "Tasks",
  //   to: "/tasks",
  //   icon: ClipboardList,
  // },
  // {
  //   name: "User",
  //   to: "/user",
  //   icon: User,
  // },
  // {
  //   name: "Documents",
  //   to: "/documents",
  //   icon: FileIcon,
  // },
  // {
  //   name: "Study",
  //   to: "/study",
  //   icon: Lightbulb,
  // },
];

const footerLinks = [
  // {
  //   name: "Einstellungen",
  //   to: "/settings",
  //   icon: Settings2Icon
  // },
  {
    name: "Logout",
    to: "/logout",
    icon: LogOutIcon,
  },
];

const collapsed = useSessionStorage("collapsed", false);

const organisationName = ref("ITS");

// Repositories list under main navigation
const repositories = ref<Repository[]>([]);
const loadingRepos = ref(true);

const onRepositoriesUpdated = () => {
  // Refresh repositories when notified by other parts of the app
  fetchRepositories();
};

onMounted(async () => {
  await fetchRepositories();
  if (typeof window !== "undefined") {
    window.addEventListener("repositories:updated", onRepositoriesUpdated);
  }
});

onBeforeUnmount(() => {
  if (typeof window !== "undefined") {
    window.removeEventListener("repositories:updated", onRepositoriesUpdated);
  }
});

async function fetchRepositories() {
  loadingRepos.value = true;
  try {
    const response = await $authFetch("/repositories") as { repositories?: Repository[] } | Repository[];
    repositories.value = ("repositories" in response ? response.repositories : response) as Repository[];
  } catch (error) {
    // Non-blocking: show nothing if it fails
    console.error("Sidebar repositories load failed", error);
  } finally {
    loadingRepos.value = false;
  }
}

function repositoryIsActive(id: string) {
  return route.path === "/repository" && String(route.query.repositoryId || "") === id;
}

</script>

<template>
  <nav class="flex flex-col gap-0.5 p-2">
    <div class="group flex h-9 cursor-default items-center justify-between gap-2 rounded-md text-sm text-gray-700">
      <div v-show="!collapsed" class="flex items-center gap-2 px-2 py-2">
        <!-- <img src="/file_folder_color.svg" class="size-5" /> -->
        <div class="line-clamp-1 leading-[1em] font-medium">
          {{ organisationName }}
        </div>
      </div>
      <div class="hidden items-center rounded-md p-2 hover:bg-gray-200 sm:flex"
        :class="collapsed ? '' : 'opacity-0 group-hover:opacity-100'" @click="collapsed = !collapsed">
        <PanelLeftClose v-show="!collapsed" class="size-4" />
        <PanelRightClose v-show="collapsed" class="size-4" />
      </div>
      <!-- <div class="block sm:hidden">
        <DButton :icon-left="XIcon" class="!px-1" @click="close" />
      </div> -->
    </div>
    <hr class="mt-1 mb-1.5 text-gray-200" />
    <NuxtLink v-for="link in links" :key="link.to"
      class="flex cursor-default items-center gap-2 rounded-md px-2 py-1.5 text-sm text-gray-500 hover:bg-gray-200"
      :to="link.to" @click="emit('close')"
      :class="(link.to === '/' ? route.path === '/' : route.path.startsWith(link.to)) ? 'bg-gray-200 text-gray-700' : ''">
      <div class="flex h-5 items-center justify-center">
        <component :is="link.icon" class="size-4" />
      </div>
      <div class="" v-show="!collapsed">{{ link.name }}</div>
    </NuxtLink>

    <!-- Repositories list -->
    <div class="mt-1.5 mb-0.5 text-xs text-gray-400 px-2" v-show="!collapsed">Repositories</div>
    <div v-if="loadingRepos" class="px-2 py-1.5 text-xs text-gray-400">Loading…</div>
    <NuxtLink v-else v-for="repo in repositories" :key="repo.id"
      class="flex cursor-default items-center gap-2 rounded-md px-2 py-1.5 text-sm text-gray-500 hover:bg-gray-200"
      :to="`/repository?repositoryId=${repo.id}`" @click="emit('close')"
      :class="repositoryIsActive(repo.id) ? 'bg-gray-200 text-gray-700' : ''">
      <div class="flex h-5 items-center justify-center">
        <BookOpenIcon class="size-4" />
      </div>
      <div class="truncate" v-show="!collapsed">{{ repo.name }}</div>
    </NuxtLink>
  </nav>

  <nav class="flex flex-col gap-0.5 p-2">
    <NuxtLink v-for="link in footerLinks" :key="link.to"
      class="flex cursor-default items-center gap-2 rounded-md px-2 py-1.5 text-sm text-gray-700 hover:bg-gray-200"
      :to="link.to" :class="route.path.startsWith(link.to) ? 'bg-gray-200' : ''" @click="emit('close')">
      <div class="flex h-5 items-center justify-center">
        <component :is="link.icon" class="size-4" />
      </div>
      <div v-show="!collapsed">{{ link.name }}</div>
    </NuxtLink>
  </nav>
</template>
