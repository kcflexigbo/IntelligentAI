import React, { useState } from 'react';
import api from '../services/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import type { Document } from '../types';

interface FileUploaderProps {
  onUploadSuccess: (document: Document) => void;
  conversationId: number | null; // <-- ADD THIS PROP
}

const FileUploader: React.FC<FileUploaderProps> = ({ onUploadSuccess, conversationId }) => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    // Check for conversationId
    if (!file || !conversationId) return;

    setUploading(true);
    setError('');
    
    try {
      // Step 1: Get presigned upload URL from backend
      const uploadUrlResponse = await api.post<{
        upload_url: string;
        s3_key: string;
        expires_in: number;
      }>('/documents/upload-url', {
        filename: file.name,
        conversation_id: conversationId,
        content_type: file.type || undefined,
      });

      const { upload_url, s3_key } = uploadUrlResponse.data;

      // Step 2: Upload file directly to S3 using presigned URL
      const uploadResponse = await fetch(upload_url, {
        method: 'PUT',
        body: file,
        headers: {
          'Content-Type': file.type || 'application/octet-stream',
        },
      });

      if (!uploadResponse.ok) {
        throw new Error(`S3 upload failed: ${uploadResponse.statusText}`);
      }

      // Step 3: Notify backend to process the uploaded file
      const processResponse = await api.post<Document>('/documents/process-upload', {
        s3_key: s3_key,
        filename: file.name,
        conversation_id: conversationId,
      });

      // Pass the full document object back
      onUploadSuccess(processResponse.data);
      setFile(null); // Clear the file input after success
    } catch (err) {
      setError('File upload failed. Please try again.');
      console.error(err);
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload Document</CardTitle>
        <CardDescription>
          {conversationId 
            ? "Upload documents (PDF, TXT, DOCX), images (JPG, PNG, etc.), or videos (MP4, AVI, etc.) to this conversation."
            : "Please select or start a conversation to upload documents."
          }
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <Input 
          type="file" 
          onChange={handleFileChange} 
          disabled={!conversationId}
          accept=".pdf,.txt,.docx,.doc,.ppt,.pptx,.md,.jpg,.jpeg,.png,.gif,.bmp,.webp,.mp4,.avi,.mov,.wmv,.webm"
        />
        <Button onClick={handleUpload} disabled={!file || uploading || !conversationId}>
          {uploading ? 'Uploading...' : 'Upload Document/Media'}
        </Button>
        {error && <p className="text-sm text-red-500">{error}</p>}
      </CardContent>
    </Card>
  );
};

export default FileUploader;