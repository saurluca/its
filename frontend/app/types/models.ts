// Task type matching backend API structure
export interface Task {
  id: string;
  type: "true_false" | "multiple_choice" | "free_text";
  question: string;
  options?: string[];
  correct_answer: string;
  course_id?: string;
  document_id?: string;
  chunk_id?: string;
  organisationId?: string;
  created_at: Date;
  updated_at: Date;
  deletedAt?: Date | null;
}

// User type
export interface User {
  id: string;
  name: string;
  role: "admin" | "user";
  email: string;
  organisationId?: string;
  createdAt: Date;
  updatedAt: Date;
  deletedAt?: Date | null;
}

// Course type
export interface Course {
  id: string;
  name: string;
  organisationId?: string;
  createdAt: Date;
  updatedAt: Date;
  deletedAt?: Date | null;
}

// Form types for creating new entities
export interface NewTaskForm {
  type: "true_false" | "multiple_choice" | "free_text";
  question: string;
  options?: string[];
  correct_answer: string;
  course_id?: string;
  document_id?: string;
  chunk_id?: string;
}

export interface NewCourseForm {
  name: string;
}
