<script setup lang="ts">
import { ref, onMounted } from 'vue';

interface Course {
  id: string;
  name: string;
  description?: string;
  organisationId?: string;
  createdAt?: string;
  updatedAt?: string;
}

// View state
const isTeacherView = ref(true);
const courses = ref<Course[]>([]);
const loading = ref(true);
const showForm = ref(false);
const editingCourse = ref<Course | null>(null);

// Load courses on component mount
onMounted(async () => {
  await fetchCourses();
});

async function fetchCourses() {
  loading.value = true;
  try {
    const response = await fetch('/api/courses');
    courses.value = await response.json();
  } catch (error) {
    console.error('Error fetching courses:', error);
    alert('Failed to load courses. Please try again.');
  } finally {
    loading.value = false;
  }
}

async function createCourse(courseData: Partial<Course>) {
  try {
    const response = await fetch('/api/courses', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(courseData),
    });
    
    if (!response.ok) {
      throw new Error('Failed to create course');
    }
    
    const newCourse = await response.json();
    courses.value.push(newCourse);
    showForm.value = false;
  } catch (error) {
    console.error('Error creating course:', error);
    alert('Failed to create course. Please try again.');
  }
}

async function updateCourse(courseData: Course) {
  try {
    const response = await fetch(`/api/courses/${courseData.id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(courseData),
    });
    
    if (!response.ok) {
      throw new Error('Failed to update course');
    }
    
    const updatedCourse = await response.json();
    const index = courses.value.findIndex(c => c.id === updatedCourse.id);
    if (index !== -1) {
      courses.value[index] = updatedCourse;
    }
    
    editingCourse.value = null;
  } catch (error) {
    console.error('Error updating course:', error);
    alert('Failed to update course. Please try again.');
  }
}

async function deleteCourse(id: string) {
  try {
    const response = await fetch(`/api/courses/${id}`, {
      method: 'DELETE',
    });
    
    if (!response.ok) {
      throw new Error('Failed to delete course');
    }
    
    courses.value = courses.value.filter(c => c.id !== id);
  } catch (error) {
    console.error('Error deleting course:', error);
    alert('Failed to delete course. Please try again.');
  }
}

function handleSave(courseData: Partial<Course>) {
  if (editingCourse.value) {
    updateCourse({ ...editingCourse.value, ...courseData });
  } else {
    createCourse(courseData);
  }
}

function editCourse(course: Course) {
  editingCourse.value = course;
  showForm.value = true;
}

function cancelEdit() {
  editingCourse.value = null;
  showForm.value = false;
}
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-8">
      <h1 class="text-3xl font-bold">Courses</h1>
      <DViewToggle v-model="isTeacherView" />
    </div>
    
    <div v-if="loading" class="py-20 text-center">
      <div class="text-xl">Loading courses...</div>
    </div>
    
    <div v-else class="space-y-8">
      <!-- Teacher View Form -->
      <div v-if="isTeacherView && !showForm" class="flex justify-end">
        <DButton 
          @click="showForm = true" 
          variant="primary"
        >
          Add New Course
        </DButton>
      </div>
      
      <DItemForm 
        v-if="isTeacherView && showForm"
        :title="editingCourse ? 'Edit Course' : 'Create New Course'"
        :item="editingCourse || undefined"
        :is-edit="!!editingCourse"
        @save="handleSave"
        @cancel="cancelEdit"
      />
      
      <!-- Courses List -->
      <div v-if="courses.length > 0" class="space-y-4">
        <DItemCard 
          v-for="course in courses" 
          :key="course.id" 
          :item="course" 
          :is-teacher-view="isTeacherView"
          @delete="deleteCourse"
          @edit="editCourse"
        />
      </div>
      
      <div v-else class="bg-white p-6 rounded-lg shadow text-center">
        <p class="text-gray-500">No courses have been created yet.</p>
      </div>
    </div>
  </div>
</template>