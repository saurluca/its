import { tasks } from "~~/server/database/schema"
import { and, eq } from "drizzle-orm"

export default defineEventHandler(async (event) => {
    const { secure } = await requireUserSession(event)
    if (!secure) throw createError({ statusCode: 401, message: "Unauthorized" })

    const taskId = getRouterParam(event, "id")
    if (!taskId) throw createError({ statusCode: 404, message: "Task not found" })

    const [deletedTask] = await useDrizzle()
        .delete(tasks)
        .where(and(eq(tasks.id, taskId), eq(tasks.organisationId, secure.organisationId)))
        .returning()

    if (!deletedTask) throw createError({ statusCode: 404, message: "Task not found" })

    return { success: true, id: deletedTask.id }
}) 