<script setup lang="ts">
import { XIcon } from "lucide-vue-next";

interface Props {
    size?: "sm" | "md" | "lg";
    variant?: "default" | "transparent" | "danger";
    disabled?: boolean;
}

const {
    size = "md",
    variant = "default",
    disabled = false,
} = defineProps<Props>();

const emit = defineEmits<{
    click: [event: MouseEvent];
}>();

const sizeClasses = {
    sm: "p-1",
    md: "p-2",
    lg: "p-3",
};

const iconSizes = {
    sm: "w-3 h-3",
    md: "w-4 h-4",
    lg: "w-5 h-5",
};

const variantClasses = {
    default: "bg-white hover:bg-gray-100 border border-gray-200",
    transparent: "bg-transparent hover:bg-gray-100 border border-transparent",
    danger: "bg-red-50 hover:bg-red-100 border border-red-200 text-red-600",
};
</script>

<template>
    <button @click="emit('click', $event)" :disabled="disabled" :class="[
        'rounded-lg shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
        sizeClasses[size],
        variantClasses[variant],
        disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
    ]" aria-label="Close">
        <XIcon :class="iconSizes[size]" />
    </button>
</template>