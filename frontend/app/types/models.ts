import type { tasks, users, courses } from "~~/server/database/schema"

export type Task = typeof tasks.$inferSelect
export type User = typeof users.$inferSelect
export type Course = typeof courses.$inferSelect

export type NewTaskForm = typeof tasks.$inferInsert
export type NewCourseForm = typeof courses.$inferInsert