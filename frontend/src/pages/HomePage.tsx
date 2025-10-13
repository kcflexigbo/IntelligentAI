import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import type { ChatMessage, ChatApiResponse } from '../types';
import api from '../services/api';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import FileUploader from '../components/FileUploader';
import MessageList from '../components/MessageList';
import ChatInput from '../components/ChatInput';

const HomePage = () => {
  const { logout } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [sessionId] = useState<string>(() => `session_${Date.now()}`);
  const messageListRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the latest message
  useEffect(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, [messages]);

  const handleUploadSuccess = (filename: string) => {
    const newMessage: ChatMessage = {
      id: Date.now(),
      sender: 'ai',
      text: `Successfully uploaded "${filename}". You can now ask questions about it.`,
    };
    setMessages((prevMessages) => [...prevMessages, newMessage]);
  };

  const handleSendMessage = async (userInput: string) => {
    const newUserMessage: ChatMessage = {
      id: Date.now(),
      sender: 'user',
      text: userInput,
    };
    setMessages((prevMessages) => [...prevMessages, newUserMessage]);
    setIsLoading(true);

    try {
      const response = await api.post<ChatApiResponse>('/chat', {
        question: userInput,
        session_id: sessionId,
      });

      const aiResponse: ChatMessage = {
        id: Date.now() + 1,
        sender: 'ai',
        text: response.data.answer,
      };
      setMessages((prevMessages) => [...prevMessages, aiResponse]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorResponse: ChatMessage = {
        id: Date.now() + 1,
        sender: 'ai',
        text: 'Sorry, something went wrong. Please try again.',
      };
      setMessages((prevMessages) => [...prevMessages, errorResponse]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-muted/40 p-4 items-center">
      <Card className="w-full max-w-3xl h-full flex flex-col">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Intelligent Learning Assistant</CardTitle>
          <Button variant="outline" onClick={logout}>Logout</Button>
        </CardHeader>
        <CardContent className="p-4">
          <FileUploader onUploadSuccess={handleUploadSuccess} />
        </CardContent>
        <div ref={messageListRef} className="flex-grow overflow-y-auto border-t border-b">
          <MessageList messages={messages} />
        </div>
        <CardFooter className="p-4">
          <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
        </CardFooter>
      </Card>
    </div>
  );
};

export default HomePage;