// Repository type matching backend API structure
export interface Repository {
  id: string;
  name: string;
  created_at: Date;
  deleted_at?: Date | null;
  document_ids?: string[];
  document_names?: string[];
}

// Document type matching backend API structure
export interface Document {
  id: string;
  title: string;
  content?: string;
  created_at: Date;
  deleted_at?: Date | null;
  repository_ids?: string[];
  source_file?: string;
}

// Chunk type matching backend API structure
export interface Chunk {
  id: string;
  content: string;
  document_id: string;
  created_at: Date;
  deleted_at?: Date | null;
}

// Task type matching backend API structure
export interface Task {
  id: string;
  type: "multiple_choice" | "free_text";
  question: string;
  answer_options: AnswerOption[];
  repository_id?: string;
  document_id?: string;
  chunk_id?: string;
  organisationId?: string;
  created_at: Date;
  updated_at: Date;
  deletedAt?: Date | null;
}

// Answer option type matching backend API structure
export interface AnswerOption {
  id: string;
  answer: string;
  is_correct: boolean;
  task_id: string;
}

// User type matching backend API structure
export interface User {
  id: string;
  email: string;
  full_name?: string;
  disabled: boolean;
  created_at: Date;
  updated_at: Date;
}

// Repository creation form
export interface RepositoryCreateForm {
  name: string;
}

// Repository update form
export interface RepositoryUpdateForm {
  name: string;
}

// Document creation form
export interface DocumentCreateForm {
  title: string;
  file?: File;
}

// Task creation form
export interface TaskCreateForm {
  type: "multiple_choice" | "free_text";
  question: string;
  answer_options?: AnswerOption[];
  repository_id?: string;
  document_id?: string;
  chunk_id?: string;
}

// User creation form matching backend UserCreate schema
export interface UserCreateForm {
  email: string;
  full_name?: string;
  password: string;
}

// User update form matching backend UserUpdate schema
export interface UserUpdateForm {
  email: string;
  full_name?: string;
  password?: string;
  disabled?: boolean;
}
