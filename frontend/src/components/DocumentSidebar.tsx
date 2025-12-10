import React, { useState, useEffect } from 'react';
import type { Document } from '../types';
import { CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { FileText, Paperclip, ChevronLeft, ChevronRight, Image as ImageIcon, Video, Loader2, Trash2 } from 'lucide-react';
import api from '../services/api';

interface DocumentSidebarProps {
  documents: Document[];
  onDeleteDocument?: (documentId: number) => void;
}

interface MediaUrl {
  url: string;
  filename: string;
  file_type: string;
}

const DocumentSidebar: React.FC<DocumentSidebarProps> = ({ documents, onDeleteDocument }) => {
  const [collapsed, setCollapsed] = useState(false);
  const [mediaUrls, setMediaUrls] = useState<Record<number, MediaUrl>>({});
  const [loadingMedia, setLoadingMedia] = useState<Record<number, boolean>>({});

  // Fetch media URLs for images and videos
  useEffect(() => {
    const fetchMediaUrls = async () => {
      for (const doc of documents) {
        if ((doc.file_type === 'image' || doc.file_type === 'video') && !mediaUrls[doc.id]) {
          setLoadingMedia(prev => ({ ...prev, [doc.id]: true }));
          try {
            const response = await api.get<MediaUrl>(`/media/${doc.id}`);
            setMediaUrls(prev => ({ ...prev, [doc.id]: response.data }));
          } catch (error) {
            console.error(`Failed to load media for document ${doc.id}:`, error);
          } finally {
            setLoadingMedia(prev => ({ ...prev, [doc.id]: false }));
          }
        }
      }
    };

    if (documents.length > 0) {
      fetchMediaUrls();
    }
  }, [documents, mediaUrls]);

  const getFileIcon = (fileType: string) => {
    switch (fileType) {
      case 'image':
        return <ImageIcon className="h-4 w-4 mr-3 flex-shrink-0 text-primary" />;
      case 'video':
        return <Video className="h-4 w-4 mr-3 flex-shrink-0 text-primary" />;
      default:
        return <FileText className="h-4 w-4 mr-3 flex-shrink-0 text-primary" />;
    }
  };

  return (
    <div className={cn('flex flex-col h-full bg-card text-foreground border-l p-4 gap-4 transition-all duration-200 shadow-lg', collapsed ? 'w-14' : 'w-80')}>
      <div className="flex items-center justify-between">
        <CardHeader className={cn('p-2 pt-0', collapsed && 'hidden')}>
          <CardTitle className="text-md flex items-center text-primary-foreground text-black font-semibold">
            <Paperclip className="mr-2 h-5 w-5 text-primary text-black" />
            Attached Documents
          </CardTitle>
        </CardHeader>
        <button
          onClick={() => setCollapsed((s) => !s)}
          aria-label={collapsed ? 'Expand documents sidebar' : 'Collapse documents sidebar'}
          className="p-2 rounded-md hover:bg-accent text-muted-foreground"
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>
      {!collapsed && (
        <CardContent className="p-0 flex-grow overflow-y-auto">
          {documents.length > 0 ? (
            <ul className="space-y-3">
              {documents.map((doc) => (
                <li key={doc.id} className="p-2 rounded-md hover:bg-accent transition-colors relative group">
                  <div className="flex items-start gap-2">
                    {getFileIcon(doc.file_type)}
                    <div className="flex-1 min-w-0">
                      <span className="text-sm text-muted-foreground truncate block">{doc.filename}</span>
                      {onDeleteDocument && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="absolute top-1 right-1 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity text-destructive hover:text-destructive hover:bg-destructive/10"
                          onClick={() => {
                            const confirmed = window.confirm(
                              `Are you sure you want to delete "${doc.filename}"?`
                            );
                            if (confirmed) {
                              onDeleteDocument(doc.id);
                            }
                          }}
                          aria-label={`Delete ${doc.filename}`}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      )}
                      {doc.file_type === 'image' && mediaUrls[doc.id] && (
                        <img 
                          src={mediaUrls[doc.id].url} 
                          alt={doc.filename}
                          className="mt-2 rounded-md max-w-full h-auto max-h-32 object-contain"
                        />
                      )}
                      {doc.file_type === 'video' && mediaUrls[doc.id] && (
                        <video 
                          src={mediaUrls[doc.id].url}
                          controls
                          className="mt-2 rounded-md max-w-full max-h-32"
                        >
                          Your browser does not support the video tag.
                        </video>
                      )}
                      {loadingMedia[doc.id] && (
                        <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          <span>Loading...</span>
                        </div>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center p-4 ">
              <p className="text-sm text-muted-foreground">No documents uploaded.</p>
              <p className="text-xs text-muted-foreground mt-1">
                Click the <Paperclip className="inline h-3 w-3 mx-1 text-primary" /> icon in the chat input to add a file to this conversation.
              </p>
            </div>
          )}
        </CardContent>
      )}
    </div>
  );
};

export default DocumentSidebar;