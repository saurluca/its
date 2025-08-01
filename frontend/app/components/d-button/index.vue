<script setup lang="ts">
import { LoaderCircleIcon } from "lucide-vue-next";
import { RouterLink } from "vue-router";

interface Props {
  variant?:
    | "primary"
    | "secondary"
    | "tertiary"
    | "danger"
    | "danger-light"
    | "transparent";
  iconLeft?: any;
  to?: any;
  type?: "submit" | "button" | any;
  loading?: boolean;
  textCenter?: boolean;
  disabled?: boolean;
}

const {
  variant = "primary",
  type = "button",
  loading = false,
  textCenter = false,
  disabled = false,
} = defineProps<Props>();
</script>

<template>
  <component
    :is="to ? RouterLink : 'button'"
    :type="type"
    :to="to"
    :disabled="disabled || loading"
    class="relative flex h-fit items-center gap-2 rounded-md px-2.5 py-1.5 text-sm ring-blue-600 ring-offset-2 outline-none focus:ring-2"
    :class="{
      'bg-gray-900 text-gray-50 hover:bg-gray-700':
        variant === 'primary' && !disabled && !loading,
      'bg-gray-100 text-gray-700 hover:bg-gray-200':
        variant === 'secondary' && !disabled && !loading,
      'bg-red-600 text-white hover:bg-red-700':
        variant === 'danger' && !disabled && !loading,
      'bg-red-100 text-red-800 hover:bg-red-200':
        variant === 'danger-light' && !disabled && !loading,
      'text-gray-500 hover:bg-gray-100':
        variant === 'transparent' && !disabled && !loading,
      'bg-blue-100 text-blue-700 hover:bg-blue-200':
        variant === 'tertiary' && !disabled && !loading,
      'bg-gray-300 text-gray-500 cursor-not-allowed': disabled || loading,
      'justify-center': textCenter,
    }"
  >
    <component v-if="iconLeft" :is="iconLeft" class="size-4" />
    <div v-if="$slots.default" class="inline" :class="{ 'opacity-0': loading }">
      <slot></slot>
    </div>
    <div
      v-if="loading"
      class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 transform"
    >
      <LoaderCircleIcon class="size-5 animate-spin" />
    </div>
  </component>
</template>
