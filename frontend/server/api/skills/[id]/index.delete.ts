import { skills } from "~~/server/database/schema"
import { and, eq } from "drizzle-orm"

export default defineEventHandler(async (event) => {
    const { secure } = await requireUserSession(event)
    if (!secure) throw createError({ statusCode: 401, message: "Unauthorized" })

    const skillId = getRouterParam(event, "id")
    if (!skillId) throw createError({ statusCode: 404, message: "Skill not found" })

    const [deletedSkill] = await useDrizzle()
        .delete(skills)
        .where(and(eq(skills.id, skillId), eq(skills.organisationId, secure.organisationId)))
        .returning()

    if (!deletedSkill) throw createError({ statusCode: 404, message: "Skill not found" })

    return { success: true, id: deletedSkill.id }
}) 