<script setup lang="ts">
import { FileIcon, LogOutIcon, PanelLeftClose, PanelRightClose, HomeIcon, BookOpenIcon, ClipboardCheck, Lightbulb } from "lucide-vue-next"
import { useSessionStorage } from "@vueuse/core"


const route = useRoute()

const links = [
  {
    name: "Home",
    to: "/",
    icon: HomeIcon,
  },
  {
    name: "Tasks",
    to: "/tasks",
    icon: ClipboardCheck,
  },
  {
    name: "Courses",
    to: "/courses",
    icon: BookOpenIcon,
  },
]

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
]

const collapsed = useSessionStorage("collapsed", false)

const organisationName = ref("ITS")

const emit = defineEmits(["close"])

function close() {
  emit("close")
}
</script>

<template>
  <nav class="flex flex-col gap-0.5 p-2">
    <div class="group flex h-9 cursor-default items-center justify-between gap-2 rounded-md text-sm text-gray-700">
      <div v-show="!collapsed" class="flex items-center gap-2 px-2 py-2">
        <!-- <img src="/file_folder_color.svg" class="size-5" /> -->
        <div class="line-clamp-1 leading-[1em] font-medium">{{ organisationName }}</div>
      </div>
      <div
        class="hidden items-center rounded-md p-2 hover:bg-gray-200 sm:flex"
        :class="collapsed ? '' : 'opacity-0 group-hover:opacity-100'"
        @click="collapsed = !collapsed"
      >
        <PanelLeftClose v-show="!collapsed" class="size-4" />
        <PanelRightClose v-show="collapsed" class="size-4" />
      </div>
      <!-- <div class="block sm:hidden">
        <DButton :icon-left="XIcon" class="!px-1" @click="close" />
      </div> -->
    </div>
    <hr class="mt-1 mb-1.5 text-gray-200" />
    <NuxtLink
      v-for="link in links"
      class="flex cursor-default items-center gap-2 rounded-md px-2 py-1.5 text-sm text-gray-500 hover:bg-gray-200"
      :to="link.to"
      :class="route.path.startsWith(link.to) ? 'bg-gray-200 text-gray-700' : ''"
    >
      <div class="flex h-5 items-center justify-center">
        <component :is="link.icon" class="size-4" />
      </div>
      <div class="" v-show="!collapsed">{{ link.name }}</div>
    </NuxtLink>
  </nav>

  <nav class="flex flex-col gap-0.5 p-2">
    <NuxtLink
      v-for="link in footerLinks"
      class="flex cursor-default items-center gap-2 rounded-md px-2 py-1.5 text-sm text-gray-700 hover:bg-gray-200"
      :to="link.to"
      :class="route.path.startsWith(link.to) ? 'bg-gray-200' : ''"
    >
      <div class="flex h-5 items-center justify-center">
        <component :is="link.icon" class="size-4" />
      </div>
      <div v-show="!collapsed">{{ link.name }}</div>
    </NuxtLink>
  </nav>
</template>
