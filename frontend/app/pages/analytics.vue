<script setup lang="ts">
import analyticsAuth from '~/middleware/analytics-auth';
import { ref, onMounted, computed, watch } from "vue";
import {
    BarChart3Icon,
    ClockIcon,
    TrendingUpIcon,
    FileTextIcon,
    UsersIcon,
    ActivityIcon,
    SearchIcon,
    GitBranchIcon,
    TrashIcon,
    EditIcon,
    CheckCircleIcon,
    XCircleIcon,
    HelpCircleIcon
} from "lucide-vue-next";
import type { Repository } from "~/types/models";
import { useNotificationsStore } from "~/stores/notifications";

const { $authFetch } = useAuthenticatedFetch();
const notifications = useNotificationsStore();

definePageMeta({
  middleware: analyticsAuth,
  title: 'Analytics Dashboard'
});

interface VersionComparison {
  fromVersion: number;
  toVersion: number;

  version1: {
    question: string;
    answer_options?: Array<{
      id: string | number;
      answer: string;
      is_correct: boolean;
    }>;
  };

  version2: {
    question: string;
    answer_options?: Array<{
      id: string | number;
      answer: string;
      is_correct: boolean;
    }>;
  };

  // optional fields
  diff?: string;
  changes?: Array<{
    field: string;
    oldValue: unknown;
    newValue: unknown;
  }>;

  // differences
  differences?: Array<{
  field: string;
  before: unknown;
  after: unknown;
}>;

}

// Types
interface TaskLifecycleStats {
    repository_id: string;
    total_created: number;
    total_deleted: number;
    total_modified: number;
    last_updated: string;
}

interface AnswerAnalytics {
    repository_id: string;
    total_answers: number;
    total_correct: number;
    total_incorrect: number;
    total_partial: number;
    unique_users: number;
    success_rate: number;
}

interface RepositoryStats {
    repository_id: string;
    task_lifecycle: TaskLifecycleStats;
    answer_analytics: AnswerAnalytics;
    generated_at: string;
}

interface TaskStats {
    task_id: string;
    total_users: number;
    total_attempts: number;
    total_correct: number;
    total_incorrect: number;
    total_partial: number;
    success_rate: number;
}

interface TaskSnapshot {
    task_id: string;
    version: number;
    question: string;
    type: string;
    created_at: string;
    answer_options: {
        id: string;
        answer: string;
        is_correct: boolean;
    }[];
}

interface VersionInfo {
    version: number;
    question: string;
    type: string;
    created_at: string;
}

interface UserPageTime {
    user_id: string;
    page: string;
    total_seconds: number;
    total_sessions: number;
    average_session_seconds: number;
}

interface AnswerEvent {
    id: string;
    user_id: string;
    result: string;
    answer_option_id?: string;
    user_answer_text?: string;
    created_at: string;
}

interface ChangeEvent {
    id: string;
    change_type: string;
    user_id?: string;
    old_value?: string;
    new_value?: string;
    change_metadata?: string;
    created_at: string;
}

interface PageStats {
    page: string;
    total_sessions: number;
    total_seconds: number;
    average_seconds: number;
    top_users: Array<{
        user_id: string;
        total_seconds: number;
    }>;
}

// Chart data interfaces
interface ChartData {
    labels: string[];
    datasets: Array<{
        label?: string;
        data: number[];
        backgroundColor: string | string[];
        borderColor: string | string[];
        borderWidth: number;
    }>;
}

// State
const repositories = ref<Repository[]>([]);
const selectedRepositoryId = ref<string | null>(null);
const selectedTaskId = ref<string | null>(null);
const loading = ref(false);
const activeTab = ref<'overview' | 'tasks' | 'users' | 'timeline'>('overview');

// Data
const repositoryStats = ref<RepositoryStats | null>(null);
const taskStats = ref<TaskStats | null>(null);
const taskSnapshot = ref<TaskSnapshot | null>(null);
const taskVersions = ref<VersionInfo[]>([]);
const answerHistory = ref<AnswerEvent[]>([]);
const changeHistory = ref<ChangeEvent[]>([]);
const userPageTime = ref<UserPageTime | null>(null);
const homePageStats = ref<PageStats | null>(null);
const tasksPageStats = ref<PageStats | null>(null);
const repositoriesPageStats = ref<PageStats | null>(null);

// Version comparison
const showVersionCompare = ref(false);
const compareVersion1 = ref<number>(1);
const compareVersion2 = ref<number>(2);
const versionComparison = ref<VersionComparison | null>(null);


// Search/Filter
const taskSearchQuery = ref("");
const selectedUserId = ref<string | null>(null);

// Chart data with proper typing
const answerDistributionChart = ref<ChartData | null>(null);
const taskLifecycleChart = ref<ChartData | null>(null);
const userEngagementChart = ref<ChartData | null>(null);

const modifiedTasksPercentage = computed(() => {
    if (!repositoryStats.value) return 0;
    const { total_created, total_modified } = repositoryStats.value.task_lifecycle;
    return total_created > 0 ? Math.round((total_modified / total_created) * 100) : 0;
});

