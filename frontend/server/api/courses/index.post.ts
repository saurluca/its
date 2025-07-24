import { courses } from "../../database/schema"
import { z } from "zod"

const courseSchema = z.object({
    name: z.string().min(1),
})

export default defineEventHandler(async (event) => {
    const { secure } = await requireUserSession(event)
    if (!secure) throw createError({ statusCode: 401, message: "Unauthorized" })

    try {
        const body = await readBody(event)
        const validatedData = courseSchema.parse(body)

        const [createdCourse] = await useDrizzle()
            .insert(courses)
            .values({
                name: validatedData.name,
                organisationId: secure.organisationId,
            })
            .returning()

        return createdCourse
    } catch (error) {
        console.error(error)
        throw createError({ statusCode: 400, message: "Invalid request body" })
    }
}) 