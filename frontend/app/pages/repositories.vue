<script setup lang="ts">
import { ref, onMounted } from "vue";
import { PlusIcon } from "lucide-vue-next";
import type { Repository } from "~/types/models";

const { $authFetch } = useAuthenticatedFetch();

// View state
const repositories = ref<Repository[]>([]);
const loading = ref(true);
const showForm = ref(false);
const editingRepository = ref<Repository | null>(null);

// Load repositories on component mount
onMounted(async () => {
    await fetchRepositories();
});

async function fetchRepositories() {
    loading.value = true;
    try {
        console.log("fetching repositories");
        const response = await $authFetch("/repositories/");
        console.log("response", response);
        repositories.value = response.repositories || response;
    } catch (error) {
        console.error("Error fetching repositories:", error);
        alert("Failed to load repositories. Please try again. " + error);
    } finally {
        loading.value = false;
    }
}

async function createRepository(repositoryData: Partial<Repository>) {
    try {
        const newRepository = await $authFetch("/repositories/", {
            method: "POST",
            body: repositoryData,
        });

        repositories.value.push(newRepository);
        showForm.value = false;
    } catch (error) {
        console.error("Error creating repository:", error);
        alert("Failed to create repository. Please try again. " + error);
    }
}

async function updateRepository(repositoryData: Repository) {
    try {
        const updatedRepository = await $authFetch(`/repositories/${repositoryData.id}/`, {
            method: "PUT",
            body: repositoryData,
        });

        const index = repositories.value.findIndex((r) => r.id === updatedRepository.id);
        if (index !== -1) {
            repositories.value[index] = updatedRepository;
        }

        editingRepository.value = null;
    } catch (error) {
        console.error("Error updating repository:", error);
        alert("Failed to update repository. Please try again. " + error);
    }
}

async function deleteRepository(id: string) {
    try {
        await $authFetch(`/repositories/${id}/`, {
            method: "DELETE",
        });

        repositories.value = repositories.value.filter((r) => r.id !== id);
    } catch (error) {
        console.error("Error deleting repository:", error);
        alert("Failed to delete repository. Please try again. " + error);
    }
}

function handleSave(repositoryData: Partial<Repository>) {
    if (editingRepository.value) {
        updateRepository({ ...editingRepository.value, ...repositoryData });
    } else {
        createRepository(repositoryData);
    }
}

function editRepository(repository: Repository) {
    editingRepository.value = repository;
    showForm.value = true;
}

function cancelEdit() {
    editingRepository.value = null;
    showForm.value = false;
}
</script>

<template>
    <div class="max-w-6xl mx-auto px-4 py-8">
        <div class="flex justify-between items-center mb-8">
            <h1 class="text-3xl font-bold">Repositories</h1>
        </div>

        <div v-if="loading" class="py-20 text-center">
            <div class="text-xl">Loading repositories...</div>
        </div>

        <div v-else class="space-y-8">
            <div v-if="!showForm" class="flex">
                <DButton @click="showForm = true" variant="primary" :iconLeft="PlusIcon">
                    New Repository
                </DButton>
            </div>

            <DItemForm v-if="showForm" :title="editingRepository ? 'Edit Repository' : 'Create New Repository'"
                :item="editingRepository || undefined" :is-edit="!!editingRepository" @save="handleSave"
                @cancel="cancelEdit" />

            <div v-if="repositories.length > 0" class="space-y-4">
                <DItemCard v-for="repository in repositories" :key="repository.id" :item="repository"
                    @delete="deleteRepository" @edit="editRepository" />
            </div>

            <div v-else class="bg-white p-6 rounded-lg shadow text-center">
                <p class="text-gray-500">No repositories have been created yet.</p>
            </div>
        </div>
    </div>
</template>