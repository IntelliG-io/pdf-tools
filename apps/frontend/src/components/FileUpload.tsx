
import React, { useState, DragEvent, ChangeEvent } from "react";
import { cn } from "@/lib/utils";
import { Upload, File, AlertCircle, CheckCircle2 } from "lucide-react";

interface FileUploadProps {
  className?: string;
  onFilesSelected?: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  maxSize?: number; // In MB
}

const FileUpload: React.FC<FileUploadProps> = ({
  className,
  onFilesSelected,
  accept = ".pdf",
  multiple = true,
  maxSize = 10, // Default 10MB
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  
  const maxSizeBytes = maxSize * 1024 * 1024;
  
  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };
  
  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };
  
  const validateFiles = (fileList: FileList): File[] => {
    const validFiles: File[] = [];
    const acceptedTypes = accept.split(",").map(type => type.trim());
    
    Array.from(fileList).forEach(file => {
      // Check file size
      if (file.size > maxSizeBytes) {
        setError(`File ${file.name} exceeds the maximum size of ${maxSize}MB`);
        return;
      }
      
      // Check file type if accept is specified
      if (accept !== "*" && !acceptedTypes.some(type => {
        if (type.startsWith(".")) {
          return file.name.toLowerCase().endsWith(type.toLowerCase());
        } else {
          return file.type.match(new RegExp(type.replace("*", ".*")));
        }
      })) {
        setError(`File ${file.name} is not an accepted file type`);
        return;
      }
      
      validFiles.push(file);
    });
    
    return validFiles;
  };
  
  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    setError(null);
    
    if (e.dataTransfer.files.length > 0) {
      const validFiles = validateFiles(e.dataTransfer.files);
      if (validFiles.length > 0) {
        handleFiles(validFiles);
      }
    }
  };
  
  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    setError(null);
    
    if (e.target.files && e.target.files.length > 0) {
      const validFiles = validateFiles(e.target.files);
      if (validFiles.length > 0) {
        handleFiles(validFiles);
      }
    }
  };
  
  const handleFiles = (validFiles: File[]) => {
    if (!multiple && validFiles.length > 1) {
      setError("Only one file can be uploaded");
      return;
    }
    
    const newFiles = multiple ? [...files, ...validFiles] : validFiles;
    setFiles(newFiles);
    
    if (onFilesSelected) {
      onFilesSelected(newFiles);
    }
  };
  
  const removeFile = (index: number) => {
    const newFiles = [...files];
    newFiles.splice(index, 1);
    setFiles(newFiles);
    
    if (onFilesSelected) {
      onFilesSelected(newFiles);
    }
  };
  
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + " B";
    else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
    else return (bytes / 1048576).toFixed(1) + " MB";
  };
  
  return (
    <div className={cn("w-full", className)}>
      <div
        className={cn(
          "relative border-2 border-dashed rounded-xl p-8 text-center smooth-transition",
          isDragging 
            ? "border-primary bg-primary/5" 
            : "border-border hover:border-primary/50 hover:bg-secondary/50",
          "cursor-pointer"
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => document.getElementById("file-upload")?.click()}
      >
        <input
          id="file-upload"
          type="file"
          accept={accept}
          multiple={multiple}
          className="hidden"
          onChange={handleFileChange}
        />
        
        <div className="flex flex-col items-center justify-center py-8">
          <div className={cn(
            "w-16 h-16 mb-4 rounded-full flex items-center justify-center smooth-transition",
            isDragging ? "bg-primary/20 text-primary" : "bg-secondary text-muted-foreground"
          )}>
            <Upload className="w-8 h-8" />
          </div>
          
          <h3 className="text-lg font-medium mb-2">
            {isDragging ? "Drop your files here" : "Drag & drop files here"}
          </h3>
          
          <p className="text-sm text-muted-foreground mb-4">
            or <span className="text-primary">browse files</span> on your computer
          </p>
          
          <div className="text-xs text-muted-foreground">
            {multiple 
              ? `Accepts ${accept.replace(/\./g, "")} files up to ${maxSize}MB each` 
              : `Accepts ${accept.replace(/\./g, "")} file up to ${maxSize}MB`}
          </div>
        </div>
      </div>
      
      {error && (
        <div className="mt-4 p-3 bg-destructive/10 text-destructive rounded-lg text-sm flex items-start">
          <AlertCircle className="w-5 h-5 mr-2 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}
      
      {files.length > 0 && (
        <div className="mt-6">
          <h4 className="text-sm font-medium mb-3">Selected Files</h4>
          <div className="space-y-2">
            {files.map((file, index) => (
              <div key={index} className="flex items-center p-3 bg-secondary/50 rounded-lg animate-fade-in animate-once">
                <div className="p-2 bg-background rounded">
                  <File className="w-5 h-5 text-primary" />
                </div>
                <div className="ml-3 flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{file.name}</div>
                  <div className="text-xs text-muted-foreground">{formatFileSize(file.size)}</div>
                </div>
                <CheckCircle2 className="w-5 h-5 text-green-500 mr-2" />
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(index);
                  }}
                  className="p-1 text-muted-foreground hover:text-foreground smooth-transition"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M18 6 6 18M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
