import React, { useState, useEffect, useRef } from 'react';
import type { Document, Course } from '../types';
import api from '../services/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { FileText, Image as ImageIcon, Video, Loader2, Upload, Paperclip, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

interface MediaUrl {
  url: string;
  filename: string;
  file_type: string;
}

const CourseMaterialsView: React.FC = () => {
  const [courseMaterials, setCourseMaterials] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [mediaUrls, setMediaUrls] = useState<Record<number, MediaUrl>>({});
  const [loadingMedia, setLoadingMedia] = useState<Record<number, boolean>>({});
  const [courseName, setCourseName] = useState<string>('Introduction to Computer Science');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch course materials on mount
  useEffect(() => {
    fetchCourseMaterials();
  }, []);

  // Fetch media URLs for images and videos
  useEffect(() => {
    const fetchMediaUrls = async () => {
      for (const doc of courseMaterials) {
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

    if (courseMaterials.length > 0) {
      fetchMediaUrls();
    }
  }, [courseMaterials, mediaUrls]);

  const fetchCourseMaterials = async () => {
    setIsLoading(true);
    try {
      const response = await api.get<Document[]>('/course-materials');
      setCourseMaterials(response.data);
      
      // Get course name from first material or fetch courses list
      if (response.data.length > 0 && response.data[0].course_name) {
        setCourseName(response.data[0].course_name);
      } else {
        // Fetch courses to get the default course name
        try {
          const coursesResponse = await api.get<Course[]>('/course-materials/courses');
          if (coursesResponse.data.length > 0) {
            setCourseName(coursesResponse.data[0].name);
          }
        } catch (err) {
          // Use default if fetch fails
          console.error('Failed to fetch courses:', err);
        }
      }
    } catch (error) {
      console.error('Failed to fetch course materials:', error);
      toast.error('Could not load course materials.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (file: File) => {
    const toastId = toast.loading("Uploading and processing document...");
    setIsUploading(true);
    
    try {
      // Step 1: Get presigned upload URL
      const uploadUrlResponse = await api.post<{
        upload_url: string;
        s3_key: string;
        expires_in: number;
      }>('/course-materials/upload-url', {
        filename: file.name,
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
      const response = await api.post<Document>('/course-materials/process-upload', {
        s3_key: s3_key,
        filename: file.name,
      });
      
      toast.success(`Successfully uploaded "${response.data.filename}"`, { id: toastId });
      
      // Refresh the course materials list
      await fetchCourseMaterials();
    } catch (err) {
      toast.error('File upload failed. Please try again.', { id: toastId });
      console.error(err);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleAttachClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
    if (e.target) {
      e.target.value = '';
    }
  };

  const getFileIcon = (fileType: string) => {
    switch (fileType) {
      case 'image':
        return <ImageIcon className="h-5 w-5 mr-3 flex-shrink-0 text-primary" />;
      case 'video':
        return <Video className="h-5 w-5 mr-3 flex-shrink-0 text-primary" />;
      default:
        return <FileText className="h-5 w-5 mr-3 flex-shrink-0 text-primary" />;
    }
  };

  const handleDeleteDocument = async (documentId: number, filename: string) => {
    // Show confirmation dialog
    const confirmed = window.confirm(
      `Are you sure you want to delete "${filename}"? This will permanently delete this course material.`
    );
    
    if (!confirmed) {
      return;
    }

    try {
      await api.delete(`/course-materials/${documentId}`);
      toast.success(`Successfully deleted "${filename}"`);
      // Refresh the course materials list
      await fetchCourseMaterials();
    } catch (error) {
      console.error('Failed to delete document:', error);
      toast.error('Failed to delete document. Please try again.');
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex flex-row items-center justify-between border-b pb-4 px-6 pt-6">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">ContextIQ - {courseName}</h2>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            className="hidden"
            accept=".pdf,.txt,.docx,.doc,.ppt,.pptx,.jpg,.jpeg,.png,.gif,.bmp,.webp,.mp4,.avi,.mov,.wmv,.flv,.webm,.mkv,.m4v"
            aria-label="Upload course material file"
          />
          <Button
            onClick={handleAttachClick}
            disabled={isUploading}
            variant="outline"
            size="sm"
          >
            <Upload className="h-4 w-4 mr-2" />
            Upload Material
          </Button>
        </div>
      </div>
      
      <div className="flex-grow p-4 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : courseMaterials.length > 0 ? (
          <div className="space-y-4">
            {courseMaterials.map((doc) => (
              <Card key={doc.id} className="p-4 relative">
                <div className="flex items-start gap-3">
                  {getFileIcon(doc.file_type)}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm font-medium truncate">{doc.filename}</span>
                      {doc.course_name && (
                        <Badge variant="secondary" className="text-xs">
                          {doc.course_name}
                        </Badge>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="absolute top-2 right-2 h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                      onClick={() => handleDeleteDocument(doc.id, doc.filename)}
                      aria-label={`Delete ${doc.filename}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                    <p className="text-xs text-muted-foreground mb-2">
                      Uploaded {new Date(doc.uploaded_at).toLocaleDateString()}
                    </p>
                    {doc.file_type === 'image' && mediaUrls[doc.id] && (
                      <img 
                        src={mediaUrls[doc.id].url} 
                        alt={doc.filename}
                        className="mt-2 rounded-md max-w-full h-auto max-h-48 object-contain"
                      />
                    )}
                    {doc.file_type === 'video' && mediaUrls[doc.id] && (
                      <video 
                        src={mediaUrls[doc.id].url}
                        controls
                        className="mt-2 rounded-md max-w-full max-h-48"
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
              </Card>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center p-4">
            <Paperclip className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-sm text-muted-foreground mb-2">No course materials uploaded yet.</p>
            <p className="text-xs text-muted-foreground">
              Click "Upload Material" to add course documents.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default CourseMaterialsView;

