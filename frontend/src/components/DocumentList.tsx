import React from 'react';
import type { Document } from '../types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FileText } from 'lucide-react';

interface DocumentListProps {
  documents: Document[];
}

const DocumentList: React.FC<DocumentListProps> = ({ documents }) => {
  return (
    <Card className="mt-4">
      <CardHeader className="py-3">
        <CardTitle className="text-base">Conversation Documents</CardTitle>
      </CardHeader>
      <CardContent className="py-3">
        {documents.length > 0 ? (
          <ul className="space-y-2">
            {documents.map((doc) => (
              <li key={doc.id} className="flex items-center text-sm text-muted-foreground">
                <FileText className="h-4 w-4 mr-2 flex-shrink-0" />
                <span className="truncate">{doc.filename}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">No documents have been uploaded for this conversation.</p>
        )}
      </CardContent>
    </Card>
  );
};

export default DocumentList;