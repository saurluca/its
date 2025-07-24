import type { tasks, users, courses, skills } from "~~/server/database/schema"

export type Task = typeof tasks.$inferSelect
export type User = typeof users.$inferSelect
export type Course = typeof courses.$inferSelect
export type Skill = typeof skills.$inferSelect

export type NewTaskForm = typeof tasks.$inferInsert
export type NewCourseForm = typeof courses.$inferInsert
export type NewSkillForm = typeof skills.$inferInsert