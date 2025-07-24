import { skills } from "~~/server/database/schema"
import { and, eq } from "drizzle-orm"
import { z } from "zod"

const skillUpdateSchema = z.object({
    name: z.string().min(1).optional(),
    description: z.string().optional(),
    progress: z.number().optional(),
    maxProgress: z.number().optional(),
})

export default defineEventHandler(async (event) => {
    const { secure } = await requireUserSession(event)
    if (!secure) throw createError({ statusCode: 401, message: "Unauthorized" })

    const skillId = getRouterParam(event, "id")
    if (!skillId) throw createError({ statusCode: 404, message: "Skill not found" })

    try {
        const body = await readBody(event)
        const validatedData = skillUpdateSchema.parse(body)

        const [updatedSkill] = await useDrizzle()
            .update(skills)
            .set({
                ...validatedData,
                updatedAt: new Date(),
            })
            .where(and(eq(skills.id, skillId), eq(skills.organisationId, secure.organisationId)))
            .returning()

        if (!updatedSkill) throw createError({ statusCode: 404, message: "Skill not found" })

        return updatedSkill
    } catch (error) {
        console.error(error)
        throw createError({ statusCode: 400, message: "Invalid request body" })
    }
}) 