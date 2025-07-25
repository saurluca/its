<script setup lang="ts">
import { ref, onMounted, computed } from "vue"
import DViewToggle from "~/components/d-view-toggle.vue";
import type { Task, Course } from '~/types/models';
const runtimeConfig = useRuntimeConfig();
const apiUrl = runtimeConfig.public.apiBase;

// Define the form interface for creating/editing tasks
interface TaskFormData {
  name: string;
  type: "true_false" | "multiple_choice" | "free_text";
  question: string;
  courseId: string;
  options: string[];
  correctAnswer: string;
}

// Define view state
const isTeacherView = ref(true)
const tasks = ref<Task[]>([])
const loading = ref(true)
const coursesList = ref<Course[]>([])
const editingTask = ref<Task | null>(null)

// For student answers
const studentAnswers = ref<Record<string, string>>({})
const showResults = ref(false)
const submittedAnswers = ref<Record<string, string>>({})

// For filtering tasks
const selectedCourseId = ref<string>("")
const filterType = ref<"course">("course")

// Computed property for filtered tasks
const filteredTasks = computed(() => {
  if (!selectedCourseId.value) {
    return tasks.value
  }
  return tasks.value.filter(task => task.courseId === selectedCourseId.value)
})

// Computed properties for score calculation
const correctAnswersCount = computed(() => {
  return filteredTasks.value.filter(task => isAnswerCorrect(task.id)).length
})

const totalAnsweredTasks = computed(() => {
  return Object.keys(submittedAnswers.value).length
})

const scorePercentage = computed(() => {
  if (totalAnsweredTasks.value === 0) return 0
  return Math.round((correctAnswersCount.value / totalAnsweredTasks.value) * 100)
})

// Toggle filter type
function toggleFilterType() {
  // Only course filter remains
  selectedCourseId.value = ""
}

// Reset filters
function resetFilters() {
  selectedCourseId.value = ""
}

// Fetch tasks on page load
onMounted(async () => {
  loading.value = true
  try {
    const [tasksResponse, coursesResponse] = await Promise.all([
      fetch(`${apiUrl}/tasks`).then(res => res.json()),
      fetch(`${apiUrl}/courses`).then(res => res.json()),
    ])
    
    tasks.value = tasksResponse.map((task: Task) => ({
      ...task,
      // Only set default values if they don't exist in the response
      question: task.question || task.name,
      options: task.options || (
        task.type === "true_false" ? ["True", "False"] : []
      ),
      correctAnswer: task.correctAnswer || ""
    }))
    
    coursesList.value = coursesResponse
  } catch (error) {
    console.error("Error fetching data:", error)
  } finally {
    loading.value = false
  }
})

async function createTask(taskData: TaskFormData) {
  try {
    // Create the basic task
    const taskResponse = await fetch(`${apiUrl}/tasks`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: taskData.name,
        type: taskData.type,
        question: taskData.question,
        options: taskData.options,
        correctAnswer: taskData.correctAnswer,
        courseId: taskData.courseId,
      }),
    })
    
    if (!taskResponse.ok) {
      throw new Error("Failed to create task")
    }
    
    const createdTask = await taskResponse.json() as Task
    
    // Add task details - in a real app, you would have a separate API for this
    // For now, we'll just add it to our local array
    tasks.value.push({
      ...createdTask,
      question: taskData.question,
      options: taskData.options,
      correctAnswer: taskData.correctAnswer
    })
    
  } catch (error) {
    console.error("Error creating task:", error)
    alert("Failed to create task. Please try again.")
  }
}

