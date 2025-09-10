<script setup lang="ts">
import { XIcon } from "lucide-vue-next";
import { onClickOutside, onKeyDown } from "@vueuse/core";
import type { MaybeElement, MaybeElementRef } from "@vueuse/core";
import { ref, onMounted, nextTick, computed, type Component } from "vue";

interface Props {
  titel: string;
  confirmText?: string;
  wide?: boolean;
  confirmIcon?: Component;
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  confirmText: "Save",
  wide: false,
  confirmIcon: undefined,
  disabled: false,
});

const emit = defineEmits(["close", "confirm"]);

const dialog = ref<MaybeElement | null>(null);
const cancelButton = ref<HTMLElement | null>(null);

function close() {
  emit("close");
}

function save() {
  emit("confirm");
}

onMounted(() => {
  // Prefer focusing an input/textarea/contenteditable element inside the modal, if present.
  nextTick(() => {
    const root = (dialog.value as HTMLElement | null) ?? undefined;
    const autoFocusTarget = root?.querySelector(
      "[data-autofocus], input, textarea, [contenteditable=\"true\"]"
    ) as HTMLElement | null | undefined;

    if (autoFocusTarget && typeof autoFocusTarget.focus === "function") {
      autoFocusTarget.focus();
    } else {
      document.getElementById("cancel")?.focus();
    }
  });
});

onClickOutside(dialog as MaybeElementRef, () => emit("close"));
onKeyDown("Escape", () => emit("close"));

const confirmVariant = computed(() => {
  const text = props.confirmText?.toLowerCase() ?? "";
  const title = props.titel?.toLowerCase() ?? "";
  const destructiveKeywords = ["delete", "remove", "destroy"];
  return destructiveKeywords.some((k) => text.includes(k) || title.includes(k))
    ? "danger"
    : "primary";
});
</script>

<template>
  <Teleport to="body">
    <div>
      <div class="fixed inset-0 z-50 bg-black/10"></div>
      <div class="fixed inset-0 z-50 overflow-y-auto">
        <div class="flex min-h-full items-center justify-center p-4 text-center">
          <div class="max-h-full w-full max-w-md">
            <div ref="dialog" class="relative rounded-md bg-white shadow">
              <div class="flex items-center justify-between rounded-t border-b border-gray-200 px-4 py-2.5">
                <h3 class="text-base font-medium text-gray-900">{{ props.titel }}</h3>
                <DButton :icon-left="XIcon" variant="secondary" class="!px-1" @click="close"></DButton>
              </div>
              <div class="items-start space-y-6 overflow-auto text-left">
                <slot></slot>
              </div>
              <div class="flex justify-end space-x-2 rounded-b border-t border-gray-200 p-4">
                <DButton ref="cancelButton" id="cancel" variant="secondary" @click="close">Cancel</DButton>
                <DButton :icon-left="props.confirmIcon" :variant="confirmVariant" :disabled="props.disabled"
                  @click="save">{{
                    props.confirmText
                  }}</DButton>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
