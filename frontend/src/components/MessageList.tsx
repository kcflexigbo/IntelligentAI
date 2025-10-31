import React from 'react';
import type { ChatMessage } from '../types';
import { cn } from '@/lib/utils'; // Import the 'cn' utility

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
              ? 'bg-blue-600 text-white self-end'
              : 'bg-white border border-blue-200 text-gray-800 self-start'
          )}
        >
          <p className="text-sm">{msg.text}</p>
        </div>
      ))}
    </div>
  );
};

export default MessageList;