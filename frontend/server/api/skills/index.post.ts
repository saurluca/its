import { skills } from "../../database/schema"
import { z } from "zod"

const skillSchema = z.object({
    name: z.string().min(1),
    description: z.string().optional(),
    progress: z.number().optional(),
})

export default defineEventHandler(async (event) => {
    const { secure } = await requireUserSession(event)
    if (!secure) throw createError({ statusCode: 401, message: "Unauthorized" })

    try {
        const body = await readBody(event)
        const validatedData = skillSchema.parse(body)

        const [createdSkill] = await useDrizzle()
            .insert(skills)
            .values({
                name: validatedData.name,
                description: validatedData.description,
                progress: validatedData.progress,
                organisationId: secure.organisationId,
            })
            .returning()

        return createdSkill
    } catch (error) {
        console.error(error)
        throw createError({ statusCode: 400, message: "Invalid request body" })
    }
}) 