import React, { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Paperclip, Send } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  onFileUpload: (file: File) => void;
  isLoading: boolean;
  isConversationSelected: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({ onSendMessage, onFileUpload, isLoading, isConversationSelected }) => {
  const [input, setInput] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleAttachClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onFileUpload(file);
    }
    if (e.target) {
        e.target.value = '';
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex w-full items-center space-x-2">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        className="hidden"
        accept=".pdf,.txt,.docx"
      />
      <Button
        type="button"
        variant="ghost"
        size="icon"
        onClick={handleAttachClick}
        disabled={isLoading || !isConversationSelected}
        aria-label="Attach file"
        className="text-primary hover:bg-accent"
      >
        <Paperclip className="h-5 w-5" />
      </Button>
      <Input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Ask a question about your documents..."
        disabled={isLoading || !isConversationSelected}
        className="bg-secondary/50 border-border focus:bg-card"
      />
      <Button type="submit" disabled={isLoading || !input.trim()}>
        <Send className="h-5 w-5" />
      </Button>
    </form>
  );
};

export default ChatInput;