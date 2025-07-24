<script setup lang="ts">
import { ref, onMounted, computed } from "vue"
import DViewToggle from "~/components/d-view-toggle.vue";
import type { Task, Course, Skill } from '~/types/models';

// Define the form interface for creating/editing tasks
interface TaskFormData {
  name: string;
  type: "true_false" | "multiple_choice" | "free_text";
  question: string;
  courseId: string;
  skillId: string;
  options: string[];
  correctAnswer: string;
}

// Define view state
const isTeacherView = ref(true)
const tasks = ref<Task[]>([])
const loading = ref(true)
const coursesList = ref<Course[]>([])
const skillsList = ref<Skill[]>([])
const editingTask = ref<Task | null>(null)

// For student answers
const studentAnswers = ref<Record<string, string>>({})
const showResults = ref(false)
const submittedAnswers = ref<Record<string, string>>({})
const skillsUpdated = ref(false) // Track if skills have been updated for this submission

// For filtering tasks
const selectedCourseId = ref<string>("")
const selectedSkillId = ref<string>("")
const filterType = ref<"course" | "skill">("course")

// Computed property for filtered tasks
const filteredTasks = computed(() => {
  if (filterType.value === "course" && !selectedCourseId.value) {
    return tasks.value
  }
  
  if (filterType.value === "skill" && !selectedSkillId.value) {
    return tasks.value
  }
  
  return tasks.value.filter(task => {
    if (filterType.value === "course") {
      return task.courseId === selectedCourseId.value
    } else {
      return task.skillId === selectedSkillId.value
    }
  })
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
  filterType.value = filterType.value === "course" ? "skill" : "course"
  // Reset selections when switching
  selectedCourseId.value = ""
  selectedSkillId.value = ""
}

// Reset filters
function resetFilters() {
  selectedCourseId.value = ""
  selectedSkillId.value = ""
}

// Fetch tasks on page load
onMounted(async () => {
  loading.value = true
  try {
    const [tasksResponse, coursesResponse, skillsResponse] = await Promise.all([
      fetch("/api/tasks").then(res => res.json()),
      fetch("/api/courses").then(res => res.json()),
      fetch("/api/skills").then(res => res.json()),
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
    skillsList.value = skillsResponse
  } catch (error) {
    console.error("Error fetching data:", error)
  } finally {
    loading.value = false
  }
})

async function createTask(taskData: TaskFormData) {
  try {
    // Create the basic task
    const taskResponse = await fetch("/api/tasks", {
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
        skillId: taskData.skillId,
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
    const taskResponse = await fetch(`/api/tasks/${taskData.id}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: taskData.name,
        type: taskData.type,
        courseId: taskData.courseId,
        skillId: taskData.skillId,
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
    const response = await fetch(`/api/tasks/${id}`, {
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
      skillId: taskData.skillId
    }
    updateTask(updatedTask)
  } else {
    // Create the task
    createTask(taskData)
    
    // After successful creation, create a new task form with preserved course and skill
    // We do this by temporarily setting editingTask to a new object with preserved values
    // then immediately setting it back to null to trigger a form reset
    const preservedCourseId = taskData.courseId
    const preservedSkillId = taskData.skillId
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
        skillId: preservedSkillId,
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
  
  // Update skill progress if not already updated for this submission
  if (!skillsUpdated.value) {
    await updateSkillProgress()
    skillsUpdated.value = true
  }
}

function resetAnswers() {
  studentAnswers.value = {}
  submittedAnswers.value = {}
  showResults.value = false
  skillsUpdated.value = false
}

function isAnswerCorrect(taskId: string): boolean {
  const task = tasks.value.find(t => t.id === taskId)
  return !!task && (submittedAnswers.value[taskId] === task.correctAnswer)
}

// Function to update skill progress
async function updateSkillProgress() {
  // Create a map to track how many points to add to each skill
  const skillPoints: Record<string, number> = {}
  
  // Count correct answers for each skill
  filteredTasks.value.forEach(task => {
    if (isAnswerCorrect(task.id) && task.skillId) {
      const skillId = task.skillId as string
      if (!skillPoints[skillId]) {
        skillPoints[skillId] = 0
      }
      skillPoints[skillId]++
    }
  })
  
  // Update each skill with additional points
  for (const skillId in skillPoints) {
    try {
      // Find the skill in our local list
      const skill = skillsList.value.find(s => s.id === skillId)
      if (skill) {
        // Calculate new progress (ensure it doesn't exceed 100)
        const currentProgress = skill.progress || 0
        const points = skillPoints[skillId] || 0
        const newProgress = Math.min(100, currentProgress + points)
        
        // Update the skill via API
        const response = await fetch(`/api/skills/${skillId}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            ...skill,
            progress: newProgress
          }),
        })
        
        if (response.ok) {
          // Update local skill data
          const updatedSkill = await response.json()
          const index = skillsList.value.findIndex(s => s.id === skillId)
          if (index !== -1) {
            skillsList.value[index] = updatedSkill
          }
        }
      }
    } catch (error) {
      console.error(`Error updating skill ${skillId}:`, error)
    }
  }
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
        :skills="skillsList"
        :initial-task="editingTask ? {
          name: editingTask.name,
          type: editingTask.type,
          question: editingTask.question || '',
          courseId: editingTask.courseId,
          skillId: editingTask.skillId,
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
      <div v-if="!showResults">
        <div class="bg-white p-6 rounded-lg shadow mb-6">
          <h2 class="text-xl font-bold mb-4">Filter Tasks</h2>
          
          <div class="flex justify-between items-center mb-4">
            <div class="flex items-center space-x-2">
              <span class="text-gray-700">Filter by:</span>
              <DButton 
                @click="toggleFilterType" 
                variant="secondary"
                class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md shadow-sm"
                :class="filterType === 'course' ? 'bg-blue-100 text-blue-800 border-blue-300' : 'bg-white text-gray-700'"
              >
                Course
              </DButton>
              <DButton 
                @click="toggleFilterType" 
                variant="secondary"
                class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md shadow-sm"
                :class="filterType === 'skill' ? 'bg-blue-100 text-blue-800 border-blue-300' : 'bg-white text-gray-700'"
              >
                Skill
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
          
          <!-- Course Filter -->
          <div v-if="filterType === 'course'">
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
          
          <!-- Skill Filter -->
          <div v-else>
            <DLabel>Select Skill</DLabel>
            <DDropdown
              v-model="selectedSkillId"
              :options="[
                { value: '', label: 'All Skills' },
                ...skillsList.map(skill => ({ value: skill.id, label: skill.name }))
              ]"
              placeholder="All Skills"
              class="mt-1 w-full"
            />
          </div>
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
          
          <div class="flex justify-end space-x-4">
            <DButton 
              @click="submitAnswers" 
              class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Submit Answers
            </DButton>
          </div>
        </div>
      </div>
      
      <!-- Results View -->
      <div v-else class="space-y-6">
        <!-- Score Summary Card -->
        <div class="bg-white p-6 rounded-lg shadow">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold">Your Results</h2>
            <DButton 
              @click="resetAnswers" 
              class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Try Again
            </DButton>
          </div>
          
          <div class="flex items-center justify-center space-x-8 py-4">
            <div class="text-center">
              <div class="text-3xl font-bold text-blue-600">{{ correctAnswersCount }}/{{ totalAnsweredTasks }}</div>
              <div class="text-sm text-gray-500 mt-1">Correct Answers</div>
            </div>
            
            <div class="text-center">
              <div class="text-3xl font-bold text-blue-600">{{ scorePercentage }}%</div>
              <div class="text-sm text-gray-500 mt-1">Score</div>
            </div>
          </div>
          
          <div v-if="skillsUpdated" class="mt-4 text-center text-sm text-green-600">
            Your progress has been updated for the skills related to these tasks.
          </div>
        </div>
        
        <h3 class="text-lg font-semibold">Task Details</h3>
        
        <DTaskResult
          v-for="(task, index) in filteredTasks"
          :key="task.id"
          :task="task"
          :index="index"
          :user-answer="submittedAnswers[task.id] || ''"
          :is-correct="isAnswerCorrect(task.id)"
        />
      </div>
    </div>
  </div>
</template>