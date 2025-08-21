<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { MenuIcon } from "lucide-vue-next";

interface Props {
  position?: "top-right" | "top-left" | "bottom-right" | "bottom-left";
  size?: "sm" | "md" | "lg";
}

withDefaults(defineProps<Props>(), {
  position: "top-right",
  size: "md",
});

const isOpen = ref(false);
const menuRef = ref<HTMLDivElement>();
const buttonRef = ref<HTMLButtonElement>();

// Close menu when clicking outside
const handleClickOutside = (event: Event) => {
  if (
    menuRef.value &&
    !menuRef.value.contains(event.target as Node) &&
    buttonRef.value &&
    !buttonRef.value.contains(event.target as Node)
  ) {
    isOpen.value = false;
  }
};

// Close menu on escape key
const handleEscape = (event: KeyboardEvent) => {
  if (event.key === "Escape") {
    isOpen.value = false;
  }
};

onMounted(() => {
  document.addEventListener("click", handleClickOutside);
  document.addEventListener("keydown", handleEscape);
});

onUnmounted(() => {
  document.removeEventListener("click", handleClickOutside);
  document.removeEventListener("keydown", handleEscape);
});

const toggleMenu = () => {
  isOpen.value = !isOpen.value;
};

const closeMenu = () => {
  isOpen.value = false;
};

// Position classes based on prop
const positionClasses = {
  "top-right": "top-0 right-0",
  "top-left": "top-0 left-0",
  "bottom-right": "bottom-0 right-0",
  "bottom-left": "bottom-0 left-0",
};

// Size classes for the button
const sizeClasses = {
  sm: "p-1",
  md: "p-2",
  lg: "p-3",
};
</script>

<template>
  <div class="relative">
    <!-- Hamburger Button -->
    <button ref="buttonRef" :class="[
      'flex items-center justify-center rounded-md bg-gray-100 hover:bg-gray-200 transition-colors duration-200',
      sizeClasses[size],
    ]" aria-label="Toggle menu" :aria-expanded="isOpen" @click="toggleMenu">
      <MenuIcon class="h-4 w-4 text-gray-700" />
    </button>

    <!-- Popup Menu -->
    <div v-if="isOpen" ref="menuRef" :class="[
      'absolute z-50 mt-2 min-w-54 rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5',
      positionClasses[position],
    ]" role="menu" aria-orientation="vertical" aria-labelledby="menu-button">
      <div class="py-1" role="none">
        <slot :close="closeMenu" />
      </div>
    </div>
  </div>
</template>
