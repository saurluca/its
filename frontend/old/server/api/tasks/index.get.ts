import { tasks } from "../../database/schema"
import { eq } from "drizzle-orm"

export default defineEventHandler(async (event) => {
    const { secure } = await requireUserSession(event)
    if (!secure) throw createError({ statusCode: 401, message: "Unauthorized" })

    return await useDrizzle().select().from(tasks).where(eq(tasks.organisationId, secure.organisationId)).limit(100)
}) 