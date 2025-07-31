<script setup lang="ts">
import { EyeIcon, SendIcon, ChevronRightIcon } from 'lucide-vue-next'

// Mock data for the bar chart
const chartData = [
  { city: 'New York', vodka: 15, wine: 12, peanuts: 8, water: 5, sandwich: 10 },
  { city: 'Las Vegas', vodka: 18, wine: 14, peanuts: 6, water: 4, sandwich: 12 },
  { city: 'Honolulu', vodka: 12, wine: 10, peanuts: 9, water: 7, sandwich: 8 },
  { city: 'Atlanta', vodka: 14, wine: 11, peanuts: 7, water: 6, sandwich: 9 },
  { city: 'Boston', vodka: 16, wine: 13, peanuts: 8, water: 5, sandwich: 11 },
  { city: 'Washington D.C.', vodka: 17, wine: 15, peanuts: 6, water: 4, sandwich: 13 },
  { city: 'Chicago', vodka: 13, wine: 9, peanuts: 10, water: 8, sandwich: 7 },
  { city: 'Orlando', vodka: 11, wine: 8, peanuts: 12, water: 9, sandwich: 6 },
  { city: 'San Francisco', vodka: 19, wine: 16, peanuts: 5, water: 3, sandwich: 14 },
  { city: 'Seattle', vodka: 10, wine: 7, peanuts: 11, water: 10, sandwich: 5 }
]

// Mock skill data
const skillData = [
  { skill: 'Data Analysis', current: 75, relevant: 85 },
  { skill: 'Critical Thinking', current: 60, relevant: 90 },
  { skill: 'Problem Solving', current: 70, relevant: 80 },
  { skill: 'Statistical Reasoning', current: 65, relevant: 75 }
]

// Reactive state
const currentQuestion = ref(0)
const answers = ref({
  multipleChoice1: '',
  multipleChoice2: '',
  freeText: ''
})
const showHint = ref(false)
const hintStep = ref(0)
const chatMessage = ref('')
const chatHistory = ref([
  { sender: 'tutor', message: 'Do you have additional questions about this task?', timestamp: new Date() }
])

const questions = [
  {
    type: 'multiple-choice',
    question: 'In which city is the cost of soda highest?',
    options: ['Las Vegas', 'NYC', 'Washington D.C.', 'Not Sure']
  },
  {
    type: 'multiple-choice',
    question: 'Which city has the highest total room service cost?',
    options: ['San Francisco', 'New York', 'Las Vegas', 'Washington D.C.']
  },
  {
    type: 'free-text',
    question: 'Describe the graph above and summarize its main insights in 100-150 words.'
  }
]

const hints = [
  'Phasor diagrams present a graphical representation, plotted on a coordinate system, of the phase relationship between the voltages and currents within passive components or a whole circuit.',
  'To analyze this data effectively, start by identifying the highest and lowest values for each category.',
  'Consider the relationship between different room service items and their costs across cities.'
]

// Methods
const submitAnswer = () => {
  if (currentQuestion.value < questions.length - 1) {
    currentQuestion.value++
  } else {
    // All questions answered
    console.log('All questions completed')
  }
}

const requestHint = () => {
  showHint.value = true
  hintStep.value = 0
}

const nextHint = () => {
  if (hintStep.value < hints.length - 1) {
    hintStep.value++
  }
}

const sendChatMessage = () => {
  if (chatMessage.value.trim()) {
    chatHistory.value.push({
      sender: 'user',
      message: chatMessage.value,
      timestamp: new Date()
    })
    chatMessage.value = ''
    
    // Simulate tutor response
    setTimeout(() => {
      chatHistory.value.push({
        sender: 'tutor',
        message: 'I understand your question. Let me help you analyze this data more effectively.',
        timestamp: new Date()
      })
    }, 1000)
  }
}

// Computed
const maxValue = computed(() => {
  return Math.max(...chartData.map(item => 
    item.vodka + item.wine + item.peanuts + item.water + item.sandwich
  ))
})

