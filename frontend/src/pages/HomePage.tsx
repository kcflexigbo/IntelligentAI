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
import CourseMaterialsView from '../components/CourseMaterialsView';
import { Toaster, toast } from 'sonner';
import usePageTitle from '@/lib/usePageTitle';
import { MessageSquare, BookOpen } from 'lucide-react';

// Type definition for backend response
interface BackendChatMessage {
  id: number;
  conversation_id: number;
  content: string;
  is_from_user: boolean;
  created_at: string;
}

const HomePage = () => {
  usePageTitle('EcoLearn');
  const { logout } = useAuth();
  
  // State Management
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isCreatingConversation, setIsCreatingConversation] = useState(false);
  const [currentView, setCurrentView] = useState<'conversations' | 'course-materials'>('conversations');
  
  // Refs
  const messageListRef = useRef<HTMLDivElement>(null);

  // Effect to fetch conversations on initial load
  useEffect(() => {
    const fetchConversations = async () => {
      try {
        const response = await api.get<Conversation[]>('/conversations');
        setConversations(response.data);
        // If conversations exist, load the first one by default
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

  /**
   * Switches the active conversation and fetches its messages and documents.
   */
  const handleSwitchConversation = async (id: number) => {
    if (id === activeConversationId) return; // Avoid refetching if already active
    
    setActiveConversationId(id);
    setIsLoading(true);
    setMessages([]);
    setDocuments([]);

    try {
      // Fetch messages and documents in parallel for faster loading
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

  /**
   * Creates a new, empty conversation and sets it as active.
   */
  const handleNewChat = async () => {
    setIsCreatingConversation(true);
    try {
      const response = await api.post<Conversation>('/conversations');
      const newConversation = response.data;
      setConversations(prev => [newConversation, ...prev]);
      // Switch to the new conversation
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

  /**
   * Deletes a conversation and handles UI updates.
   */
  const handleDeleteConversation = async (id: number) => {
    const originalConversations = [...conversations];
    // Optimistically remove from UI for a faster user experience
    setConversations(prev => prev.filter(c => c.id !== id));
    
    // If the deleted conversation was active, clear the main panel
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
      // Rollback UI change if API call fails
      setConversations(originalConversations);
    }
  };
  
  /**
   * Handles renaming a conversation title.
   */
  const handleRenameConversation = async (id: number, newTitle: string) => {
    const originalConversations = [...conversations];

    // Optimistically update the UI for a snappy feel
    setConversations(prev => 
      prev.map(c => (c.id === id ? { ...c, title: newTitle } : c))
    );

    try {
      // Send the update to the backend
      await api.patch(`/conversations/${id}`, { title: newTitle });
    } catch (error) {
      console.error('Failed to rename conversation:', error);
      toast.error("Failed to save the new title.");
      // If the API call fails, revert the change in the UI
      setConversations(originalConversations);
    }
  };
  
  /**
   * Handles uploading a file. It will auto-create a conversation if none is active.
   */
  const handleFileUpload = async (file: File) => {
    let conversationIdToUse = activeConversationId;

    // If no conversation is active, create one for the document
    if (!conversationIdToUse) {
      try {
        setIsCreatingConversation(true);
        toast.info("Creating a new conversation for your document...");
        const response = await api.post<Conversation>('/conversations');
        conversationIdToUse = response.data.id;
        
        // Create a title based on the filename
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

    const toastId = toast.loading("Uploading and processing document...");
    try {
      // Step 1: Get presigned upload URL
      const uploadUrlResponse = await api.post<{
        upload_url: string;
        s3_key: string;
        expires_in: number;
      }>('/documents/upload-url', {
        filename: file.name,
        conversation_id: conversationIdToUse,
        content_type: file.type || undefined,
      });

      const { upload_url, s3_key } = uploadUrlResponse.data;

      // Step 2: Upload directly to S3
      toast.loading("Uploading to storage...", { id: toastId });
      const uploadResponse = await fetch(upload_url, {
        method: 'PUT',
        body: file,
        headers: {
          'Content-Type': file.type || 'application/octet-stream',
        },
      });

      if (!uploadResponse.ok) {
        throw new Error(`Upload failed: ${uploadResponse.statusText}`);
      }

      // Step 3: Process the uploaded file
      toast.loading("Processing document...", { id: toastId });
      const response = await api.post<Document>('/documents/process-upload', {
        s3_key: s3_key,
        filename: file.name,
        conversation_id: conversationIdToUse,
      });
      
      toast.success(`Successfully uploaded "${response.data.filename}"`, { id: toastId });
      setDocuments(prev => [...prev, response.data]);
    } catch (err) {
      toast.error('File upload failed. Please try again.', { id: toastId });
      console.error(err);
    }
  };

  /**
   * Handles deleting a document from a conversation.
   */
  const handleDeleteDocument = async (documentId: number) => {
    if (!activeConversationId) {
      toast.error('No active conversation.');
      return;
    }

    try {
      await api.delete(`/documents/${documentId}`);
      toast.success('Document deleted successfully.');
      
      // Refresh documents list
      const documentsResponse = await api.get<Document[]>(`/conversations/${activeConversationId}/documents`);
      setDocuments(documentsResponse.data);
    } catch (error) {
      console.error('Failed to delete document:', error);
      toast.error('Failed to delete document. Please try again.');
    }
  };

  /**
   * Sends a user's message. It will auto-create a conversation if none is active.
   */
  const handleSendMessage = async (userInput: string) => {
    let conversationIdToUse = activeConversationId;
    let isNewConversation = false;

    // If no conversation is active, create one for the message
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
      
      // If a new conversation was created, update its title in the sidebar
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
        {/* Left Sidebar for Conversations */}
        <ConversationSidebar
          conversations={conversations}
          activeConversationId={activeConversationId}
          onNewChat={handleNewChat}
          onSwitchConversation={handleSwitchConversation}
          onDeleteConversation={handleDeleteConversation}
          onRenameConversation={handleRenameConversation}
          isCreating={isCreatingConversation}
        />

        {/* Main Chat Panel */}
        <main className="flex-1 flex flex-col p-4" style={{ maxHeight: '100vh' }}>
          <Card className="w-full h-full flex flex-col overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between border-b">
              <div className="flex items-center gap-2">
                <CardTitle>ContextIQ</CardTitle>
                <div className="flex items-center gap-1 ml-4">
                  <Button
                    variant={currentView === 'conversations' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setCurrentView('conversations')}
                  >
                    <MessageSquare className="h-4 w-4 mr-2" />
                    Conversations
                  </Button>
                  <Button
                    variant={currentView === 'course-materials' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setCurrentView('course-materials')}
                  >
                    <BookOpen className="h-4 w-4 mr-2" />
                    Course Materials
                  </Button>
                </div>
              </div>
              <Button variant="outline" onClick={logout}>Logout</Button>
            </CardHeader>
            {currentView === 'conversations' ? (
              <>
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
              </>
            ) : (
              <CourseMaterialsView />
            )}
          </Card>
        </main>

        {/* Right Sidebar for Documents */}
        <DocumentSidebar documents={documents} onDeleteDocument={handleDeleteDocument} />
      </div>
    </>
  );
};

export default HomePage;