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
    
    const formData = new FormData();
    formData.append('file', file);
    // Append conversation_id to the form data
    formData.append('conversation_id', String(conversationId));

    try {
      const response = await api.post<Document>('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      // Pass the full document object back
      onUploadSuccess(response.data);
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
            ? "Upload a PDF, TXT, or DOCX file to this conversation."
            : "Please select or start a conversation to upload documents."
          }
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <Input type="file" onChange={handleFileChange} disabled={!conversationId} />
        <Button onClick={handleUpload} disabled={!file || uploading || !conversationId}>
          {uploading ? 'Uploading...' : 'Upload Document'}
        </Button>
        {error && <p className="text-sm text-red-500">{error}</p>}
      </CardContent>
    </Card>
  );
};

export default FileUploader;