const getBarHeight = (value: number) => {
  return (value / maxValue.value) * 200
}

// definePageMeta({
//   layout: "minimal",
// });
</script>

<template>
  <div class="h-full bg-gray-50 p-4">
    <div class="h-full">
      <div class="grid grid-cols-2 gap-4 h-[calc(100vh-120px)]">
        <!-- Top Left - Chart and Questions -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 overflow-y-auto">
          <!-- Chart -->
          <div class="mb-6">
            <h2 class="text-xl font-semibold text-gray-900 mb-4">Hotel Costs of Room Service</h2>
            <div class="relative h-64">
              <div class="flex items-end justify-between h-48 space-x-2">
                <div 
                  v-for="(item, index) in chartData" 
                  :key="index"
                  class="flex-1 flex flex-col items-center"
                >
                  <div class="relative w-full h-48 flex items-end">
                    <!-- Stacked bars -->
                    <div class="absolute bottom-0 w-full h-full flex flex-col-reverse">
                      <div class="h-1/5 bg-purple-500" :style="{ height: `${(item.vodka / maxValue) * 100}%` }"></div>
                      <div class="h-1/5 bg-orange-500" :style="{ height: `${(item.wine / maxValue) * 100}%` }"></div>
                      <div class="h-1/5 bg-red-500" :style="{ height: `${(item.peanuts / maxValue) * 100}%` }"></div>
                      <div class="h-1/5 bg-green-500" :style="{ height: `${(item.water / maxValue) * 100}%` }"></div>
                      <div class="h-1/5 bg-blue-500" :style="{ height: `${(item.sandwich / maxValue) * 100}%` }"></div>
                    </div>
                  </div>
                  <div class="text-xs text-gray-600 mt-2 text-center">
                    {{ item.city }}
                  </div>
                </div>
              </div>
              <!-- Legend -->
              <div class="flex justify-center mt-4 space-x-4 text-xs">
                <div class="flex items-center space-x-1">
                  <div class="w-3 h-3 bg-purple-500"></div>
                  <span>Vodka</span>
                </div>
                <div class="flex items-center space-x-1">
                  <div class="w-3 h-3 bg-orange-500"></div>
                  <span>Wine</span>
                </div>
                <div class="flex items-center space-x-1">
                  <div class="w-3 h-3 bg-red-500"></div>
                  <span>Peanuts</span>
                </div>
                <div class="flex items-center space-x-1">
                  <div class="w-3 h-3 bg-green-500"></div>
                  <span>Water</span>
                </div>
                <div class="flex items-center space-x-1">
                  <div class="w-3 h-3 bg-blue-500"></div>
                  <span>Sandwich</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Questions -->
          <div v-if="currentQuestion < questions.length" class="space-y-4">
            <div v-if="questions[currentQuestion].type === 'multiple-choice'">
              <h3 class="text-lg font-medium text-gray-900 mb-3">
                {{ questions[currentQuestion].question }}
              </h3>
              <div class="space-y-2">
                <label 
                  v-for="option in questions[currentQuestion].options" 
                  :key="option"
                  class="flex items-center space-x-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer"
                >
                  <input 
                    type="radio" 
                    :name="`question-${currentQuestion}`"
                    :value="option"
                    v-model="answers[`multipleChoice${currentQuestion + 1}`]"
                    class="text-blue-600"
                  />
                  <span class="text-gray-700">{{ option }}</span>
                </label>
              </div>
            </div>

            <div v-else-if="questions[currentQuestion].type === 'free-text'">
              <h3 class="text-lg font-medium text-gray-900 mb-3">
                {{ questions[currentQuestion].question }}
              </h3>
              <textarea
                v-model="answers.freeText"
                placeholder="Write your answer here..."
                class="w-full h-32 p-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              ></textarea>
            </div>

            <button
              @click="submitAnswer"
              class="w-full bg-teal-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-teal-700 transition-colors"
            >
              Done
            </button>
          </div>
        </div>

                <!-- Bottom Right - Chat with Tutor -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 flex flex-col">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">Chat with the tutor</h2>
          
          <div class="flex items-center space-x-2 mb-4 p-3 bg-gray-50 rounded-lg">
            <EyeIcon class="w-4 h-4 text-gray-500" />
            <span class="text-xs text-gray-600">
              In order to answer your questions, the tutor is connected to the task space and collects rich interaction data. Additionally, all your conversations with the chat is recorded and used to support you in future tasks.
            </span>
          </div>

          <!-- Chat Messages -->
          <div class="space-y-3 mb-4 flex-1 overflow-y-auto min-h-0">
            <div 
              v-for="(message, index) in chatHistory" 
              :key="index"
              :class="[
                'flex',
                message.sender === 'user' ? 'justify-end' : 'justify-start'
              ]"
            >
              <div 
                :class="[
                  'max-w-xs px-4 py-2 rounded-lg text-sm',
                  message.sender === 'user' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-teal-100 text-gray-800'
                ]"
              >
                {{ message.message }}
              </div>
            </div>
          </div>

          <!-- Chat Input -->
          <div class="flex space-x-2">
            <input
              v-model="chatMessage"
              @keyup.enter="sendChatMessage"
              type="text"
              placeholder="Type your question..."
              class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <button
              @click="sendChatMessage"
              class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <SendIcon class="w-4 h-4" />
            </button>
          </div>
        </div>

        <!-- Top Right - Skill Evaluation -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 overflow-y-auto">
          <h2 class="text-lg font-semibold text-gray-900 mb-4">Skill evaluation</h2>
          
          <div class="space-y-4">
            <div v-for="skill in skillData" :key="skill.skill" class="space-y-2">
              <div class="flex justify-between text-sm">
                <span class="text-gray-700">{{ skill.skill }}</span>
                <span class="text-gray-500">{{ skill.current }}% / {{ skill.relevant }}%</span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-2">
                <div 
                  class="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  :style="{ width: `${skill.current}%` }"
                ></div>
              </div>
            </div>
          </div>

          <div class="flex items-center space-x-2 mt-4 p-3 bg-gray-50 rounded-lg">
            <EyeIcon class="w-4 h-4 text-gray-500" />
            <span class="text-xs text-gray-600">
              Skill feedback is provided based on your performance on the task (i.e., the correctness of your answers). If you prefer this data not to be collected, please choose Level 1 in the tutor settings.
            </span>
          </div>
        </div>



        <!-- Bottom Left - Hint Tutor -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 overflow-y-auto">
          <div class="flex items-center space-x-2 mb-4">
            <EyeIcon class="w-5 h-5 text-gray-500" />
            <span class="text-sm text-gray-600">
              This hint is provided based on the task you are currently solving. It is not related to your previous answers and performance while solving tasks.
            </span>
          </div>

          <div v-if="showHint" class="mb-4">
            <h3 class="text-lg font-medium text-gray-900 mb-2">
              Hint {{ hintStep + 1 }}/{{ hints.length }}
            </h3>
            <p class="text-gray-700 bg-yellow-50 p-4 rounded-lg border border-yellow-200">
              {{ hints[hintStep] }}
            </p>
            
            <div class="flex space-x-2 mt-4">
              <button
                v-for="(hint, index) in hints"
                :key="index"
                @click="hintStep = index"
                class="px-4 py-2 bg-yellow-500 text-white rounded-lg text-sm hover:bg-yellow-600 transition-colors"
              >
                {{ index === 0 ? 'Theory' : index === 1 ? 'Procedure' : 'Tell me the next step' }}
              </button>
            </div>
          </div>

          <button
            @click="requestHint"
            class="w-full bg-yellow-500 text-white py-3 px-6 rounded-lg font-medium hover:bg-yellow-600 transition-colors"
          >
            I need a hint
          </button>
        </div>


      </div>
    </div>
  </div>
</template>