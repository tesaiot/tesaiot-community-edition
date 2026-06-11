/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useCallback } from 'react';
import { ImageInput } from '@/components/image-input/image-input';
import { toast } from 'sonner';

interface DevicePictureUploadProps {
  value?: string | null;
  onChange: (imageData: string | null) => void;
  disabled?: boolean;
  className?: string;
}

// Allowed file types and max size
const ALLOWED_FILE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp'];
const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
const MAX_DIMENSION = 2048; // Max width or height

export const DevicePictureUpload: React.FC<DevicePictureUploadProps> = ({
  value,
  onChange,
  disabled = false,
  className = ''
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(value || null);

  const validateFile = (file: File): Promise<boolean> => {
    return new Promise((resolve) => {
      // Check file type
      if (!ALLOWED_FILE_TYPES.includes(file.type)) {
        toast.error(`Invalid file type. Allowed types: ${ALLOWED_EXTENSIONS.join(', ')}`);
        resolve(false);
        return;
      }

      // Check file size
      if (file.size > MAX_FILE_SIZE) {
        toast.error(`File size exceeds 5MB limit. Current size: ${(file.size / 1024 / 1024).toFixed(2)}MB`);
        resolve(false);
        return;
      }

      // Check image dimensions
      const img = new Image();
      const url = URL.createObjectURL(file);
      
      img.onload = () => {
        URL.revokeObjectURL(url);
        
        if (img.width > MAX_DIMENSION || img.height > MAX_DIMENSION) {
          toast.error(`Image dimensions exceed ${MAX_DIMENSION}x${MAX_DIMENSION}px. Current: ${img.width}x${img.height}px`);
          resolve(false);
        } else {
          resolve(true);
        }
      };

      img.onerror = () => {
        URL.revokeObjectURL(url);
        toast.error('Failed to load image. File may be corrupted.');
        resolve(false);
      };

      img.src = url;
    });
  };

  const compressImage = async (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = (e) => {
        const img = new Image();
        
        img.onload = () => {
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d');
          
          if (!ctx) {
            reject(new Error('Failed to get canvas context'));
            return;
          }

          // Calculate new dimensions while maintaining aspect ratio
          let { width, height } = img;
          if (width > MAX_DIMENSION || height > MAX_DIMENSION) {
            if (width > height) {
              height = (height / width) * MAX_DIMENSION;
              width = MAX_DIMENSION;
            } else {
              width = (width / height) * MAX_DIMENSION;
              height = MAX_DIMENSION;
            }
          }

          canvas.width = width;
          canvas.height = height;

          // Draw and compress
          ctx.drawImage(img, 0, 0, width, height);
          
          // Convert to base64 with compression
          const compressedDataUrl = canvas.toDataURL('image/jpeg', 0.8);
          resolve(compressedDataUrl);
        };

        img.onerror = () => reject(new Error('Failed to load image for compression'));
        img.src = e.target?.result as string;
      };

      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsDataURL(file);
    });
  };

  const handleImageChange = useCallback(async (fileList: any[]) => {
    if (fileList.length === 0) {
      setPreviewUrl(null);
      onChange(null);
      return;
    }

    const imageFile = fileList[0];
    if (!imageFile.file) return;

    setIsUploading(true);

    try {
      // Validate file
      const isValid = await validateFile(imageFile.file);
      if (!isValid) {
        setIsUploading(false);
        return;
      }

      // Compress if needed
      let imageData: string;
      if (imageFile.file.size > 1024 * 1024 || imageFile.dataURL) { // > 1MB or already has dataURL
        imageData = await compressImage(imageFile.file);
      } else {
        imageData = imageFile.dataURL || await compressImage(imageFile.file);
      }

      setPreviewUrl(imageData);
      onChange(imageData);
      toast.success('Device picture uploaded successfully');
    } catch (error) {
      console.error('Image upload error:', error);
      toast.error('Failed to process image. Please try again.');
    } finally {
      setIsUploading(false);
    }
  }, [onChange]);

  const handleRemove = useCallback(() => {
    setPreviewUrl(null);
    onChange(null);
    toast.info('Device picture removed');
  }, [onChange]);

  return (
    <div className={`device-picture-upload ${className}`} style={{ width: '100%' }}>
      <ImageInput
        value={previewUrl ? [{ dataURL: previewUrl }] : []}
        onChange={handleImageChange}
        multiple={false}
        acceptType={ALLOWED_EXTENSIONS}
        inputProps={{ disabled: disabled || isUploading }}
      >
        {({ fileList, onImageUpload, onImageRemove, dragProps, isDragging }) => (
          <div className="upload-container" style={{ marginTop: '1rem' }}>
            {fileList.length === 0 ? (
              <div
                className={`upload-area p-8 border-2 border-dashed rounded-lg text-center cursor-pointer transition-all ${
                  isDragging ? 'border-primary bg-primary/5' : 'border-gray-300 hover:border-primary'
                } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                onClick={!disabled ? onImageUpload : undefined}
                {...(!disabled ? dragProps : {})}
                style={{ 
                  minHeight: '200px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  alignItems: 'center'
                }}
              >
                <div className="mb-4">
                  <i className="fas fa-camera text-4xl text-gray-400"></i>
                </div>
                <h4 className="text-lg font-medium mb-2">
                  {isDragging ? 'Drop image here' : 'Upload Device Picture'}
                </h4>
                <p className="text-sm text-gray-500 mb-2">
                  Drag and drop or click to select
                </p>
                <p className="text-xs text-gray-400">
                  Supported formats: JPEG, PNG, WebP (Max 5MB, {MAX_DIMENSION}x{MAX_DIMENSION}px)
                </p>
                {isUploading && (
                  <div className="mt-4">
                    <div className="spinner-border spinner-border-sm" role="status">
                      <span className="sr-only">Processing...</span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="preview-container" style={{ textAlign: 'center' }}>
                <div className="position-relative">
                  <img
                    src={fileList[0].dataURL}
                    alt="Device preview"
                    className="img-fluid rounded shadow-sm"
                    style={{ maxHeight: '300px', width: 'auto' }}
                  />
                  {!disabled && (
                    <button
                      type="button"
                      className="btn btn-sm btn-danger position-absolute top-0 end-0 m-2"
                      onClick={() => onImageRemove(0)}
                      title="Remove picture"
                    >
                      <i className="fas fa-times"></i>
                    </button>
                  )}
                </div>
                <div className="mt-3">
                  <button
                    type="button"
                    className="btn btn-sm btn-secondary"
                    onClick={onImageUpload}
                    disabled={disabled || isUploading}
                  >
                    <i className="fas fa-sync-alt me-1"></i>
                    Replace Picture
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </ImageInput>

    </div>
  );
};

export default DevicePictureUpload;