const deletedTasksPercentage = computed(() => {
    if (!repositoryStats.value) return 0;
    const { total_created, total_deleted } = repositoryStats.value.task_lifecycle;
    return total_created > 0 ? Math.round((total_deleted / total_created) * 100) : 0;
});

// Lifecycle
onMounted(async () => {
    await fetchRepositories();
    await fetchPageStats();
});

// Watch for repository selection
watch(selectedRepositoryId, async (newId) => {
    if (newId) {
        await fetchRepositoryStats(newId);
    }
});

// Watch for task selection
watch(selectedTaskId, async (newId) => {
    if (newId) {
        await loadTaskData(newId);
    }
});

// API Functions
async function fetchRepositories() {
    loading.value = true;
    try {
        const response = await $authFetch("/repositories") as { repositories?: Repository[] } | Repository[];
        const list = ('repositories' in response ? response.repositories : response) as Repository[];
        repositories.value = list;
       
        // Auto-select first repository with null check
        if (list.length > 0 && !selectedRepositoryId.value && list[0]) {
            selectedRepositoryId.value = list[0].id;
        }
    } catch (error) {
        console.error("Error fetching repositories:", error);
        notifications.error("Failed to load repositories.");
    } finally {
        loading.value = false;
    }
}

async function fetchRepositoryStats(repositoryId: string) {
    loading.value = true;
    try {
        const stats = await $authFetch(`/repositories/${repositoryId}/statistics`) as RepositoryStats;
        repositoryStats.value = stats;
       
        // Prepare chart data
        prepareCharts(stats);
    } catch (error) {
        console.error("Error fetching repository stats:", error);
        notifications.error("Failed to load repository statistics.");
    } finally {
        loading.value = false;
    }
}

async function fetchPageStats() {
    try {
        const [homeStats, tasksStats, reposStats] = await Promise.all([
            $authFetch("/analytics/pages/home/stats") as Promise<PageStats>,
            $authFetch("/analytics/pages/tasks/stats") as Promise<PageStats>,
            $authFetch("/analytics/pages/repositories/stats") as Promise<PageStats>
        ]);
       
        homePageStats.value = homeStats;
        tasksPageStats.value = tasksStats;
        repositoriesPageStats.value = reposStats;
    } catch (error) {
        console.error("Error fetching page stats:", error);
        notifications.error("Failed to load page statistics.");
    }
}

async function loadTaskData(taskId: string) {
    loading.value = true;
    try {
        // Fetch all task data in parallel
        const [stats, snapshot, versions, answers, changes] = await Promise.all([
            $authFetch(`/tasks/${taskId}/stats`) as Promise<TaskStats>,
            $authFetch(`/tasks/${taskId}/snapshot/latest`) as Promise<TaskSnapshot>,
            $authFetch(`/tasks/${taskId}/versions`) as Promise<{ versions: VersionInfo[] }>,
            $authFetch(`/tasks/${taskId}/answer-history?limit=50`) as Promise<{ events: AnswerEvent[] }>,
            $authFetch(`/tasks/${taskId}/change-history?limit=50`) as Promise<{ changes: ChangeEvent[] }>
        ]);
       
        taskStats.value = stats;
        taskSnapshot.value = snapshot;
        taskVersions.value = versions.versions;
        answerHistory.value = answers.events;
        changeHistory.value = changes.changes;
       
        // Set default comparison versions with null check
        if (versions && versions.versions) {
            compareVersion1.value = versions.versions[versions.versions.length - 1]!.version;
            compareVersion2.value = versions.versions[0]!.version;
        }

    } catch (error) {
        console.error("Error loading task data:", error);
        notifications.error("Failed to load task data.");
    } finally {
        loading.value = false;
    }
}

async function fetchUserPageTime(userId: string) {
    try {
        const data = await $authFetch(`/auth/users/${userId}/time-spent?page=tasks`) as UserPageTime;
        userPageTime.value = data;
    } catch (error) {
        console.error("Error fetching user page time:", error);
        notifications.error("Failed to load user time data.");
    }
}

async function compareVersions() {
    if (!selectedTaskId.value) return;
   
    loading.value = true;
    try {
        const comparison = await $authFetch(
            `/tasks/${selectedTaskId.value}/compare?version1=${compareVersion1.value}&version2=${compareVersion2.value}`
        );
        versionComparison.value = comparison;
        showVersionCompare.value = true;
    } catch (error) {
        console.error("Error comparing versions:", error);
        notifications.error("Failed to compare versions.");
    } finally {
        loading.value = false;
    }
}

