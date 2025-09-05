<script setup lang="ts">
import { ref } from 'vue'

// Test comment

interface Props {
    titel: string;
    confirmText?: string;
    wide?: boolean;
    disabled?: boolean;
}

withDefaults(defineProps<Props>(), {
    confirmText: "Accept",
    wide: true,
    disabled: false,
});

const emit = defineEmits(["close", "confirm"]);

const consentChecked = ref(false);

function close() {
    emit("close");
}

function accept() {
    if (consentChecked.value) {
        emit("confirm");
    }
}

function handleConsentChange() {
    // This will be called when the checkbox changes
}
</script>

<template>
    <Teleport to="body">
        <div>
            <div class="fixed inset-0 z-50 bg-black/50"></div>
            <div class="fixed inset-0 z-50 overflow-y-auto">
                <div class="flex min-h-full items-center justify-center p-4 ">
                    <div class="max-h-full w-full max-w-4xl">
                        <div class="relative rounded-md bg-white shadow-lg">
                            <div class="flex   rounded-t border-b border-gray-200 px-6 py-4">
                                <h3 class="text-xl font-semibold text-gray-900">{{ titel }}</h3>
                                <button @click="close" class="text-gray-400 hover:text-gray-600">
                                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                            d="M6 18L18 6M6 6l12 12"></path>
                                    </svg>
                                </button>
                            </div>

                            <div class="max-h-[600px] overflow-y-auto px-6 py-4">
                                <!-- Study Information -->
                                <div class="mb-6">
                                    <p class="text-sm text-gray-600 mb-2"><strong>Title:</strong> Development and
                                        Evaluation of an Intelligent Tutoring System</p>
                                    <p class="text-sm text-gray-600 mb-2"><strong>Place and time:</strong> ETH Zurich,
                                        Online Study, 2025</p>
                                    <p class="text-sm text-gray-600 mb-2"><strong>Contact:</strong> Luca Saur, ETH
                                        Zurich, lusaur@ethz.ch</p>
                                    <p class="text-sm text-gray-600 mb-4"><strong>Data Protection Officer:</strong>
                                        Tomislav Mitar (tomislav.mitar@sl.ethz.ch)</p>

                                    <p class="text-gray-700 mb-6">
                                        We would like to ask you if you are willing to participate in our research
                                        project. Your participation is
                                        voluntary. Please read the text below carefully before deciding whether you wish
                                        to take part.
                                    </p>
                                </div>

                                <!-- Study Information Sections -->
                                <div class="space-y-6 mb-8">
                                    <section>
                                        <h4 class="text-base font-medium text-gray-900 mb-2">What is investigated and
                                            how?</h4>
                                        <p class="text-sm text-gray-700 leading-relaxed">
                                            This study investigates how large language models can provide reliable
                                            feedback on short student answers. We
                                            aim to develop and evaluate an intelligent tutoring system that generates
                                            questions based on reference texts
                                            and collects student answers. These anonymised answers will help us to
                                            fine-tune models and improve feedback
                                            quality. The study benefits education by creating a system that can support
                                            teachers and provide students
                                            with personalised learning assistance.
                                        </p>
                                    </section>

                                    <section>
                                        <h4 class="text-base font-medium text-gray-900 mb-2">Who can participate?</h4>
                                        <p class="text-sm text-gray-700 leading-relaxed">
                                            All students and self-learners who voluntarily wish to use the online
                                            tutoring platform may participate.
                                            There are no further exclusion criteria beyond refusal of consent.
                                        </p>
                                    </section>

                                    <section>
                                        <h4 class="text-base font-medium text-gray-900 mb-2">What am I supposed to do as
                                            a participant?</h4>
                                        <p class="text-sm text-gray-700 leading-relaxed">
                                            You will read short excerpts of text and answer automatically generated
                                            short-answer questions on the online
                                            platform. Optionally, you may provide feedback on the usability of the
                                            system. No additional activities are
                                            required.
                                        </p>
                                    </section>

                                    <section>
                                        <h4 class="text-base font-medium text-gray-900 mb-2">What are my rights during
                                            participation?</h4>
                                        <p class="text-sm text-gray-700 leading-relaxed">
                                            Your participation in this study is voluntary. You may withdraw at any time
                                            without giving reasons and
                                            without any disadvantage.
                                        </p>
                                    </section>

                                    <section>
                                        <h4 class="text-base font-medium text-gray-900 mb-2">What risks and benefits can
                                            I expect?</h4>
                                        <p class="text-sm text-gray-700 leading-relaxed">
                                            No physical or psychological risks are expected. The only burden is the time
                                            you choose to spend answering
                                            questions. The potential benefit is contributing to the development of an
                                            improved tutoring system that may
                                            help students receive better feedback in the future.
                                        </p>
                                    </section>

                                    <section>
                                        <h4 class="text-base font-medium text-gray-900 mb-2">Will I be compensated for
                                            my participation?</h4>
                                        <p class="text-sm text-gray-700 leading-relaxed">
                                            You will not receive monetary compensation or other incentives for
                                            participation.
                                        </p>
                                    </section>

                                    <section>
                                        <h4 class="text-base font-medium text-gray-900 mb-2">What data is collected from
                                            me and how is it used?</h4>
                                        <p class="text-sm text-gray-700 leading-relaxed mb-2">
                                            The platform collects only your submitted answers to questions. No names,
                                            email addresses, or other personal
                                            data are collected. The answers are stored anonymously on secure ETH
                                            servers. All data will be anonymised
                                            and cannot be traced back to you. The anonymised dataset may be used for
                                            scientific publications and may be
                                            made available in open research repositories. No conclusions about
                                            individuals can be drawn from any
                                            publication.
                                        </p>
                                        <p class="text-xs text-gray-600 italic mb-2">
                                            <strong>Required note:</strong> Anonymised data may be published for further
                                            use (e.g., in a scientific data repository).
                                        </p>
                                        <p class="text-sm text-gray-700 leading-relaxed">
                                            No non-anonymised data or results will be shared with third parties.
                                        </p>
                                    </section>

                                    <section>
                                        <h4 class="text-base font-medium text-gray-900 mb-2">Who is funding the study?
                                        </h4>
                                        <p class="text-sm text-gray-700 leading-relaxed">
                                            The study is conducted within ETH Zurich. No external industry partners are
                                            involved, and there are no
                                            conflicts of interest.
                                        </p>
                                    </section>

                                    <section>
                                        <h4 class="text-base font-medium text-gray-900 mb-2">Who reviewed the study?
                                        </h4>
                                        <p class="text-sm text-gray-700 leading-relaxed">
                                            This study was reviewed and approved by the ETH Zurich Ethics Committee
                                            under application number
                                            <em>[Insert application number]</em>.
                                        </p>
                                    </section>

                                    <section>
                                        <h4 class="text-base font-medium text-gray-900 mb-2">Complaints office</h4>
                                        <p class="text-sm text-gray-700 leading-relaxed">
                                            If you have complaints regarding your participation in the study, you may
                                            contact the secretariat of the ETH
                                            Zurich Ethics Committee at
                                            <a href="mailto:ethics@sl.ethz.ch"
                                                class="text-gray-900 underline">ethics@sl.ethz.ch</a>
                                            or <a href="tel:+41446328572" class="text-gray-900 underline">+41 44 632 85
                                                72</a>.
                                        </p>
                                    </section>
                                </div>

                                <!-- Consent Form -->
                                <div class="border-t border-gray-200 pt-6 mb-6">
                                    <h4 class="text-lg font-medium text-gray-900 mb-4">Consent Form</h4>

                                    <p class="text-sm text-gray-700 mb-3">By ticking the box below, you confirm that:
                                    </p>
                                    <ul class="text-sm text-gray-700 space-y-1 mb-4 ml-4">
                                        <li>• You have read and understood the study information.</li>
                                        <li>• You had enough time to decide about your participation and are taking part
                                            voluntarily.</li>
                                        <li>• You consent that your answers may be collected and used as described
                                            above.</li>
                                        <li>• You know that the data collected from you may be published in anonymised
                                            form.</li>
                                        <li>• You know that you can cancel your participation at any time.</li>
                                    </ul>

                                    <label class="flex items-center space-x-3 cursor-pointer">
                                        <input v-model="consentChecked" type="checkbox" required
                                            class="w-4 h-4 text-gray-900 border-gray-300 rounded focus:ring-gray-500"
                                            @change="handleConsentChange">
                                        <span class="text-sm text-gray-900 font-medium leading-tight">
                                            I consent to participate in this study.
                                        </span>
                                    </label>
                                </div>
                            </div>

                            <div class="flex justify-end space-x-3 rounded-b border-t border-gray-200 px-6 py-4">
                                <button @click="close"
                                    class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500">
                                    Cancel
                                </button>
                                <button @click="accept" :disabled="!consentChecked"
                                    class="px-4 py-2 text-sm font-medium text-white bg-gray-900 border border-transparent rounded-md hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed">
                                    {{ confirmText }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </Teleport>
</template>
