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