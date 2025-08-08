import { defineStore } from "pinia";

export type NotificationKind = "success" | "error" | "warning";

export interface NotificationItem {
  id: number;
  kind: NotificationKind;
  message: string;
  durationMs: number;
}

interface NotificationsState {
  items: NotificationItem[];
}

export const useNotificationsStore = defineStore("notifications", {
  state: (): NotificationsState => ({
    items: [],
  }),

  actions: {
    notify(
      message: string,
      kind: NotificationKind = "success",
      durationMs = 4000
    ): number {
      const id = Date.now() + Math.floor(Math.random() * 1000);
      const item: NotificationItem = { id, kind, message, durationMs };
      this.items.unshift(item);

      // Auto-dismiss
      if (durationMs > 0) {
        setTimeout(() => this.remove(id), durationMs);
      }

      return id;
    },

    success(message: string, durationMs?: number) {
      return this.notify(message, "success", durationMs ?? 4000);
    },

    error(message: string, durationMs?: number) {
      return this.notify(message, "error", durationMs ?? 6000);
    },

    warning(message: string, durationMs?: number) {
      return this.notify(message, "warning", durationMs ?? 5000);
    },

    remove(id: number) {
      this.items = this.items.filter((n) => n.id !== id);
    },

    clear() {
      this.items = [];
    },
  },
});
