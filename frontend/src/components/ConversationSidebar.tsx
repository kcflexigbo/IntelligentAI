import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { Conversation } from '../types';
import { PlusCircle, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';

interface ConversationSidebarProps {
  conversations: Conversation[];
  activeConversationId: number | null;
  onNewChat: () => void;
  onSwitchConversation: (id: number) => void;
  onDeleteConversation: (id: number) => void; // <-- ADD THIS LINE
  isCreating: boolean;
}

const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  conversations,
  activeConversationId,
  onNewChat,
  onSwitchConversation,
  onDeleteConversation, // <-- DESTRUCTURE THE PROP
  isCreating,
}) => {
  const [collapsed, setCollapsed] = useState(false);
  // Stop event propagation to prevent switching conversation when deleting
  const handleDeleteClick = (e: React.MouseEvent, id: number) => {
    e.stopPropagation(); 
    if (window.confirm('Are you sure you want to delete this conversation?')) {
        onDeleteConversation(id);
    }
  };

  return (
  <div className={cn('flex flex-col h-full bg-white text-gray-800 border-r border-blue-200 p-4 gap-4 transition-all duration-200 shadow-lg', collapsed ? 'w-14' : 'w-72')}>
      <div className="flex items-center justify-between">
        <Button onClick={onNewChat} disabled={isCreating} className={cn('bg-blue-600 hover:bg-blue-700 text-white', collapsed && 'hidden')}>
          <PlusCircle className="mr-2 h-4 w-4" />
          New Chat
        </Button>
        <button
          onClick={() => setCollapsed((s) => !s)}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="p-2 rounded-md text-red-600"
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>
      {!collapsed && (
        <div className="flex-grow overflow-y-auto pr-2">
        <div className="flex flex-col gap-2">
          <h2 className="text-lg font-semibold tracking-tight mb-2 text-blue-700">
            History
          </h2>
          {conversations.length > 0 ? (
            conversations.map((conv) => (
              <div key={conv.id} className="relative group flex items-center">
                <Button
                  variant="ghost"
                  className={cn(
                    'w-full justify-start text-left rounded-md transition-colors pr-8', // Add padding for the icon
                    activeConversationId === conv.id
                      ? 'bg-blue-100 text-red-700 border border-red-300'
                      : 'text-gray-700 hover:bg-gray-100'
                  )}
                  onClick={() => onSwitchConversation(conv.id)}
                >
                  <p className="truncate">{conv.title}</p>
                </Button>
                <button
                  onClick={(e) => handleDeleteClick(e, conv.id)}
                  className={cn(
                    'absolute right-1 p-1 rounded-md text-gray-500 hover:bg-red-100 hover:text-red-600 transition-colors',
                    // Make it visible on hover, or always if it's the active chat
                    activeConversationId === conv.id ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                  )}
                  aria-label="Delete conversation"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))
          ) : (
            <p className="text-sm text-gray-500 px-2">No conversations yet.</p>
          )}
        </div>
      </div>
      )}
    </div>
  );
};

export default ConversationSidebar;