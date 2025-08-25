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
    <div class="flex flex-row justify-between items-center w-full">
        <DButton @click="emit('click')" variant="primary" :icon-left="icon ?? undefined">
            {{ title }}
        </DButton>
        <span class="text-md text-gray-500">
            <slot />
        </span>
    </div>
</template>