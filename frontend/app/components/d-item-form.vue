<script setup lang="ts">
import { ref, onMounted } from 'vue';

interface BaseItem {
  id?: string;
  name: string;
  description?: string;
  [key: string]: any;
}

const props = defineProps<{
  item?: BaseItem;
  title: string;
  isEdit?: boolean;
}>();

const emit = defineEmits<{
  (e: 'save', item: BaseItem): void;
  (e: 'cancel'): void;
}>();

const formData = ref<BaseItem>({
  name: '',
  description: ''
});

onMounted(() => {
  if (props.item) {
    formData.value = { ...props.item };
  }
});

function saveItem() {
  if (!formData.value.name) {
    alert('Name is required');
    return;
  }
  
  emit('save', formData.value);
  
  // Reset form if not editing
  if (!props.isEdit) {
    formData.value = {
      name: '',
      description: ''
    };
  }
}
</script>

<template>
  <div class="bg-white p-6 rounded-lg shadow">
    <h2 class="text-xl font-bold mb-4">{{ title }}</h2>
    
    <div class="space-y-4">
      <div>
        <DLabel>Name</DLabel>
        <DInput 
          v-model="formData.name" 
          type="text" 
          placeholder="Enter name"
        />
      </div>
      
      <div>
        <DLabel>Description</DLabel>
        <DInputArea 
          v-model="formData.description" 
          rows="3"
          placeholder="Enter description (optional)"
        />
      </div>
      
      <slot name="extra-fields"></slot>
      
      <div class="flex justify-end space-x-3 mt-6">
        <DButton 
          v-if="isEdit"
          @click="$emit('cancel')" 
          variant="secondary"
        >
          Cancel
        </DButton>
        <DButton 
          @click="saveItem" 
          variant="primary"
        >
          {{ isEdit ? 'Update' : 'Create' }}
        </DButton>
      </div>
    </div>
  </div>
</template>