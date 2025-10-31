import React, { useState } from 'react';
import type { Document } from '../types';
import { CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { FileText, Paperclip, ChevronLeft, ChevronRight } from 'lucide-react';

interface DocumentSidebarProps {
  documents: Document[];
  // The onUploadClick prop is no longer needed here
}

const DocumentSidebar: React.FC<DocumentSidebarProps> = ({ documents }) => {
  const [collapsed, setCollapsed] = useState(false);
  return (
  <div className={cn('flex flex-col h-full bg-white text-gray-800 border-l border-blue-200 p-4 gap-4 transition-all duration-200 shadow-lg', collapsed ? 'w-14' : 'w-80')}>
      <div className="flex items-center justify-between">
        <CardHeader className={cn('p-2 pt-0', collapsed && 'hidden')}>
          <CardTitle className="text-lg flex items-center text-blue-700">
            <Paperclip className="mr-2 h-5 w-5 text-blue-600" />
            Attached Documents
          </CardTitle>
        </CardHeader>
        <button
          onClick={() => setCollapsed((s) => !s)}
          aria-label={collapsed ? 'Expand documents sidebar' : 'Collapse documents sidebar'}
          className="p-2 rounded-md hover:bg-blue-50 text-blue-600"
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>
      {!collapsed && (
        <CardContent className="p-0 flex-grow overflow-y-auto">
          {documents.length > 0 ? (
            <ul className="space-y-3">
              {documents.map((doc) => (
                <li key={doc.id} className="flex items-center text-sm text-gray-700 p-2 rounded-md hover:bg-blue-50 transition-colors">
                  <FileText className="h-4 w-4 mr-3 flex-shrink-0 text-blue-600" />
                  <span className="truncate">{doc.filename}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center p-4">
              <p className="text-sm text-gray-500">No documents uploaded.</p>
              <p className="text-xs text-gray-500 mt-1">
                Click the <Paperclip className="inline h-3 w-3 mx-1 text-blue-600" /> icon in the chat input to add a file to this conversation.
              </p>
            </div>
          )}
        </CardContent>
      )}
    </div>
  );
};

export default DocumentSidebar;