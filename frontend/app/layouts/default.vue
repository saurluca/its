<script setup lang="ts">
import { ref } from "vue";
import { FlagIcon } from "lucide-vue-next";
import { useNotificationsStore } from "~/stores/notifications";

const showReportDialog = ref(false);
const reportMessage = ref("");
const submitting = ref(false);

const { $authFetch } = useAuthenticatedFetch();
const notifications = useNotificationsStore();

async function submitReport() {
  if (submitting.value) return;
  submitting.value = true;
  try {
    const url = window.location.href;
    await $authFetch("/reports", {
      method: "POST",
      body: {
        report_type: "generic",
        url,
        message: reportMessage.value || null,
      },
    });
    notifications.success("Thanks for the report!");
    showReportDialog.value = false;
    reportMessage.value = "";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="flex h-full max-h-screen flex-col sm:flex-row bg-gray-50">
    <DPageSidebar />
    <main class="flex-1 overflow-y-auto p-2 sm:p-4">
      <slot></slot>
    </main>
    <DSnackbar />

    <!-- Floating Report Button -->
    <button
      class="fixed bottom-4 right-4 z-50 rounded-full bg-red-600 text-white shadow-lg px-4 py-2 sm:px-5 sm:py-3 active:scale-95 focus:outline-none focus:ring-2 focus:ring-red-400 flex items-center gap-2"
      aria-label="Report a problem" @click="showReportDialog = true">
      <FlagIcon class="h-4 w-4" />
      <span class="hidden sm:inline">Report</span>
      <span class="sm:hidden">!</span>
    </button>

    <!-- Simple Modal Dialog -->
    <div v-if="showReportDialog" class="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      <div class="absolute inset-0 bg-black/40" @click="showReportDialog = false"></div>
      <div class="relative w-full sm:max-w-md bg-white rounded-t-2xl sm:rounded-2xl p-4 sm:p-6 shadow-xl">
        <h3 class="text-lg font-semibold mb-2">Report a problem</h3>
        <p class="text-sm text-gray-600 mb-3">Briefly describe the issue (bug or bad content).</p>
        <textarea v-model="reportMessage" rows="4"
          class="w-full rounded border border-gray-300 p-2 focus:ring-2 focus:ring-red-300"
          placeholder="What went wrong?" />
        <div class="mt-4 flex justify-end gap-2">
          <DButton variant="secondary" @click="showReportDialog = false">Cancel</DButton>
          <DButton :disabled="submitting" @click="submitReport">Submit</DButton>
        </div>
      </div>
    </div>
  </div>
</template>