async function updateTask(taskData: Task) {
  try {
    // Update the basic task
    const taskResponse = await fetch(`${apiUrl}/tasks/${taskData.id}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: taskData.name,
        type: taskData.type,
        courseId: taskData.courseId,
      }),
    })
    
    if (!taskResponse.ok) {
      throw new Error("Failed to update task")
    }
    
    const index = tasks.value.findIndex(t => t.id === taskData.id)
    if (index !== -1) {
      tasks.value[index] = {
        ...taskData,
        updatedAt: new Date()
      }
    }
    
    editingTask.value = null
    
  } catch (error) {
    console.error("Error updating task:", error)
    alert("Failed to update task. Please try again.")
  }
}

async function deleteTask(id: string) {
  try {
    const response = await fetch(`${apiUrl}/tasks/${id}`, {
      method: "DELETE",
    })
    
    if (!response.ok) {
      throw new Error("Failed to delete task")
    }
    
    tasks.value = tasks.value.filter(t => t.id !== id)
  } catch (error) {
    console.error("Error deleting task:", error)
    alert("Failed to delete task. Please try again.")
  }
}

function handleSaveTask(taskData: TaskFormData) {
  if (editingTask.value) {
    const updatedTask = {
      ...editingTask.value,
      name: taskData.name,
      type: taskData.type,
      question: taskData.question,
      options: taskData.options,
      correctAnswer: taskData.correctAnswer,
      courseId: taskData.courseId,
    }
    updateTask(updatedTask)
  } else {
    // Create the task
    createTask(taskData)
    
    // After successful creation, create a new task form with preserved course
    // We do this by temporarily setting editingTask to a new object with preserved values
    // then immediately setting it back to null to trigger a form reset
    const preservedCourseId = taskData.courseId
    const preservedType = taskData.type
    
    // Use setTimeout to ensure this happens after the current execution context
    setTimeout(() => {
      // First set a temporary task with preserved values
      editingTask.value = {
        id: "",
        name: "",
        type: preservedType,
        question: "",
        options: preservedType === "true_false" ? ["True", "False"] : 
                 preservedType === "multiple_choice" ? ["", "", ""] : [],
        correctAnswer: "",
        courseId: preservedCourseId,
        organisationId: "",
        createdAt: new Date(),
        updatedAt: new Date(),
        deletedAt: null
      } as Task
      
      // Then immediately set it back to null to trigger the form reset
      setTimeout(() => {
        editingTask.value = null
      }, 10)
    }, 0)
  }
}

function handleEditTask(task: Task) {
  editingTask.value = { ...task }
}

// Functions for student view
async function submitAnswers() {
  submittedAnswers.value = { ...studentAnswers.value }
  showResults.value = true
  
}

function resetAnswers() {
  studentAnswers.value = {}
  submittedAnswers.value = {}
  showResults.value = false
}

function isAnswerCorrect(taskId: string): boolean {
  const task = tasks.value.find(t => t.id === taskId)
  return !!task && (submittedAnswers.value[taskId] === task.correctAnswer)
}

</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-8">
      <h1 class="text-3xl font-bold">Tasks</h1>
      
      <DViewToggle v-model="isTeacherView" />
    </div>
    
    <div v-if="loading" class="py-20 text-center">
      <div class="text-xl">Loading tasks...</div>
    </div>
    
    <!-- Teacher View -->
    <div v-else-if="isTeacherView" class="space-y-8">
      <!-- Task Creation Form -->
      <DTaskForm
        :courses="coursesList"
        :initial-task="editingTask ? {
          name: editingTask.name,
          type: editingTask.type,
          question: editingTask.question || '',
          courseId: editingTask.courseId,
          options: editingTask.options || [],
          correctAnswer: editingTask.correctAnswer || ''
        } : undefined"
        @save="handleSaveTask"
      />
      
      <!-- Existing Tasks -->
      <div v-if="tasks.length > 0" class="space-y-4">
        <h2 class="text-xl font-bold">Existing Tasks</h2>
        
        <DTaskCard
          v-for="task in tasks"
          :key="task.id"
          :task="task"
          :is-teacher-view="true"
          @delete="deleteTask"
          @edit="handleEditTask"
        />
      </div>
      
      <div v-else class="bg-white p-6 rounded-lg shadow text-center">
        <p class="text-gray-500">No tasks have been created yet.</p>
      </div>
    </div>
    
    <!-- Student View -->
    <div v-else class="space-y-8">
      <div>
        <div class="bg-white p-6 rounded-lg shadow mb-6">
          <h2 class="text-xl font-bold mb-4">Filter Tasks</h2>
          
          <div class="flex justify-between items-center mb-4">
            <div class="flex items-center space-x-2">
              <span class="text-gray-700">Filter by:</span>
              <DButton 
                @click="toggleFilterType" 
                variant="secondary"
                class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md shadow-sm bg-blue-100 text-blue-800 border-blue-300"
              >
                Course
              </DButton>
            </div>
            <DButton 
              @click="resetFilters" 
              variant="secondary"
              class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50"
            >
              Reset
            </DButton>
          </div>
          
          <DLabel>Select Course</DLabel>
          <DDropdown
            v-model="selectedCourseId"
            :options="[
              { value: '', label: 'All Courses' },
              ...coursesList.map(course => ({ value: course.id, label: course.name }))
            ]"
            placeholder="All Courses"
            class="mt-1 w-full"
          />
        </div>

        <h2 class="text-xl font-bold mb-4">Answer Tasks</h2>
        
        <div v-if="filteredTasks.length === 0" class="bg-white p-6 rounded-lg shadow text-center">
          <p class="text-gray-500">No tasks available for the selected filters.</p>
        </div>
        
        <div v-else class="space-y-6">
          <DTaskAnswer
            v-for="(task, index) in filteredTasks"
            :key="task.id"
            :task="task"
            :index="index"
            :model-value="studentAnswers[task.id] || ''"
            @update:model-value="(val) => studentAnswers[task.id] = val"
          />
          
        </div>
      </div>
    </div>
  </div>
</template>