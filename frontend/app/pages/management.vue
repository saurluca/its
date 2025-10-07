<script setup lang="ts">
import { ref, onMounted } from "vue";
import { UserPlusIcon, TrashIcon, ShieldCheckIcon } from "lucide-vue-next";
import type { RepositoryUser } from "~/types/models";
import { useNotificationsStore } from "~/stores/notifications";

const { $authFetch } = useAuthenticatedFetch();
const route = useRoute();
const notifications = useNotificationsStore();

// Get repository ID from query params
const repositoryId = computed(() => route.query.repositoryId as string);

// State
const users = ref<RepositoryUser[]>([]);
const loading = ref(true);
const repositoryName = ref("");
const currentUserAccessLevel = ref<"read" | "write" | "owner">("read");

// Invite modal state
const showInviteModal = ref(false);
const inviteEmail = ref("");
const inviteAccessLevel = ref<"read" | "write">("read");

// Remove user modal state
const showRemoveModal = ref(false);
const removeUserId = ref<string | null>(null);
const removeUserEmail = ref<string | null>(null);

// Load repository and users
onMounted(async () => {
    if (!repositoryId.value) {
        notifications.error("No repository selected");
        navigateTo("/");
        return;
    }
    await fetchRepositoryDetails();
    await fetchUsers();
});

async function fetchRepositoryDetails() {
    try {
        const response = await $authFetch(`/repositories/${repositoryId.value}`) as {
            name: string;
            access_level?: "read" | "write" | "owner"
        };
        repositoryName.value = response.name;
        currentUserAccessLevel.value = response.access_level || "read";

        // Check if user has write or owner access
        if (currentUserAccessLevel.value === "read") {
            notifications.error("You don't have permission to manage users");
            navigateTo("/");
        }
    } catch (error) {
        console.error("Error fetching repository:", error);
        notifications.error("Failed to load repository. " + error);
        navigateTo("/");
    }
}

async function fetchUsers() {
    loading.value = true;
    try {
        const response = await $authFetch(`/repositories/${repositoryId.value}/users`) as RepositoryUser[];
        users.value = response;
    } catch (error) {
        console.error("Error fetching users:", error);
        notifications.error("Failed to load users. " + error);
    } finally {
        loading.value = false;
    }
}

// Change user access level (toggle between read and write)
async function toggleUserAccess(user: RepositoryUser) {
    if (user.is_owner) return;

    const newAccessLevel = user.access_level === "read" ? "write" : "read";

    try {
        await $authFetch(`/repositories/${repositoryId.value}/access/${user.user_id}`, {
            method: "PUT",
            body: { access_level: newAccessLevel },
        });

        notifications.success(`Updated ${user.email}'s access to ${newAccessLevel}`);
        await fetchUsers();
    } catch (error) {
        console.error("Error updating access:", error);
        notifications.error("Failed to update access. " + error);
    }
}

// Invite user modal functions
function openInviteModal() {
    inviteEmail.value = "";
    inviteAccessLevel.value = "read";
    showInviteModal.value = true;
}

function closeInviteModal() {
    showInviteModal.value = false;
    inviteEmail.value = "";
}

async function confirmInvite() {
    const email = inviteEmail.value.trim();
    if (!email) {
        notifications.warning("Please enter an email address.");
        return;
    }

    try {
        await $authFetch(`/repositories/${repositoryId.value}/access`, {
            method: "POST",
            body: { email, access_level: inviteAccessLevel.value },
        });
        notifications.success("If the user exists, access has been granted.");
        closeInviteModal();
        await fetchUsers();
    } catch (error) {
        console.error("Error granting access:", error);
        notifications.error("Failed to grant access. Please try again.");
    }
}

// Remove user modal functions
function openRemoveModal(user: RepositoryUser) {
    removeUserId.value = user.user_id;
    removeUserEmail.value = user.email;
    showRemoveModal.value = true;
}

function closeRemoveModal() {
    showRemoveModal.value = false;
    removeUserId.value = null;
    removeUserEmail.value = null;
}

async function confirmRemove() {
    if (!removeUserId.value) return;

    try {
        await $authFetch(`/repositories/${repositoryId.value}/access/${removeUserId.value}`, {
            method: "DELETE",
        });
        notifications.success("User access removed.");
        closeRemoveModal();
        await fetchUsers();
    } catch (error) {
        console.error("Error removing access:", error);
        notifications.error("Failed to remove access. " + error);
    }
}

function canManageUser(user: RepositoryUser): boolean {
    // Owner can manage everyone except themselves
    // Write users cannot manage anyone
    return currentUserAccessLevel.value === "owner" && !user.is_owner;
}

function formatDate(dateString: Date): string {
    const date = new Date(dateString);
    return date.toLocaleDateString();
}

