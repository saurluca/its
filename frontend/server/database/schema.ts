import { pgTable, timestamp, text, primaryKey, uuid, integer } from "drizzle-orm/pg-core"
import { uuidv7 } from "uuidv7"

// Types
export type UserRole = "admin" | "user"
export type TaskType = "true_false" | "multiple_choice" | "free_text"

// Helpers
const timestamps = {
  createdAt: timestamp({ withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp({ withTimezone: true }).notNull().defaultNow(),
  deletedAt: timestamp({ withTimezone: true }),
}

const organisationId = {
  organisationId: uuid()
    .notNull()
    .references(() => organisations.id),
}

export const organisations = pgTable("organisations", {
  id: uuid().primaryKey().$defaultFn(uuidv7),
  name: text().notNull(),
  ...timestamps,
})

// Tables
export const users = pgTable("users", {
  id: uuid().primaryKey().$defaultFn(uuidv7),
  name: text().notNull(),
  role: text().$type<UserRole>().notNull().default("user"),
  email: text().notNull().unique(),
  password: text().notNull(),
  resetPasswordToken: text(),
  resetPasswordExpiresAt: timestamp({ withTimezone: true }),
  ...organisationId,
  ...timestamps,
})

export const sessions = pgTable(
  "sessions",
  {
    token: text().notNull().unique(),
    userId: uuid()
      .notNull()
      .references(() => users.id),
    ...timestamps,
  },
  (t: any) => [primaryKey({ columns: [t.token, t.userId] })],
)

export const skills = pgTable("skills", {
  id: uuid().primaryKey().$defaultFn(uuidv7),
  name: text().notNull(),
  description: text(),
  progress: integer().default(0),
  maxProgress: integer().default(100),
  ...organisationId,
  ...timestamps,
})

export const courses = pgTable("courses", {
  id: uuid().primaryKey().$defaultFn(uuidv7),
  name: text().notNull(),
  ...organisationId,
  ...timestamps,
})

export const tasks = pgTable("tasks", {
  id: uuid().primaryKey().$defaultFn(uuidv7),
  name: text().notNull(),
  type: text().$type<TaskType>().notNull(),
  question: text().notNull(),
  options: text().array(),
  correctAnswer: text().notNull(),
  courseId: uuid()
    .notNull()
    .references(() => courses.id),
  skillId: uuid()
    .notNull()
    .references(() => skills.id),
  ...organisationId,
  ...timestamps,
})

