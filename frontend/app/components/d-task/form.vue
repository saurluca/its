<script setup lang="ts">
import { ref, watch, computed } from "vue";
import type { Course, NewTaskForm } from "~/types/models";

interface TaskForm extends Omit<NewTaskForm, "organisationId"> {
  type: "true_false" | "multiple_choice" | "free_text";
  question: string;
  courseId: string;
  options: string[];
  correctAnswer: string;
}

const props = defineProps<{
  initialTask?: TaskForm;
  courses: Course[];
}>();

const emit = defineEmits<{
  (e: "save", task: TaskForm): void;
}>();

const task = ref<TaskForm>({
  type: "true_false",
  question: "",
  courseId: "",
  options: ["True", "False"],
  correctAnswer: "True",
});

// Initialize with initial task if provided
watch(
  () => props.initialTask,
  (newValue) => {
    if (newValue) {
      task.value = { ...newValue };
    }
  },
  { immediate: true },
);

const taskTypes = [
  { value: "true_false", label: "True/False" },
  { value: "multiple_choice", label: "Multiple Choice" },
  { value: "free_text", label: "Free Text" },
];

function updateTaskType(value: string) {
  // Cast the string value to the appropriate type
  const type = value as "true_false" | "multiple_choice" | "free_text";
  task.value.type = type;

  // Reset options and correct answer based on task type
  if (type === "true_false") {
    task.value.options = ["True", "False"];
    task.value.correctAnswer = "True";
  } else if (type === "multiple_choice") {
    task.value.options = ["", "", ""]; // Three empty options by default
    task.value.correctAnswer = "";
  } else {
    task.value.options = [];
    task.value.correctAnswer = "";
  }
}

function addOption() {
  if (task.value.type === "multiple_choice") {
    task.value.options.push("");
  }
}

function removeOption(index: number) {
  if (task.value.type === "multiple_choice" && task.value.options.length > 2) {
    task.value.options.splice(index, 1);

    // Reset correct answer if it was removed
    if (task.value.correctAnswer === task.value.options[index]) {
      task.value.correctAnswer = "";
    }
  }
}

function saveTask() {
  if (!task.value.question || !task.value.courseId) {
    alert("Please fill in all required fields");
    return;
  }

  // Validate correct answer based on task type
  if (task.value.type === "multiple_choice" && !task.value.correctAnswer) {
    alert("Please select a correct answer");
    return;
  }
  console.log("task.value", task.value);
  emit("save", task.value);
}

// Format courses for dropdown
const courseOptions = computed(() => {
  return props.courses.map((course) => ({
    value: course.id,
    label: course.name,
  }));
});

// Format multiple choice options for correct answer dropdown
const correctAnswerOptions = computed(() => {
  if (task.value.type !== "multiple_choice") return [];

  return task.value.options
    .filter((option) => option.trim() !== "")
    .map((option) => ({
      value: option,
      label: option,
    }));
});
</script>

<template>
  <div class="bg-white p-6 rounded-lg shadow">
    <h2 class="text-xl font-bold mb-4">
      {{ initialTask ? "Edit Task" : "Create New Task" }}
    </h2>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Basic Task Info -->
      <div class="space-y-4">
        <div>
          <DLabel>Question</DLabel>
          <DInputArea
            v-model="task.question"
            rows="3"
            placeholder="Enter your question"
          />
        </div>

        <div>
          <DLabel>Task Type</DLabel>
          <div class="mt-1">
            <DButtonRadio
              v-model="task.type"
              name="taskType"
              :options="taskTypes"
              direction="horizontal"
              @update:model-value="updateTaskType"
            />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <DLabel>Course</DLabel>
            <DDropdown
              v-model="task.courseId"
              :options="courseOptions"
              placeholder="Select a course"
              class="mt-1"
            />
          </div>
        </div>
      </div>

      <!-- Answer Options Based on Task Type -->
      <div class="space-y-4">
        <!-- True/False Options -->
        <div v-if="task.type === 'true_false'">
          <DLabel>Correct Answer</DLabel>
          <DButtonRadio
            v-model="task.correctAnswer"
            name="correctAnswerTF"
            :options="['True', 'False']"
          />
        </div>

        <!-- Multiple Choice Options -->
        <div v-if="task.type === 'multiple_choice'" class="space-y-4">
          <div>
            <div class="flex justify-between items-center mb-2">
              <DLabel>Answer Options</DLabel>
              <DButton @click="addOption" variant="secondary">
                + Add Option
              </DButton>
            </div>

            <div
              v-for="(option, index) in task.options"
              :key="index"
              class="flex items-center space-x-2 mb-2"
            >
              <DInput
                v-model="task.options[index]"
                :placeholder="`Option ${index + 1}`"
              />
              <DButton
                @click="removeOption(index)"
                variant="danger"
                v-if="task.options.length > 2"
              >
                <span class="sr-only">Remove</span>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-5 w-5"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fill-rule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clip-rule="evenodd"
                  />
                </svg>
              </DButton>
            </div>
          </div>

          <div>
            <DLabel>Correct Answer</DLabel>
            <DDropdown
              v-model="task.correctAnswer"
              :options="correctAnswerOptions"
              placeholder="Select correct answer"
              class="mt-1"
            />
          </div>
        </div>

        <!-- Free Text Answer -->
        <div v-if="task.type === 'free_text'">
          <DLabel>Sample Correct Answer</DLabel>
          <DInputArea
            v-model="task.correctAnswer"
            rows="4"
            placeholder="Enter a sample correct answer"
          />
          <p class="mt-1 text-sm text-gray-500">
            This will be used as a reference for grading.
          </p>
        </div>
      </div>
    </div>

    <div class="mt-6">
      <DButton @click="saveTask" variant="primary">
        {{ initialTask ? "Update Task" : "Create Task" }}
      </DButton>
    </div>
  </div>
</template>
