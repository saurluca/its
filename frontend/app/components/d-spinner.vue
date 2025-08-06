<script setup lang="ts">
interface Props {
    size?: "sm" | "md" | "lg";
    color?: "gray" | "blue" | "white";
    variant?: "border" | "border-b";
}

const props = withDefaults(defineProps<Props>(), {
    size: "md",
    color: "gray",
    variant: "border",
});

const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-8 w-8",
    lg: "h-12 w-12",
};

const colorClasses = {
    gray: "border-gray-300 border-t-gray-600",
    blue: "border-blue-300 border-t-blue-600",
    white: "border-white border-t-gray-600",
};

const variantClasses = {
    border: "border-2 border-solid",
    "border-b": "border-b-2 border-gray-900",
};
</script>

<template>
    <div class="flex items-center justify-center">
        <div class="animate-spin rounded-full"
            :class="[sizeClasses[size], colorClasses[color], variantClasses[variant]]">
        </div>
    </div>
</template>