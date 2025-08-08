<script setup lang="ts">
import {
    CheckCircle2Icon,
    AlertTriangleIcon,
    CircleAlertIcon,
    XIcon,
} from "lucide-vue-next";
import { storeToRefs } from "pinia";
import { useNotificationsStore } from "~/stores/notifications";

const notifications = useNotificationsStore();
const { items } = storeToRefs(notifications);

function close(id: number) {
    notifications.remove(id);
}
</script>

<template>
    <Teleport to="body">
        <div
            class="pointer-events-none fixed right-4 top-4 z-50 flex w-[calc(100%-2rem)] max-w-sm flex-col gap-2 sm:w-auto">
            <TransitionGroup name="snackbar" tag="div">
                <div v-for="n in items" :key="n.id"
                    class="pointer-events-auto flex items-start gap-3 rounded-md border p-3 shadow-md backdrop-blur-sm"
                    :class="{
                        'border-green-300 bg-green-50/95 text-green-800': n.kind === 'success',
                        'border-red-300 bg-red-50/95 text-red-800': n.kind === 'error',
                        'border-amber-300 bg-amber-50/95 text-amber-800': n.kind === 'warning',
                    }">
                    <component
                        :is="n.kind === 'success' ? CheckCircle2Icon : n.kind === 'warning' ? AlertTriangleIcon : CircleAlertIcon"
                        class="mt-0.5 size-5 flex-shrink-0" :class="{
                            'text-green-600': n.kind === 'success',
                            'text-red-600': n.kind === 'error',
                            'text-amber-600': n.kind === 'warning',
                        }" />

                    <div class="min-w-0 flex-1 text-sm">
                        <p class="leading-5">{{ n.message }}</p>
                    </div>

                    <button class="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded hover:bg-black/5"
                        type="button" aria-label="Close notification" @click="close(n.id)">
                        <XIcon class="size-4 opacity-65" />
                    </button>
                </div>
            </TransitionGroup>
        </div>
    </Teleport>
</template>

<style scoped>
.snackbar-enter-active,
.snackbar-leave-active {
    transition: all 0.18s ease, transform 0.18s ease;
}

.snackbar-enter-from,
.snackbar-leave-to {
    opacity: 0;
    transform: translateY(-6px) translateX(6px) scale(0.98);
}
</style>
