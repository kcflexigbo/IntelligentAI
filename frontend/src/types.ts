export interface AuthContextType {
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}
export interface ChatMessage {
  id: number;
  sender: 'user' | 'ai';
  text: string;
}
export interface ChatApiResponse {
  answer: string;
  retrieved_context: string[];
  rewritten_question?: string;
}
export interface Conversation {
  id: number;
  title: string;
  user_id: number;
  created_at: string; // ISO 8601 date string
}

// --- NEW INTERFACE ---
export interface Document {
  id: number;
  filename: string;
  uploaded_at: string;
  user_id: number | null;
  file_type: 'text' | 'image' | 'video';
  s3_key?: string | null;
  transcription?: string | null;
  is_course_material: boolean;
  course_id?: number | null;
  course_name?: string | null; // Course name for badge display
}

export interface Course {
  id: number;
  name: string;
  description?: string | null;
  created_at: string;
}