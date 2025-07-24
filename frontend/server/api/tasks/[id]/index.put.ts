import { tasks } from "~~/server/database/schema"
import { and, eq } from "drizzle-orm"
import { z } from "zod"

const taskUpdateSchema = z.object({
    name: z.string().min(1).optional(),
    type: z.enum(["true_false", "multiple_choice", "free_text"]).optional(),
    courseId: z.string().uuid().optional(),
    skillId: z.string().uuid().optional(),
})

export default defineEventHandler(async (event) => {
    const { secure } = await requireUserSession(event)
    if (!secure) throw createError({ statusCode: 401, message: "Unauthorized" })

    const taskId = getRouterParam(event, "id")
    if (!taskId) throw createError({ statusCode: 404, message: "Task not found" })

    try {
        const body = await readBody(event)
        const validatedData = taskUpdateSchema.parse(body)

        const [updatedTask] = await useDrizzle()
            .update(tasks)
            .set({
                ...validatedData,
                updatedAt: new Date(),
            })
            .where(and(eq(tasks.id, taskId), eq(tasks.organisationId, secure.organisationId)))
            .returning()

        if (!updatedTask) throw createError({ statusCode: 404, message: "Task not found" })

        return updatedTask
    } catch (error) {
        console.error(error)
        throw createError({ statusCode: 400, message: "Invalid request body" })
    }
}) 