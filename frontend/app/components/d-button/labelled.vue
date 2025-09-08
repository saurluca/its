<script setup lang="ts">
import type { Component } from 'vue';

defineProps<{
    title: string;
    icon?: Component;
}>();

const emit = defineEmits<{
    (e: 'click'): void;
}>();
</script>

<template>
    <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center w-full gap-2 sm:gap-0 ">
        <DButton @click="emit('click')" variant="primary" :icon-left="icon ?? undefined">
            {{ title }}
        </DButton>
        <span class="text-md text-gray-500">
            <slot />
        </span>
    </div>
</template>