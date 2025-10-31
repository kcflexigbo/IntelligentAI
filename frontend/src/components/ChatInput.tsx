import React, { useState, useRef } from 'react'; // <-- Import useRef
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Paperclip, Send } from 'lucide-react'; // <-- Import icons

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  onFileUpload: (file: File) => void; // <-- Add file upload handler prop
  isLoading: boolean;
  isConversationSelected: boolean; // <-- To disable upload button
}

const ChatInput: React.FC<ChatInputProps> = ({ onSendMessage, onFileUpload, isLoading, isConversationSelected }) => {
  const [input, setInput] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null); // <-- Ref for the hidden file input

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleAttachClick = () => {
    // Trigger the hidden file input when the button is clicked
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onFileUpload(file);
    }
    // Reset the input value to allow uploading the same file again
    if (e.target) {
        e.target.value = '';
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex w-full items-center space-x-2">
      {/* Hidden file input */}
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
      >
        <Paperclip className="h-5 w-5" />
      </Button>

      <Input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Ask a question about your documents..."
        disabled={isLoading || !isConversationSelected}
      />
      <Button type="submit" disabled={isLoading || !input.trim()}>
        <Send className="h-5 w-5" />
      </Button>
    </form>
  );
};

export default ChatInput;