// Chart preparation
function prepareCharts(stats: RepositoryStats) {
    // Answer distribution chart
    answerDistributionChart.value = {
        labels: ['Correct', 'Incorrect', 'Partial'],
        datasets: [{
            data: [
                stats.answer_analytics.total_correct,
                stats.answer_analytics.total_incorrect,
                stats.answer_analytics.total_partial
            ],
            backgroundColor: [
                'rgba(34, 197, 94, 0.7)',
                'rgba(239, 68, 68, 0.7)',
                'rgba(245, 158, 11, 0.7)'
            ],
            borderColor: [
                'rgb(34, 197, 94)',
                'rgb(239, 68, 68)',
                'rgb(245, 158, 11)'
            ],
            borderWidth: 1
        }]
    };
   
    // Task lifecycle chart
    taskLifecycleChart.value = {
        labels: ['Created', 'Modified', 'Deleted'],
        datasets: [{
            data: [
                stats.task_lifecycle.total_created,
                stats.task_lifecycle.total_modified,
                stats.task_lifecycle.total_deleted
            ],
            backgroundColor: [
                'rgba(59, 130, 246, 0.7)',
                'rgba(168, 85, 247, 0.7)',
                'rgba(239, 68, 68, 0.7)'
            ],
            borderColor: [
                'rgb(59, 130, 246)',
                'rgb(168, 85, 247)',
                'rgb(239, 68, 68)'
            ],
            borderWidth: 1
        }]
    };
   
    // User engagement chart
    userEngagementChart.value = {
        labels: ['Home', 'Tasks', 'Repositories'],
        datasets: [{
            label: 'Total Time (seconds)',
            data: [
                homePageStats.value?.total_seconds || 0,
                tasksPageStats.value?.total_seconds || 0,
                repositoriesPageStats.value?.total_seconds || 0
            ],
            backgroundColor: 'rgba(59, 130, 246, 0.7)',
            borderColor: 'rgb(59, 130, 246)',
            borderWidth: 1
        }]
    };
}

// Helper Functions
function formatDate(dateString: string): string {
    return new Date(dateString).toLocaleString();
}

function formatDuration(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
   
    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    }
    return `${secs}s`;
}

function getResultIcon(result: string) {
    switch (result.toLowerCase()) {
        case 'correct':
            return CheckCircleIcon;
        case 'incorrect':
            return XCircleIcon;
        case 'partial':
            return HelpCircleIcon;
        default:
            return HelpCircleIcon;
    }
}

function getChangeTypeBadgeClass(changeType: string): string {
    switch (changeType) {
        case 'QUESTION_UPDATE':
            return 'bg-blue-100 text-blue-800';
        case 'OPTION_ADDED':
            return 'bg-green-100 text-green-800';
        case 'OPTION_UPDATED':
            return 'bg-yellow-100 text-yellow-800';
        case 'OPTION_DELETED':
            return 'bg-red-100 text-red-800';
        case 'CORRECTNESS_CHANGED':
            return 'bg-purple-100 text-purple-800';
        case 'MODIFIED':
            return 'bg-indigo-100 text-indigo-800';
        case 'DELETED':
            return 'bg-red-100 text-red-800';
        default:
            return 'bg-gray-100 text-gray-800';
    }
}

function getChangeTypeIcon(changeType: string) {
    switch (changeType) {
        case 'QUESTION_UPDATE':
        case 'MODIFIED':
            return EditIcon;
        case 'OPTION_ADDED':
            return CheckCircleIcon;
        case 'OPTION_UPDATED':
        case 'CORRECTNESS_CHANGED':
            return EditIcon;
        case 'OPTION_DELETED':
        case 'DELETED':
            return TrashIcon;
        default:
            return ActivityIcon;
    }
}

function closeVersionCompare() {
    showVersionCompare.value = false;
    versionComparison.value = null;
}
</script>

