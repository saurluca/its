import { courses } from "~~/server/database/schema"
import { and, eq } from "drizzle-orm"
import { z } from "zod"

const courseUpdateSchema = z.object({
    name: z.string().min(1).optional(),
})

export default defineEventHandler(async (event) => {
    const { secure } = await requireUserSession(event)
    if (!secure) throw createError({ statusCode: 401, message: "Unauthorized" })

    const courseId = getRouterParam(event, "id")
    if (!courseId) throw createError({ statusCode: 404, message: "Course not found" })

    try {
        const body = await readBody(event)
        const validatedData = courseUpdateSchema.parse(body)

        const [updatedCourse] = await useDrizzle()
            .update(courses)
            .set({
                ...validatedData,
                updatedAt: new Date(),
            })
            .where(and(eq(courses.id, courseId), eq(courses.organisationId, secure.organisationId)))
            .returning()

        if (!updatedCourse) throw createError({ statusCode: 404, message: "Course not found" })

        return updatedCourse
    } catch (error) {
        console.error(error)
        throw createError({ statusCode: 400, message: "Invalid request body" })
    }
}) 