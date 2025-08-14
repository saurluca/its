<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useNotificationsStore } from "~/stores/notifications";

interface BaseItem {
  id?: string;
  name: string;
  description?: string;
  [key: string]: string | number | boolean | Date | string[] | null | undefined;
}

const props = defineProps<{
  item?: BaseItem;
  title: string;
  isEdit?: boolean;
}>();

const emit = defineEmits<{
  (e: "save", item: BaseItem): void;
  (e: "cancel"): void;
}>();

const formData = ref<BaseItem>({
  name: "",
  description: "",
});

const notifications = useNotificationsStore();

onMounted(() => {
  if (props.item) {
    formData.value = { ...props.item };
  }
});

function saveItem() {
  if (!formData.value.name) {
    notifications.warning("Name is required");
    return;
  }

  emit("save", formData.value);

  // Reset form if not editing
  if (!props.isEdit) {
    formData.value = {
      name: "",
      description: "",
    };
  }
}
</script>

<template>
  <div class="bg-white p-6 rounded-lg shadow">
    <h2 class="text-xl font-bold mb-4">{{ title }}</h2>

    <div class="flex items-center justify-between space-x-3">
      <div>
        <DInput v-model="formData.name" type="text" placeholder="Enter name" />
      </div>
      <div class="flex space-x-2">
        <DButton v-if="isEdit" @click="$emit('cancel')" variant="secondary">
          Cancel
        </DButton>
        <DButton @click="saveItem" variant="primary">
          {{ isEdit ? "Update" : "Create" }}
        </DButton>
      </div>
    </div>
  </div>
</template>