<template>
    <div class="h-full flex flex-col">
        <div class="w-full mt-8 flex-1 overflow-auto">
            <div class="max-w-7xl mx-auto px-4">
                <DPageHeader title="Analytics Dashboard" />
               
                <!-- Repository Selector -->
                <div class="mb-6">
                    <label class="block text-sm font-medium text-gray-700 mb-2">
                        Select Repository
                    </label>
                    <select
                        v-model="selectedRepositoryId"
                        class="w-full max-w-md border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
                    >
                        <option :value="null">Select a repository...</option>
                        <option
                            v-for="repo in repositories"
                            :key="repo.id"
                            :value="repo.id"
                        >
                            {{ repo.name }}
                        </option>
                    </select>
                </div>
                <!-- Repository Statistics Card -->
                <div v-if="repositoryStats" class="mb-8">
                    <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
                        <BarChart3Icon class="w-5 h-5" />
                        Repository Statistics
                    </h2>
                   
                    <!-- Task Lifecycle Stats -->
                    <div class="mb-6">
                        <h3 class="text-lg font-medium mb-3 text-gray-700">Task Lifecycle</h3>
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div class="bg-white p-6 rounded-lg shadow border border-gray-200">
                                <div class="flex items-center justify-between">
                                    <div>
                                        <p class="text-sm text-gray-500">Tasks Created</p>
                                        <p class="text-3xl font-bold text-blue-600">
                                            {{ repositoryStats.task_lifecycle.total_created }}
                                        </p>
                                    </div>
                                    <TrendingUpIcon class="w-12 h-12 text-blue-200" />
                                </div>
                            </div>
                           
                            <div class="bg-white p-6 rounded-lg shadow border border-gray-200">
                                <div class="flex items-center justify-between">
                                    <div>
                                        <p class="text-sm text-gray-500">Tasks Modified</p>
                                        <p class="text-3xl font-bold text-purple-600">
                                            {{ repositoryStats.task_lifecycle.total_modified }}
                                        </p>
                                        <p class="text-xs text-gray-500 mt-1">{{ modifiedTasksPercentage }}% of created</p>
                                    </div>
                                    <EditIcon class="w-12 h-12 text-purple-200" />
                                </div>
                            </div>
                           
                            <div class="bg-white p-6 rounded-lg shadow border border-gray-200">
                                <div class="flex items-center justify-between">
                                    <div>
                                        <p class="text-sm text-gray-500">Tasks Deleted</p>
                                        <p class="text-3xl font-bold text-red-600">
                                            {{ repositoryStats.task_lifecycle.total_deleted }}
                                        </p>
                                        <p class="text-xs text-gray-500 mt-1">{{ deletedTasksPercentage }}% of created</p>
                                    </div>
                                    <TrashIcon class="w-12 h-12 text-red-200" />
                                </div>
                            </div>
                        </div>
                    </div>
                   
                    <!-- Answer Analytics -->
                    <div class="mb-6">
                        <h3 class="text-lg font-medium mb-3 text-gray-700">Answer Analytics</h3>
                        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                            <div class="bg-white p-6 rounded-lg shadow border border-gray-200">
                                <div class="flex items-center justify-between">
                                    <div>
                                        <p class="text-sm text-gray-500">Total Answers</p>
                                        <p class="text-3xl font-bold text-blue-600">
                                            {{ repositoryStats.answer_analytics.total_answers }}
                                        </p>
                                    </div>
                                    <FileTextIcon class="w-12 h-12 text-blue-200" />
                                </div>
                            </div>
                           
                            <div class="bg-white p-6 rounded-lg shadow border border-gray-200">
                                <div class="flex items-center justify-between">
                                    <div>
                                        <p class="text-sm text-gray-500">Correct Answers</p>
                                        <p class="text-3xl font-bold text-green-600">
                                            {{ repositoryStats.answer_analytics.total_correct }}
                                        </p>
                                    </div>
                                    <CheckCircleIcon class="w-12 h-12 text-green-200" />
                                </div>
                            </div>
                           
                            <div class="bg-white p-6 rounded-lg shadow border border-gray-200">
                                <div class="flex items-center justify-between">
                                    <div>
                                        <p class="text-sm text-gray-500">Incorrect Answers</p>
                                        <p class="text-3xl font-bold text-red-600">
                                            {{ repositoryStats.answer_analytics.total_incorrect }}
                                        </p>
                                    </div>
                                    <XCircleIcon class="w-12 h-12 text-red-200" />
                                </div>
                            </div>
                           
                            <div class="bg-white p-6 rounded-lg shadow border border-gray-200">
                                <div class="flex items-center justify-between">
                                    <div>
                                        <p class="text-sm text-gray-500">Success Rate</p>
                                        <p class="text-3xl font-bold text-blue-600">
                                            {{ repositoryStats.answer_analytics.success_rate }}%
                                        </p>
                                    </div>
                                    <TrendingUpIcon class="w-12 h-12 text-blue-200" />
                                </div>
                            </div>
                        </div>
                    </div>
                   
                    <!-- Charts -->
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div class="bg-white p-6 rounded-lg shadow border border-gray-200">
                            <h3 class="text-lg font-medium mb-3 text-gray-700">Answer Distribution</h3>
                            <div class="h-64 flex items-center justify-center">
                                <DChart
                                    v-if="answerDistributionChart"
                                    type="pie"
                                    :data="answerDistributionChart"
                                    :options="{ responsive: true, maintainAspectRatio: false }"
                                />
                                <div v-else class="text-gray-500">No data available</div>
                            </div>
                        </div>
                       
                        <div class="bg-white p-6 rounded-lg shadow border border-gray-200">
                            <h3 class="text-lg font-medium mb-3 text-gray-700">Task Lifecycle</h3>
                            <div class="h-64 flex items-center justify-center">
                                <DChart
                                    v-if="taskLifecycleChart"
                                    type="doughnut"
                                    :data="taskLifecycleChart"
                                    :options="{ responsive: true, maintainAspectRatio: false }"
                                />
                                <div v-else class="text-gray-500">No data available</div>
                            </div>
                        </div>
                    </div>
                </div>
               
                <!-- User Engagement Stats -->
                <div v-if="homePageStats || tasksPageStats || repositoriesPageStats" class="mb-8">
                    <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
                        <UsersIcon class="w-5 h-5" />
                        User Engagement
                    </h2>
                   
                    <div class="bg-white p-6 rounded-lg shadow border border-gray-200">
                        <h3 class="text-lg font-medium mb-3 text-gray-700">Time Spent by Page</h3>
                        <div class="h-64 flex items-center justify-center">
                            <DChart
                                v-if="userEngagementChart"
                                type="bar"
                                :data="userEngagementChart"
                                :options="{ responsive: true, maintainAspectRatio: false }"
                            />
                            <div v-else class="text-gray-500">No data available</div>
                        </div>
                       
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                            <div v-if="homePageStats" class="p-4 bg-gray-50 rounded-lg">
                                <h4 class="font-medium text-gray-700 mb-2">Home Page</h4>
                                <p class="text-sm text-gray-600">Total time: {{ formatDuration(homePageStats.total_seconds) }}</p>
                                <p class="text-sm text-gray-600">Sessions: {{ homePageStats.total_sessions }}</p>
                                <p class="text-sm text-gray-600">Average: {{ formatDuration(Math.round(homePageStats.average_seconds)) }}</p>
                            </div>
                           
                            <div v-if="tasksPageStats" class="p-4 bg-gray-50 rounded-lg">
                                <h4 class="font-medium text-gray-700 mb-2">Tasks Page</h4>
                                <p class="text-sm text-gray-600">Total time: {{ formatDuration(tasksPageStats.total_seconds) }}</p>
                                <p class="text-sm text-gray-600">Sessions: {{ tasksPageStats.total_sessions }}</p>
                                <p class="text-sm text-gray-600">Average: {{ formatDuration(Math.round(tasksPageStats.average_seconds)) }}</p>
                            </div>
                           
                            <div v-if="repositoriesPageStats" class="p-4 bg-gray-50 rounded-lg">
                                <h4 class="font-medium text-gray-700 mb-2">Repositories Page</h4>
                                <p class="text-sm text-gray-600">Total time: {{ formatDuration(repositoriesPageStats.total_seconds) }}</p>
                                <p class="text-sm text-gray-600">Sessions: {{ repositoriesPageStats.total_sessions }}</p>
                                <p class="text-sm text-gray-600">Average: {{ formatDuration(Math.round(repositoriesPageStats.average_seconds)) }}</p>
                            </div>
                        </div>
                    </div>
                </div>
               
                <!-- Task Selector -->
                <div class="mb-6">
                    <label class="block text-sm font-medium text-gray-700 mb-2">
                        Select Task to Analyze
                    </label>
                    <div class="flex gap-2">
                        <input
                            v-model="taskSearchQuery"
                            type="text"
                            placeholder="Enter task ID..."
                            class="flex-1 max-w-md border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500"
                        />
                        <DButton
                            @click="selectedTaskId = taskSearchQuery"
                            :icon-left="SearchIcon"
                            variant="primary"
                        >
                            Load Task
                        </DButton>
                    </div>
                </div>
               
                <!-- Task Analytics (shown when task is selected) -->
                <div v-if="selectedTaskId && taskStats" class="space-y-6">
                    <!-- Task Stats Overview -->
                    <div class="bg-white p-6 rounded-lg shadow border border-gray-200">
                        <h3 class="text-lg font-semibold mb-4">Task Performance</h3>
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div class="text-center">
                                <p class="text-2xl font-bold text-blue-600">{{ taskStats.total_users }}</p>
                                <p class="text-sm text-gray-500">Users</p>
                            </div>
                            <div class="text-center">
                                <p class="text-2xl font-bold text-purple-600">{{ taskStats.total_attempts }}</p>
                                <p class="text-sm text-gray-500">Total Attempts</p>
                            </div>
                            <div class="text-center">
                                <p class="text-2xl font-bold text-green-600">{{ taskStats.total_correct }}</p>
                                <p class="text-sm text-gray-500">Correct</p>
                            </div>
                            <div class="text-center">
                                <p class="text-2xl font-bold text-orange-600">{{ taskStats.success_rate }}%</p>
                                <p class="text-sm text-gray-500">Success Rate</p>
                            </div>
                        </div>
                    </div>
                   
                    <!-- Tabs -->
                    <div class="border-b border-gray-200">
                        <nav class="flex gap-4">
                            <button
                                @click="activeTab = 'overview'"
                                :class="[
                                    'px-4 py-2 border-b-2 font-medium text-sm',
                                    activeTab === 'overview'
                                        ? 'border-blue-500 text-blue-600'
                                        : 'border-transparent text-gray-500 hover:text-gray-700'
                                ]"
                            >
                                Overview
                            </button>
                            <button
                                @click="activeTab = 'tasks'"
                                :class="[
                                    'px-4 py-2 border-b-2 font-medium text-sm',
                                    activeTab === 'tasks'
                                        ? 'border-blue-500 text-blue-600'
                                        : 'border-transparent text-gray-500 hover:text-gray-700'
                                ]"
                            >
                                Versions ({{ taskVersions.length }})
                            </button>
                            <button
                                @click="activeTab = 'timeline'"
                                :class="[
                                    'px-4 py-2 border-b-2 font-medium text-sm',
                                    activeTab === 'timeline'
                                        ? 'border-blue-500 text-blue-600'
                                        : 'border-transparent text-gray-500 hover:text-gray-700'
                                ]"
                            >
                                History
                            </button>
                            <button
                                @click="activeTab = 'users'"
                                :class="[
                                    'px-4 py-2 border-b-2 font-medium text-sm',
                                    activeTab === 'users'
                                        ? 'border-blue-500 text-blue-600'
                                        : 'border-transparent text-gray-500 hover:text-gray-700'
                                ]"
                            >
                                Users
                            </button>
                        </nav>
                    </div>
                   
                    <!-- Tab Content -->
                    <div class="space-y-6">
                        <!-- Overview Tab -->
                        <div v-if="activeTab === 'overview'" class="space-y-6">
                            <!-- Current Task Snapshot -->
                            <div v-if="taskSnapshot" class="bg-white p-6 rounded-lg shadow border border-gray-200">
                                <h3 class="text-lg font-semibold mb-4 flex items-center gap-2">
                                    <GitBranchIcon class="w-5 h-5" />
                                    Current Version (v{{ taskSnapshot.version }})
                                </h3>
                                <div class="space-y-3">
                                    <div>
                                        <span class="text-sm font-medium text-gray-500">Question:</span>
                                        <p class="mt-1">{{ taskSnapshot.question }}</p>
                                    </div>
                                    <div>
                                        <span class="text-sm font-medium text-gray-500">Type:</span>
                                        <span class="ml-2 px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm">
                                            {{ taskSnapshot.type }}
                                        </span>
                                    </div>
                                    <div v-if="taskSnapshot.answer_options.length > 0">
                                        <span class="text-sm font-medium text-gray-500">Answer Options:</span>
                                        <ul class="mt-2 space-y-2">
                                            <li
                                                v-for="option in taskSnapshot.answer_options"
                                                :key="option.id"
                                                class="flex items-center gap-2 p-2 bg-gray-50 rounded"
                                            >
                                                <span
                                                    :class="[
                                                        'px-2 py-1 rounded text-xs font-medium',
                                                        option.is_correct
                                                            ? 'bg-green-100 text-green-800'
                                                            : 'bg-gray-100 text-gray-800'
                                                    ]"
                                                >
                                                    {{ option.is_correct ? '✓ Correct' : 'Incorrect' }}
                                                </span>
                                                <span>{{ option.answer }}</span>
                                            </li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                           
                            <!-- Recent Answer Events -->
                            <div class="bg-white p-6 rounded-lg shadow border border-gray-200">
                                <h3 class="text-lg font-semibold mb-4">Recent Answers (Last 10)</h3>
                                <div v-if="answerHistory.length > 0" class="space-y-2">
                                    <div
                                        v-for="event in answerHistory.slice(0, 10)"
                                        :key="event.id"
                                        class="flex items-center justify-between p-3 bg-gray-50 rounded"
                                    >
                                        <div class="flex items-center gap-3">
                                            <component
                                                :is="getResultIcon(event.result)"
                                                :class="[
                                                    'w-5 h-5',
                                                    event.result.toLowerCase() === 'correct' ? 'text-green-600' :
                                                    event.result.toLowerCase() === 'incorrect' ? 'text-red-600' : 'text-yellow-600'
                                                ]"
                                            />
                                            <span class="text-sm text-gray-600">
                                                User: {{ event.user_id.substring(0, 8) }}...
                                            </span>
                                        </div>
                                        <span class="text-xs text-gray-500">
                                            {{ formatDate(event.created_at) }}
                                        </span>
                                    </div>
                                </div>
                                <p v-else class="text-gray-500 text-center py-4">
                                    No answer history available
                                </p>
                            </div>
                        </div>
                       
                        <!-- Tasks Tab -->
                        <div v-if="activeTab === 'tasks'" class="space-y-6">
                            <!-- Version Comparison Tool -->
                            <div class="bg-white p-6 rounded-lg shadow border border-gray-200">
                                <h3 class="text-lg font-semibold mb-4">Compare Versions</h3>
                                <div class="flex gap-4 items-end">
                                    <div class="flex-1">
                                        <label class="block text-sm font-medium text-gray-700 mb-2">
                                            Version 1
                                        </label>
                                        <select
                                            v-model="compareVersion1"
                                            class="w-full border border-gray-300 rounded-lg px-4 py-2"
                                        >
                                            <option
                                                v-for="v in taskVersions"
                                                :key="v.version"
                                                :value="v.version"
                                            >
                                                v{{ v.version }} - {{ formatDate(v.created_at) }}
                                            </option>
                                        </select>
                                    </div>
                                    <div class="flex-1">
                                        <label class="block text-sm font-medium text-gray-700 mb-2">
                                            Version 2
                                        </label>
                                        <select
                                            v-model="compareVersion2"
                                            class="w-full border border-gray-300 rounded-lg px-4 py-2"
                                        >
                                            <option
                                                v-for="v in taskVersions"
                                                :key="v.version"
                                                :value="v.version"
                                            >
                                                v{{ v.version }} - {{ formatDate(v.created_at) }}
                                            </option>
                                        </select>
                                    </div>
                                    <DButton @click="compareVersions" variant="primary">
                                        Compare
                                    </DButton>
                                </div>
                            </div>
                           
                            <!-- Version Comparison Results -->
                            <div v-if="showVersionCompare && versionComparison" class="bg-white p-6 rounded-lg shadow border border-gray-200">
                                <div class="flex items-center justify-between mb-4">
                                    <h3 class="text-lg font-semibold">Version Comparison Results</h3>
                                    <DButton @click="closeVersionCompare" variant="transparent" size="sm">
                                        Close
                                    </DButton>
                                </div>
                                <div class="space-y-4">
                                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div class="p-4 bg-blue-50 rounded-lg">
                                            <h4 class="font-medium text-blue-800 mb-2">Version {{ compareVersion1 }}</h4>
                                            <p class="text-sm text-gray-700">{{ versionComparison.version1.question }}</p>
                                            <div v-if="versionComparison.version1.answer_options" class="mt-2">
                                                <p class="text-xs font-medium text-gray-500 mb-1">Answer Options:</p>
                                                <ul class="text-xs space-y-1">
                                                    <li
                                                        v-for="option in versionComparison.version1.answer_options"
                                                        :key="option.id"
                                                        class="flex items-center gap-1"
                                                    >
                                                        <span
                                                            :class="[
                                                                'px-1 py-0.5 rounded text-xs',
                                                                option.is_correct
                                                                    ? 'bg-green-100 text-green-800'
                                                                    : 'bg-gray-100 text-gray-800'
                                                            ]"
                                                        >
                                                            {{ option.is_correct ? '✓' : '✗' }}
                                                        </span>
                                                        <span>{{ option.answer }}</span>
                                                    </li>
                                                </ul>
                                            </div>
                                        </div>
                                        <div class="p-4 bg-purple-50 rounded-lg">
                                            <h4 class="font-medium text-purple-800 mb-2">Version {{ compareVersion2 }}</h4>
                                            <p class="text-sm text-gray-700">{{ versionComparison.version2.question }}</p>
                                            <div v-if="versionComparison.version2.answer_options" class="mt-2">
                                                <p class="text-xs font-medium text-gray-500 mb-1">Answer Options:</p>
                                                <ul class="text-xs space-y-1">
                                                    <li
                                                        v-for="option in versionComparison.version2.answer_options"
                                                        :key="option.id"
                                                        class="flex items-center gap-1"
                                                    >
                                                        <span
                                                            :class="[
                                                                'px-1 py-0.5 rounded text-xs',
                                                                option.is_correct
                                                                    ? 'bg-green-100 text-green-800'
                                                                    : 'bg-gray-100 text-gray-800'
                                                            ]"
                                                        >
                                                            {{ option.is_correct ? '✓' : '✗' }}
                                                        </span>
                                                        <span>{{ option.answer }}</span>
                                                    </li>
                                                </ul>
                                            </div>
                                        </div>
                                    </div>
                                   
                                    <div v-if="versionComparison.differences" class="p-4 bg-yellow-50 rounded-lg">
                                        <h4 class="font-medium text-yellow-800 mb-2">Differences</h4>
                                        <ul class="text-sm space-y-1">
                                            <li v-for="(diff, index) in versionComparison.differences" :key="index">
                                                {{ diff }}
                                            </li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                           
                            <!-- Version List -->
                            <div class="bg-white p-6 rounded-lg shadow border border-gray-200">
                                <h3 class="text-lg font-semibold mb-4">All Versions</h3>
                                <div class="space-y-3">
                                    <div
                                        v-for="version in taskVersions"
                                        :key="version.version"
                                        class="p-4 bg-gray-50 rounded-lg"
                                    >
                                        <div class="flex items-center justify-between mb-2">
                                            <span class="font-semibold text-blue-600">
                                                Version {{ version.version }}
                                            </span>
                                            <span class="text-sm text-gray-500">
                                                {{ formatDate(version.created_at) }}
                                            </span>
                                        </div>
                                        <p class="text-sm text-gray-700">{{ version.question }}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                       
                        <!-- History Tab -->
                        <div v-if="activeTab === 'timeline'" class="space-y-6">
                            <!-- Change History -->
                            <div class="bg-white p-6 rounded-lg shadow border border-gray-200">
                                <h3 class="text-lg font-semibold mb-4">Change History</h3>
                                <div v-if="changeHistory.length > 0" class="space-y-2">
                                    <div
                                        v-for="event in changeHistory"
                                        :key="event.id"
                                        class="p-3 bg-gray-50 rounded"
                                    >
                                        <div class="flex items-center justify-between mb-2">
                                            <div class="flex items-center gap-2">
                                                <component
                                                    :is="getChangeTypeIcon(event.change_type)"
                                                    :class="[
                                                        'w-4 h-4',
                                                        event.change_type === 'DELETED' ? 'text-red-600' :
                                                        event.change_type === 'MODIFIED' ? 'text-indigo-600' :
                                                        event.change_type === 'QUESTION_UPDATE' ? 'text-blue-600' :
                                                        event.change_type === 'OPTION_ADDED' ? 'text-green-600' :
                                                        event.change_type === 'OPTION_UPDATED' ? 'text-yellow-600' :
                                                        event.change_type === 'OPTION_DELETED' ? 'text-red-600' :
                                                        event.change_type === 'CORRECTNESS_CHANGED' ? 'text-purple-600' :
                                                        'text-gray-600'
                                                    ]"
                                                />
                                                <span
                                                    :class="[
                                                        'px-2 py-1 rounded text-xs font-medium',
                                                        getChangeTypeBadgeClass(event.change_type)
                                                    ]"
                                                >
                                                    {{ event.change_type.replace('_', ' ') }}
                                                </span>
                                            </div>
                                            <span class="text-xs text-gray-500">
                                                {{ formatDate(event.created_at) }}
                                            </span>
                                        </div>
                                        <div v-if="event.old_value || event.new_value" class="text-sm space-y-1">
                                            <div v-if="event.old_value" class="text-red-600">
                                                <span class="font-medium">Old:</span> {{ event.old_value }}
                                            </div>
                                            <div v-if="event.new_value" class="text-green-600">
                                                <span class="font-medium">New:</span> {{ event.new_value }}
                                            </div>
                                        </div>
                                        <div v-if="event.change_metadata" class="text-xs text-gray-500 mt-1">
                                            {{ event.change_metadata }}
                                        </div>
                                    </div>
                                </div>
                                <p v-else class="text-gray-500 text-center py-4">
                                    No change history available
                                </p>
                            </div>
                           
                            <!-- Answer History (Full) -->
                            <div class="bg-white p-6 rounded-lg shadow border border-gray-200">
                                <h3 class="text-lg font-semibold mb-4">All Answer Events</h3>
                                <div v-if="answerHistory.length > 0" class="space-y-2 max-h-96 overflow-y-auto">
                                    <div
                                        v-for="event in answerHistory"
                                        :key="event.id"
                                        class="flex items-center justify-between p-3 bg-gray-50 rounded"
                                    >
                                        <div class="flex items-center gap-3">
                                            <component
                                                :is="getResultIcon(event.result)"
                                                :class="[
                                                    'w-5 h-5',
                                                    event.result.toLowerCase() === 'correct' ? 'text-green-600' :
                                                    event.result.toLowerCase() === 'incorrect' ? 'text-red-600' : 'text-yellow-600'
                                                ]"
                                            />
                                            <span class="text-sm text-gray-600">
                                                User: {{ event.user_id.substring(0, 8) }}...
                                            </span>
                                            <span v-if="event.user_answer_text" class="text-sm text-gray-500">
                                                Answer: {{ event.user_answer_text }}
                                            </span>
                                        </div>
                                        <span class="text-xs text-gray-500">
                                            {{ formatDate(event.created_at) }}
                                        </span>
                                    </div>
                                </div>
                                <p v-else class="text-gray-500 text-center py-4">
                                    No answer history available
                                </p>
                            </div>
                        </div>
                       
                        <!-- Users Tab -->
                        <div v-if="activeTab === 'users'" class="space-y-6">
                            <div class="bg-white p-6 rounded-lg shadow border border-gray-200">
                                <h3 class="text-lg font-semibold mb-4">User Analytics</h3>
                                <div class="space-y-4">
                                    <div>
                                        <label class="block text-sm font-medium text-gray-700 mb-2">
                                            Analyze User
                                        </label>
                                        <div class="flex gap-2">
                                            <input
                                                v-model="selectedUserId"
                                                type="text"
                                                placeholder="Enter user ID..."
                                                class="flex-1 border border-gray-300 rounded-lg px-4 py-2"
                                            />
                                            <DButton
                                                @click="fetchUserPageTime(selectedUserId!)"
                                                :icon-left="ClockIcon"
                                                :disabled="!selectedUserId"
                                            >
                                                Load
                                            </DButton>
                                        </div>
                                    </div>
                                   
                                    <!-- User Time Data -->
                                    <div v-if="userPageTime" class="p-4 bg-blue-50 rounded-lg">
                                        <div class="grid grid-cols-3 gap-4">
                                            <div>
                                                <p class="text-sm text-gray-500">Total Time</p>
                                                <p class="text-xl font-bold text-blue-600">
                                                    {{ formatDuration(userPageTime.total_seconds) }}
                                                </p>
                                            </div>
                                            <div>
                                                <p class="text-sm text-gray-500">Sessions</p>
                                                <p class="text-xl font-bold text-blue-600">
                                                    {{ userPageTime.total_sessions }}
                                                </p>
                                            </div>
                                            <div>
                                                <p class="text-sm text-gray-500">Avg Session</p>
                                                <p class="text-xl font-bold text-blue-600">
                                                    {{ formatDuration(Math.round(userPageTime.average_session_seconds)) }}
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
               
                <!-- Empty State -->
                <div v-if="!selectedTaskId" class="bg-white p-12 rounded-lg shadow border border-gray-200 text-center">
                    <BarChart3Icon class="w-16 h-16 text-gray-300 mx-auto mb-4" />
                    <h3 class="text-lg font-medium text-gray-900 mb-2">Select a task to analyze</h3>
                    <p class="text-gray-500">Enter a task ID above to view detailed analytics.</p>
                </div>
            </div>
        </div>
    </div>
</template>