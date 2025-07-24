<script setup lang="ts">
import { ref, onMounted } from 'vue';

interface Skill {
  id: string;
  name: string;
  description?: string;
  progress?: number;
  organisationId?: string;
  createdAt?: string;
  updatedAt?: string;
}

// View state
const isTeacherView = ref(true);
const skills = ref<Skill[]>([]);
const loading = ref(true);
const showForm = ref(false);
const editingSkill = ref<Skill | null>(null);

// Load skills on component mount
onMounted(async () => {
  await fetchSkills();
});

async function fetchSkills() {
  loading.value = true;
  try {
    const response = await fetch('/api/skills');
    skills.value = await response.json();
  } catch (error) {
    console.error('Error fetching skills:', error);
    alert('Failed to load skills. Please try again.');
  } finally {
    loading.value = false;
  }
}

async function createSkill(skillData: Partial<Skill>) {
  try {
    const response = await fetch('/api/skills', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(skillData),
    });
    
    if (!response.ok) {
      throw new Error('Failed to create skill');
    }
    
    const newSkill = await response.json();
    skills.value.push(newSkill);
    showForm.value = false;
  } catch (error) {
    console.error('Error creating skill:', error);
    alert('Failed to create skill. Please try again.');
  }
}

async function updateSkill(skillData: Skill) {
  try {
    const response = await fetch(`/api/skills/${skillData.id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(skillData),
    });
    
    if (!response.ok) {
      throw new Error('Failed to update skill');
    }
    
    const updatedSkill = await response.json();
    const index = skills.value.findIndex(s => s.id === updatedSkill.id);
    if (index !== -1) {
      skills.value[index] = updatedSkill;
    }
    
    editingSkill.value = null;
  } catch (error) {
    console.error('Error updating skill:', error);
    alert('Failed to update skill. Please try again.');
  }
}

async function deleteSkill(id: string) {
  try {
    const response = await fetch(`/api/skills/${id}`, {
      method: 'DELETE',
    });
    
    if (!response.ok) {
      throw new Error('Failed to delete skill');
    }
    
    skills.value = skills.value.filter(s => s.id !== id);
  } catch (error) {
    console.error('Error deleting skill:', error);
    alert('Failed to delete skill. Please try again.');
  }
}

function handleSave(skillData: Partial<Skill>) {
  if (editingSkill.value) {
    updateSkill({ ...editingSkill.value, ...skillData });
  } else {
    createSkill(skillData);
  }
}

function editSkill(skill: Skill) {
  editingSkill.value = skill;
  showForm.value = true;
}

function cancelEdit() {
  editingSkill.value = null;
  showForm.value = false;
}
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-8">
      <h1 class="text-3xl font-bold">Skills</h1>
      <DViewToggle v-model="isTeacherView" />
    </div>
    
    <div v-if="loading" class="py-20 text-center">
      <div class="text-xl">Loading skills...</div>
    </div>
    
    <div v-else class="space-y-8">
      <!-- Teacher View Form -->
      <div v-if="isTeacherView && !showForm" class="flex justify-end">
        <DButton 
          @click="showForm = true" 
          class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Add New Skill
        </DButton>
      </div>
      
      <DItemForm 
        v-if="isTeacherView && showForm"
        :title="editingSkill ? 'Edit Skill' : 'Create New Skill'"
        :item="editingSkill || undefined"
        :is-edit="!!editingSkill"
        @save="handleSave"
        @cancel="cancelEdit"
      >
        <template #extra-fields>
          <div v-if="editingSkill">
            <DLabel>Progress</DLabel>
            <DInput 
              v-model.number="editingSkill.progress" 
              type="number" 
              min="0" 
              max="100"
              class="mt-1 p-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="Enter progress (0-100)"
            />
          </div>
        </template>
      </DItemForm>
      
      <!-- Skills List -->
      <div v-if="skills.length > 0" class="space-y-4">
        <DItemCard 
          v-for="skill in skills" 
          :key="skill.id" 
          :item="skill" 
          :is-teacher-view="isTeacherView"
          @delete="deleteSkill"
          @edit="editSkill"
        >
          <div v-if="skill.progress !== undefined" class="mt-3">
            <div class="flex justify-between items-center text-sm text-gray-500">
              <span>Progress</span>
              <span>{{ skill.progress }}%</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2.5 mt-1">
              <div 
                class="bg-blue-600 h-2.5 rounded-full" 
                :style="{ width: `${skill.progress}%` }"
              ></div>
            </div>
          </div>
        </DItemCard>
      </div>
      
      <div v-else class="bg-white p-6 rounded-lg shadow text-center">
        <p class="text-gray-500">No skills have been created yet.</p>
      </div>
    </div>
  </div>
</template>