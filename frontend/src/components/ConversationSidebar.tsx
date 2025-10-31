import React, { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input'; // <-- Import Input component
import { cn } from '@/lib/utils';
import type { Conversation } from '../types';
import { PlusCircle, Trash2, Pencil } from 'lucide-react'; // <-- Import Pencil icon

interface ConversationSidebarProps {
  conversations: Conversation[];
  activeConversationId: number | null;
  onNewChat: () => void;
  onSwitchConversation: (id: number) => void;
  onDeleteConversation: (id: number) => void;
  onRenameConversation: (id: number, newTitle: string) => void; // <-- Add rename handler prop
  isCreating: boolean;
}

const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  conversations,
  activeConversationId,
  onNewChat,
  onSwitchConversation,
  onDeleteConversation,
  onRenameConversation, // <-- Destructure handler
  isCreating,
}) => {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [tempTitle, setTempTitle] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus the input when editing starts
  useEffect(() => {
    if (editingId !== null) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editingId]);

  const handleDeleteClick = (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this conversation?')) {
      onDeleteConversation(id);
    }
  };

  const handleRenameClick = (e: React.MouseEvent, conversation: Conversation) => {
    e.stopPropagation();
    setEditingId(conversation.id);
    setTempTitle(conversation.title); // Pre-fill with current title
  };

  const handleRenameSubmit = () => {
    if (editingId && tempTitle.trim()) {
      onRenameConversation(editingId, tempTitle.trim());
    }
    setEditingId(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleRenameSubmit();
    } else if (e.key === 'Escape') {
      setEditingId(null); // Cancel editing on Escape
    }
  };

  return (
    <div className="flex flex-col h-full bg-card border-r p-4 gap-4 w-72">
      <Button onClick={onNewChat} disabled={isCreating}>
        <PlusCircle className="mr-2 h-4 w-4" />
        New Chat
      </Button>
      <div className="flex-grow overflow-y-auto pr-2">
        <div className="flex flex-col gap-2">
          <h2 className="text-lg font-semibold tracking-tight mb-2">History</h2>
          {conversations.map((conv) => (
            <div key={conv.id} className="relative group flex items-center w-full">
              {editingId === conv.id ? (
                <Input
                  ref={inputRef}
                  value={tempTitle}
                  onChange={(e) => setTempTitle(e.target.value)}
                  onBlur={handleRenameSubmit}
                  onKeyDown={handleKeyDown}
                  className="h-9"
                />
              ) : (
                <Button
                  variant="ghost"
                  className={cn(
                    'w-full justify-start text-left rounded-md transition-colors pr-14', // Add padding for icons
                    activeConversationId === conv.id
                      ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                      : 'text-muted-foreground'
                  )}
                  onClick={() => onSwitchConversation(conv.id)}
                >
                  <p className="truncate">{conv.title}</p>
                </Button>
              )}
              {editingId !== conv.id && (
                <div className="absolute right-1 flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={(e) => handleRenameClick(e, conv)}
                    className="p-1 rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    aria-label="Rename conversation"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    onClick={(e) => handleDeleteClick(e, conv.id)}
                    className="p-1 rounded-md text-muted-foreground hover:bg-destructive/20 hover:text-destructive"
                    aria-label="Delete conversation"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>
          ))}
          {conversations.length === 0 && (
            <p className="text-sm text-muted-foreground px-2">No conversations yet.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default ConversationSidebar;