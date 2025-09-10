<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
    current: number;
    total: number;
}>();

const safeTotal = computed(() => Math.max(0, props.total || 0));
const safeCurrent = computed(() => {
    const total = safeTotal.value;
    const current = Math.max(0, props.current || 0);
    return total === 0 ? 0 : Math.min(current, total);
});

const percentage = computed(() => {
    const total = safeTotal.value;
    if (total === 0) return 0;
    return Math.round((safeCurrent.value / total) * 100);
});
</script>

<template>
    <div class="w-full">
        <div class="flex items-center justify-between mb-1">
            <div class="text-sm font-medium text-gray-700">Progress</div>
            <div class="text-xs text-gray-600">{{ safeCurrent }} / {{ safeTotal }} ({{ percentage }}%)</div>
        </div>
        <div class="w-full bg-gray-200 rounded h-2.5 overflow-hidden" role="progressbar" :aria-valuenow="percentage"
            aria-valuemin="0" :aria-valuemax="100">
            <div class="h-full bg-green-600 transition-all duration-300" :style="{ width: `${percentage}%` }"></div>
        </div>
    </div>

</template>
