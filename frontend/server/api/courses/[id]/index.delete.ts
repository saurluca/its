import { courses } from "~~/server/database/schema"
import { and, eq } from "drizzle-orm"

export default defineEventHandler(async (event) => {
    const { secure } = await requireUserSession(event)
    if (!secure) throw createError({ statusCode: 401, message: "Unauthorized" })

    const courseId = getRouterParam(event, "id")
    if (!courseId) throw createError({ statusCode: 404, message: "Course not found" })

    const [deletedCourse] = await useDrizzle()
        .delete(courses)
        .where(and(eq(courses.id, courseId), eq(courses.organisationId, secure.organisationId)))
        .returning()

    if (!deletedCourse) throw createError({ statusCode: 404, message: "Course not found" })

    return { success: true, id: deletedCourse.id }
}) 