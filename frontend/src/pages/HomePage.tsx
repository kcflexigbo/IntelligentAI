import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import type { ChatMessage, Conversation, Document } from '../types';
import api from '../services/api';

// UI Components
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import MessageList from '../components/MessageList';
import ChatInput from '../components/ChatInput';
import ConversationSidebar from '../components/ConversationSidebar';
import DocumentSidebar from '../components/DocumentSidebar';
import { Toaster, toast } from 'sonner';

// Type definition for backend response
interface BackendChatMessage {
  id: number;
  conversation_id: number;
  content: string;
  is_from_user: boolean;
  created_at: string;
}

const HomePage = () => {
  const { logout } = useAuth();
  
  // State Management
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isCreatingConversation, setIsCreatingConversation] = useState(false);
  
  // Refs
  const messageListRef = useRef<HTMLDivElement>(null);
  // The fileInputRefForSidebar is no longer needed

  // Effect to fetch conversations on initial load
  useEffect(() => {
    const fetchConversations = async () => {
      try {
        const response = await api.get<Conversation[]>('/conversations');
        setConversations(response.data);
        if (response.data.length > 0) {
          handleSwitchConversation(response.data[0].id);
        }
      } catch (error) {
        console.error('Failed to fetch conversations:', error);
        toast.error('Could not load conversation history.');
      }
    };
    fetchConversations();
  }, []);

  // Effect to auto-scroll to the latest message
  useEffect(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSwitchConversation = async (id: number) => {
    if (id === activeConversationId) return;
    
    setActiveConversationId(id);
    setIsLoading(true);
    setMessages([]);
    setDocuments([]);

    try {
      const [messagesResponse, documentsResponse] = await Promise.all([
        api.get<BackendChatMessage[]>(`/conversations/${id}/messages`),
        api.get<Document[]>(`/conversations/${id}/documents`),
      ]);

      const fetchedMessages: ChatMessage[] = messagesResponse.data.map(msg => ({
        id: msg.id,
        sender: msg.is_from_user ? 'user' : 'ai',
        text: msg.content,
      }));
      
      setMessages(fetchedMessages);
      setDocuments(documentsResponse.data);
    } catch (error) {
      console.error(`Failed to fetch data for conversation ${id}:`, error);
      toast.error('Error loading conversation.');
      const errorMsg: ChatMessage = { id: Date.now(), sender: 'ai', text: 'Error loading messages.' };
      setMessages([errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChat = async () => {
    setIsCreatingConversation(true);
    try {
      const response = await api.post<Conversation>('/conversations');
      const newConversation = response.data;
      setConversations(prev => [newConversation, ...prev]);
      setActiveConversationId(newConversation.id);
      setMessages([]);
      setDocuments([]);
    } catch (error) {
      console.error('Failed to create new conversation:', error);
      toast.error('Failed to create a new chat.');
    } finally {
      setIsCreatingConversation(false);
    }
  };

  const handleDeleteConversation = async (id: number) => {
    const originalConversations = [...conversations];
    setConversations(prev => prev.filter(c => c.id !== id));
    
    if (activeConversationId === id) {
      setActiveConversationId(null);
      setMessages([]);
      setDocuments([]);
    }

    try {
      await api.delete(`/conversations/${id}`);
      toast.success("Conversation deleted.");
    } catch (error) {
      console.error('Failed to delete conversation:', error);
      toast.error("Failed to delete conversation. Please try again.");
      setConversations(originalConversations);
    }
  };
  
  const handleFileUpload = async (file: File) => {
    let conversationIdToUse = activeConversationId;

    if (!conversationIdToUse) {
      try {
        setIsCreatingConversation(true);
        toast.info("Creating a new conversation for your document...");
        const response = await api.post<Conversation>('/conversations');
        conversationIdToUse = response.data.id;
        const newConversation = { ...response.data, title: file.name.substring(0, 50) };
        setConversations(prev => [newConversation, ...prev]);
        setActiveConversationId(conversationIdToUse);
        setMessages([]);
        setDocuments([]);
      } catch (error) {
        toast.error("Failed to create a conversation. Please try again.");
        return;
      } finally {
        setIsCreatingConversation(false);
      }
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('conversation_id', String(conversationIdToUse));

    const toastId = toast.loading("Uploading and processing document...");
    try {
      const response = await api.post<Document>('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      toast.success(`Successfully uploaded "${response.data.filename}"`, { id: toastId });
      setDocuments(prev => [...prev, response.data]);
    } catch (err) {
      toast.error('File upload failed. Please try again.', { id: toastId });
      console.error(err);
    }
  };

  const handleSendMessage = async (userInput: string) => {
    let conversationIdToUse = activeConversationId;
    let isNewConversation = false;

    if (!conversationIdToUse) {
        isNewConversation = true;
      try {
        setIsCreatingConversation(true);
        const response = await api.post<Conversation>('/conversations');
        conversationIdToUse = response.data.id;
        const newConversation = { ...response.data, title: userInput.substring(0, 50) };
        setConversations(prev => [newConversation, ...prev]);
        setActiveConversationId(conversationIdToUse);
        setMessages([]);
        setDocuments([]);
      } catch (error) {
        toast.error('Failed to create conversation.');
        return;
      } finally {
        setIsCreatingConversation(false);
      }
    }

    const newUserMessage: ChatMessage = { id: Date.now(), sender: 'user', text: userInput };
    setMessages(prev => [...prev, newUserMessage]);
    setIsLoading(true);

    try {
      const response = await api.post(`/conversations/${conversationIdToUse}/messages`, {
        question: userInput,
      });
      const aiResponse: ChatMessage = { id: Date.now() + 1, sender: 'ai', text: response.data.answer };
      setMessages(prev => [...prev, aiResponse]);
      
      if (isNewConversation) {
        setConversations(prev => 
          prev.map(c => c.id === conversationIdToUse ? { ...c, title: userInput.substring(0, 50) } : c)
        );
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorResponse: ChatMessage = { id: Date.now() + 1, sender: 'ai', text: 'Sorry, something went wrong.' };
      setMessages(prev => [...prev, errorResponse]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <Toaster position="top-center" richColors />
      <div className="flex h-screen bg-muted/40">
        <ConversationSidebar
          conversations={conversations}
          activeConversationId={activeConversationId}
          onNewChat={handleNewChat}
          onSwitchConversation={handleSwitchConversation}
          onDeleteConversation={handleDeleteConversation}
          isCreating={isCreatingConversation}
        />

        <main className="flex-1 flex flex-col p-4" style={{ maxHeight: '100vh' }}>
          <Card className="w-full h-full flex flex-col overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between border-b">
              <CardTitle>Intelligent Learning Assistant</CardTitle>
              <Button variant="outline" onClick={logout}>Logout</Button>
            </CardHeader>
            <CardContent ref={messageListRef} className="flex-grow p-4 overflow-y-auto">
                {activeConversationId ? (
                  <MessageList messages={messages} />
                ) : (
                  <div className="flex h-full items-center justify-center">
                    <p className="text-muted-foreground text-center">
                      {conversations.length > 0
                        ? "Select a conversation to begin."
                        : 'Click "New Chat" to start a conversation.'
                      }
                    </p>
                  </div>
                )}
            </CardContent>
            <CardFooter className="p-4 border-t">
              <ChatInput
                onSendMessage={handleSendMessage}
                onFileUpload={handleFileUpload}
                isLoading={isLoading || isCreatingConversation}
                isConversationSelected={!!activeConversationId || isCreatingConversation}
              />
            </CardFooter>
          </Card>
        </main>

        <DocumentSidebar documents={documents} />
      </div>
    </>
  );
};

export default HomePage;