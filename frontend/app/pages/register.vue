<script setup lang="ts">
definePageMeta({
  layout: "minimal",
});

const name = ref("");
const email = ref("");
const password = ref("");

const authStore = useAuthStore();

// Sleep utility function
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const success = ref(false);
const loading = ref(false);
const errorMsg = ref("");
const showConsentModal = ref(false);
const consentGiven = ref(false);

async function register() {
  try {
    loading.value = true;
    errorMsg.value = "";

    const result = await authStore.register({
      email: email.value,
      password: password.value,
      full_name: email.value,
    });

    if (result.success) {
      success.value = true;
      await sleep(1000);
      navigateTo("/login");
    } else {
      errorMsg.value = result.error || "Registration failed";
    }
  } catch {
    errorMsg.value = "Registration failed";
  } finally {
    loading.value = false;
  }
}

function handleRegisterClick() {
  if (!consentGiven.value) {
    showConsentModal.value = true;
  } else {
    register();
  }
}

function handleConsentAccepted() {
  consentGiven.value = true;
  showConsentModal.value = false;
  register();
}

function handleConsentCancelled() {
  showConsentModal.value = false;
}
</script>

<template>
  <div class="h-full px-8 pt-24">
    <div class="mx-auto max-w-sm rounded-lg border border-gray-50 bg-white p-8 shadow">
      <h1 class="mb-4 text-center text-2xl font-semibold text-gray-900">ITS</h1>

      <div v-if="success" class="mb-4 rounded-md bg-green-100 px-4 py-3 text-center">
        <h2 class="font-medium text-green-800">Registration Successful</h2>
        <!-- <p class="text-sm text-green-700">Please check your email for a confirmation link.</p> -->
        <p class="text-sm text-green-700">You will be redirected shortly...</p>
      </div>

      <form v-else class="flex flex-col gap-4">
        <div class="flex flex-col gap-1">
          <d-label for="email">Email</d-label>
          <d-input v-model="email" type="email" id="email" name="email" required placeholder="Your email address" />
        </div>

        <div class="flex flex-col gap-1">
          <d-label for="password">Password</d-label>
          <d-input v-model="password" type="password" id="password" name="password" required
            placeholder="Your password" />
        </div>

        <div class="flex flex-col gap-2">
          <DButton :loading="loading" @click="handleRegisterClick" text-center>Register</DButton>
          <DButton to="/login" variant="secondary" text-center>Already registered? Login</DButton>
        </div>

        <div v-if="errorMsg" class="mb-2 rounded-md bg-red-100 px-4 py-2 text-center text-sm text-red-600">
          {{ errorMsg }}
        </div>
      </form>
    </div>

    <!-- Consent Modal -->
    <ConsentModal v-if="showConsentModal" titel="Information and Consent Form" confirm-text="Accept and Register"
      @close="handleConsentCancelled" @confirm="handleConsentAccepted" />
  </div>
</template>
