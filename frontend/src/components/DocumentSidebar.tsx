import React from 'react';
import type { Document } from '../types';
import { CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FileText, Paperclip } from 'lucide-react';

interface DocumentSidebarProps {
  documents: Document[];
  // The onUploadClick prop is no longer needed here
}

const DocumentSidebar: React.FC<DocumentSidebarProps> = ({ documents }) => {
  return (
    <div className="flex flex-col h-full bg-card border-l p-4 gap-4 w-80">
      <CardHeader className="p-2 pt-0">
        <CardTitle className="text-lg flex items-center">
          <Paperclip className="mr-2 h-5 w-5" />
          Attached Documents
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0 flex-grow overflow-y-auto">
        {documents.length > 0 ? (
          <ul className="space-y-3">
            {documents.map((doc) => (
              <li key={doc.id} className="flex items-center text-sm text-muted-foreground p-2 rounded-md hover:bg-muted/50">
                <FileText className="h-4 w-4 mr-3 flex-shrink-0 text-primary" />
                <span className="truncate">{doc.filename}</span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center p-4">
            <p className="text-sm text-muted-foreground">No documents uploaded.</p>
            <p className="text-xs text-muted-foreground mt-1">
              Click the <Paperclip className="inline h-3 w-3 mx-1" /> icon in the chat input to add a file to this conversation.
            </p>
          </div>
        )}
      </CardContent>
    </div>
  );
};

export default DocumentSidebar;