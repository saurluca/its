import { tasks } from "../../database/schema"
import { z } from "zod"

const taskSchema = z.object({
    name: z.string().min(1),
    type: z.enum(["true_false", "multiple_choice", "free_text"]),
    question: z.string().min(1),
    options: z.array(z.string()).optional(),
    correctAnswer: z.string().min(1),
    courseId: z.string().uuid(),
    skillId: z.string().uuid(),
})

export default defineEventHandler(async (event) => {
    const { secure } = await requireUserSession(event)
    if (!secure) throw createError({ statusCode: 401, message: "Unauthorized" })

    try {
        const body = await readBody(event)
        const validatedData = taskSchema.parse(body)

        const [createdTask] = await useDrizzle()
            .insert(tasks)
            .values({
                name: validatedData.name,
                type: validatedData.type,
                question: validatedData.question,
                options: validatedData.options,
                correctAnswer: validatedData.correctAnswer,
                courseId: validatedData.courseId,
                skillId: validatedData.skillId,
                organisationId: secure.organisationId,
            })
            .returning()

        return createdTask
    } catch (error) {
        console.error(error)
        throw createError({ statusCode: 400, message: "Invalid request body" })
    }
}) 