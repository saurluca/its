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

// User type matching backend API structure
export interface User {
  id: string;
  username: string;
  email?: string;
  full_name?: string;
  disabled: boolean;
  created_at: Date;
  updated_at: Date;
}

// Course type matching backend API structure
export interface Course {
  id: string;
  name: string;
  organisationId?: string;
  created_at: Date;
  updated_at: Date;
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

// User creation form matching backend UserCreate schema
export interface UserCreateForm {
  username: string;
  email?: string;
  full_name?: string;
  password: string;
}

// User update form matching backend UserUpdate schema
export interface UserUpdateForm {
  username?: string;
  email?: string;
  full_name?: string;
  password?: string;
  disabled?: boolean;
}
