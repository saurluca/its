<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { RefreshCw } from "lucide-vue-next";

interface UserSkillProgress {
    skill_id: string;
    skill_name: string;
    progress: number; // 0..1
    updated_at: string; // ISO string
}

const { $authFetch } = useAuthenticatedFetch();

const loading = ref<boolean>(false);
const error = ref<string | null>(null);
const skills = ref<UserSkillProgress[]>([]);

async function fetchUserSkills() {
    loading.value = true;
    error.value = null;
    try {
        const resp = (await $authFetch("/skills/user/progress")) as UserSkillProgress[];
        skills.value = (resp || []).sort((a, b) => a.skill_name.localeCompare(b.skill_name));
    } catch (e) {
        console.error("Failed to load user skills:", e);
        error.value = "Failed to load your skills.";
    } finally {
        loading.value = false;
    }
}

onMounted(fetchUserSkills);

const hasSkills = computed(() => skills.value.length > 0);

function formatUpdatedAt(iso: string): string {
    try {
        const d = new Date(iso);
        if (Number.isNaN(d.getTime())) return "";
        return d.toLocaleString();
    } catch {
        return "";
    }
}

function toPercent(p: number): number {
    if (typeof p !== "number") return 0;
    if (p < 0) return 0;
    if (p > 1) return 100;
    return Math.round(p * 100);
}
</script>

<template>
    <div class="max-w-4xl mx-auto mt-8 px-4">
        <DPageHeader title="Your Skills">
            <DButton variant="secondary" @click="fetchUserSkills" :icon-left="RefreshCw">
                Refresh
            </DButton>
        </DPageHeader>

        <div v-if="loading" class="py-16 text-center">
            <div class="flex items-center justify-center gap-3 text-gray-700">
                <DSpinner />
                <span>Loading your skills…</span>
            </div>
        </div>

        <div v-else-if="error" class="bg-red-50 border border-red-200 text-red-700 rounded-md p-4">
            {{ error }}
        </div>

        <div v-else>
            <div v-if="hasSkills" class="space-y-3">
                <div v-for="s in skills" :key="s.skill_id"
                    class="bg-white p-4 rounded-lg shadow border border-gray-200">
                    <div class="flex items-center justify-between mb-2">
                        <div class="font-medium truncate">{{ s.skill_name }}</div>
                        <div class="text-sm text-gray-600 tabular-nums">{{ toPercent(s.progress) }}%</div>
                    </div>

                    <div class="w-full bg-gray-100 rounded h-3 overflow-hidden">
                        <div class="bg-blue-600 h-3" :style="{ width: toPercent(s.progress) + '%' }"></div>
                    </div>

                    <div class="mt-2 text-xs text-gray-500">Updated {{ formatUpdatedAt(s.updated_at) }}</div>
                </div>
            </div>

            <div v-else class="bg-white p-8 rounded-lg shadow text-center text-gray-600">
                You don't have any skills yet.
            </div>
        </div>
    </div>
</template>
