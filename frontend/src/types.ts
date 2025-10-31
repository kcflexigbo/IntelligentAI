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
  user_id: number;
}