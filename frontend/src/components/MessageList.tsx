import React from 'react';
import type { ChatMessage } from '../types';
import { cn } from '@/lib/utils';

interface MessageListProps {
  messages: ChatMessage[];
}

const MessageList: React.FC<MessageListProps> = ({ messages }) => {
  return (
    <div className="flex flex-col gap-4 p-4">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={cn(
            'p-3 rounded-lg max-w-[70%] shadow-sm',
            msg.sender === 'user'
              ? 'bg-primary text-primary-foreground self-end'
              : 'bg-card border border-border text-foreground self-start'
          )}
        >
          <p className="text-sm">{msg.text}</p>
        </div>
      ))}
    </div>
  );
};

export default MessageList;