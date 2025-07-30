<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import type { Task } from "~/types/models";

const route = useRoute();
const pageState = ref<"studying" | "finished">("studying");
const fileId = ref("");
const tasks = ref<Task[]>([]);
const currentTaskIndex = ref(0);
const currentAnswer = ref("");
const showEvaluation = ref(false);
const isCorrect = ref<boolean | null>(null);
const score = ref(0);
const loading = ref(false);
const error = ref<string | null>(null);
const feedback = ref<string | null>(null);
const router = useRouter();
const runtimeConfig = useRuntimeConfig();
const apiUrl = runtimeConfig.public.apiBase;

const currentTask = computed(() => tasks.value[currentTaskIndex.value]);

onMounted(() => {
  // Check if documentId is provided in URL parameters
  const documentId = route.query.documentId as string;
  if (documentId) {
    fileId.value = documentId;
    startStudy();
  }
});

async function startStudy() {
  if (!fileId.value) {
    error.value = "Please enter a Document ID.";
    return;
  }
  loading.value = true;
  error.value = null;

  try {
    const { data: responseData, error: fetchError } = await useFetch<{
      tasks: Task[];
    }>(`${apiUrl}/tasks/document/${fileId.value}`);

    if (fetchError.value) {
      throw new Error(
        fetchError.value.data?.message || "Failed to load tasks.",
      );
    }

    const fetchedTasks = responseData.value?.tasks;

    if (fetchedTasks && fetchedTasks.length > 0) {
      tasks.value = fetchedTasks;
      console.log("Loaded tasks:", fetchedTasks.length, fetchedTasks);
      pageState.value = "studying";
    } else {
      error.value =
        "No tasks found for this document, or the document is empty.";
    }
  } catch (e: any) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}

async function evaluateAnswer() {
  if (currentAnswer.value === null || currentAnswer.value === "") {
    error.value = "Please enter an answer.";
    return;
  }

  feedback.value = "Evaluating...";

  const correct = currentAnswer.value === currentTask.value.correct_answer;
  isCorrect.value = correct;

  showEvaluation.value = true;

  if (correct) {
    score.value++;
  } else {
    const { data: responseData, error: fetchError } = await useFetch<{
      feedback: string;
    }>(`${apiUrl}/tasks/evaluate_answer/${currentTask.value.id}`, {
      method: "POST",
      body: {
        student_answer: currentAnswer.value,
      },
    });

    if (fetchError.value) {
      error.value =
        fetchError.value.data?.message || "Failed to evaluate answer.";
      return;
    }
    feedback.value = responseData.value?.feedback;
  }
}

function nextQuestion() {
  console.log(
    "Next question called. Current index:",
    currentTaskIndex.value,
    "Total tasks:",
    tasks.value.length,
  );
  if (currentTaskIndex.value < tasks.value.length - 1) {
    currentTaskIndex.value++;
    currentAnswer.value = "";
    isCorrect.value = null;
    showEvaluation.value = false;
    console.log("Moving to question:", currentTaskIndex.value + 1);
  } else {
    console.log("Study session finished");
    pageState.value = "finished";
  }
}

function restart() {
  pageState.value = "studying";
  fileId.value = "";
  tasks.value = [];
  currentTaskIndex.value = 0;
  currentAnswer.value = "";
  showEvaluation.value = false;
  isCorrect.value = null;
  score.value = 0;
  error.value = null;
  feedback.value = null;

  router.push("/documents");
}
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-8">
    <DPageHeader title="Study Mode" />
    <DPageContent>
      <div class="mx-auto max-w-2xl">
        <!-- Studying State: Displaying Questions -->
        <div
          v-if="pageState === 'studying' && tasks.length > 0"
          class="space-y-2"
        >
          <DTaskAnswer
            :task="currentTask"
            :index="currentTaskIndex"
            v-model="currentAnswer"
            :disabled="showEvaluation"
          />

          <div v-if="showEvaluation">
            <DTaskResult
              :task="currentTask"
              :index="currentTaskIndex"
              :userAnswer="currentAnswer"
              :isCorrect="isCorrect ?? false"
              :feedback="feedback ?? ''"
              class="mt-4"
            />
            <div class="flex justify-end">
              <DButton @click="nextQuestion" class="mt-4">
                {{
                  currentTaskIndex < tasks.length - 1
                    ? "Next Question"
                    : "Show Results"
                }}
              </DButton>
            </div>
          </div>
          <div v-else class="flex justify-end">
            <DButton @click="evaluateAnswer">Evaluate</DButton>
          </div>
        </div>

        <!-- Finished State: Show Score -->
        <div v-if="pageState === 'finished'" class="text-center space-y-4">
          <h2 class="text-2xl font-bold">Study Session Complete!</h2>
          <p class="text-lg">
            You scored <span class="font-bold">{{ score }}</span> out of
            <span class="font-bold">{{ tasks.length }}</span
            >.
          </p>
          <DButton @click="restart">Study Another Document</DButton>
        </div>
      </div>
    </DPageContent>
  </div>
</template>