function goBack() {
    navigateTo("/");
}
</script>

<template>
    <div class="h-full flex">
        <div class="w-full mt-8">
            <div class="max-w-4xl mx-auto">
                <DPageHeader :title="`Manage Users: ${repositoryName}`" />

                <div class="mb-4">
                    <DButton @click="goBack" variant="secondary">
                        ← Back to Repositories
                    </DButton>
                </div>

                <div v-if="loading" class="py-20 text-center">
                    <div class="text-xl">Loading users...</div>
                </div>

                <div v-else class="space-y-6">
                    <div class="flex flex-col gap-3 mr-4">
                        <DButtonLabelled v-if="currentUserAccessLevel === 'owner'" title="Invite User"
                            :icon="UserPlusIcon" @click="openInviteModal">
                            Grant repository access to a user by email
                        </DButtonLabelled>
                        <div class="border-t border-gray-200"></div>
                    </div>

                    <div v-if="users.length > 0" class="space-y-3">
                        <div v-for="user in users" :key="user.user_id"
                            class="bg-white p-4 rounded-lg shadow border border-gray-200">
                            <div class="flex justify-between items-center">
                                <div class="flex flex-col">
                                    <div class="flex items-center gap-2">
                                        <h3 class="text-lg font-medium">
                                            {{ user.email || 'No email' }}
                                        </h3>
                                        <span :class="{
                                            'bg-purple-100 text-purple-800': user.access_level === 'owner',
                                            'bg-blue-100 text-blue-800': user.access_level === 'write',
                                            'bg-gray-100 text-gray-800': user.access_level === 'read'
                                        }" class="px-2 py-1 rounded text-xs font-semibold uppercase">
                                            {{ user.access_level }}
                                        </span>
                                    </div>
                                    <span v-if="user.full_name" class="text-sm text-gray-600">
                                        {{ user.full_name }}
                                    </span>
                                    <span class="text-xs text-gray-500">
                                        Access granted: {{ formatDate(user.granted_at) }}
                                    </span>
                                </div>

                                <div class="flex gap-2">
                                    <!-- Toggle access button (only for non-owners, only if current user is owner) -->
                                    <DButton v-if="canManageUser(user) && !user.is_owner"
                                        @click="toggleUserAccess(user)"
                                        :variant="user.access_level === 'read' ? 'tertiary' : 'secondary'"
                                        :icon-left="ShieldCheckIcon">
                                        {{ user.access_level === 'read' ? 'Grant Write' : 'Revoke Write' }}
                                    </DButton>

                                    <!-- Remove user button (only for non-owners, only if current user is owner) -->
                                    <DButton v-if="canManageUser(user)" @click="openRemoveModal(user)"
                                        variant="danger-light" :icon-left="TrashIcon">

                                    </DButton>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div v-else class="bg-white p-6 rounded-lg shadow text-center">
                        <p class="text-gray-500">No users found.</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Invite User Modal -->
        <DModal v-if="showInviteModal" titel="Invite User" confirm-text="Invite" @close="closeInviteModal"
            @confirm="confirmInvite">
            <div class="p-4 space-y-4">
                <div>
                    <label for="invite-email" class="block mb-2 font-medium">User Email</label>
                    <input id="invite-email" type="email" v-model="inviteEmail"
                        class="w-full border rounded px-3 py-2 text-sm border-gray-200" placeholder="name@example.com"
                        @keyup.enter="confirmInvite" />
                </div>
                <div>
                    <label class="block mb-2 font-medium">Access Level</label>
                    <div class="flex gap-4 text-sm">
                        <label class="inline-flex items-center gap-2 cursor-pointer">
                            <input type="radio" value="read" v-model="inviteAccessLevel" class="accent-black"
                                style="accent-color: black;" />
                            <span>Read</span>
                        </label>
                        <label class="inline-flex items-center gap-2 cursor-pointer">
                            <input type="radio" value="write" v-model="inviteAccessLevel" class="accent-black"
                                style="accent-color: black;" />
                            <span>Write</span>
                        </label>
                    </div>
                    <p class="text-xs text-gray-500 mt-1">
                        Only the owner can manage user access.
                    </p>
                </div>
            </div>
        </DModal>

        <!-- Remove User Modal -->
        <DModal v-if="showRemoveModal" titel="Remove User Access" confirm-text="Remove" @close="closeRemoveModal"
            @confirm="confirmRemove">
            <div class="p-4">
                <p>
                    Are you sure you want to remove access for "{{ removeUserEmail }}"?
                </p>
                <p class="mt-2 text-sm text-gray-500">
                    They will no longer be able to access this repository.
                </p>
            </div>
        </DModal>
    </div>
</template>
