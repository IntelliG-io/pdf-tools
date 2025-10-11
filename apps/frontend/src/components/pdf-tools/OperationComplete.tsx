import React from "react";
import { Link } from "react-router-dom";
import { Check, Info } from "lucide-react";
import { cn } from "@/lib/utils";

interface OperationCompleteProps {
  fileName: string;
  fileType: string;
  fileUrl: string | null;
  onReset: () => void;
  additionalInfo?: React.ReactNode;
}

const OperationComplete: React.FC<OperationCompleteProps> = ({
  fileName,
  fileType,
  fileUrl,
  onReset,
  additionalInfo
}) => {
  return (
    <div className="max-w-xl mx-auto w-full animate-fade-in animate-once text-center">
      <div className="mb-6">
        <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <Check className="w-10 h-10 text-green-600" />
        </div>
        <h3 className="text-2xl font-bold mb-2">Processing Complete!</h3>
        <p className="text-muted-foreground mb-6">
          Your file has been successfully processed and is ready for download.
        </p>
      </div>
      
      <div className="p-6 border rounded-lg bg-secondary/30 mb-8">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center">
            <div className="p-2 bg-primary/10 rounded">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
                <path d="M13 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8" />
                <path d="M13 3v5h5" />
              </svg>
            </div>
            <div className="ml-3">
              <div className="text-sm font-medium">
                {fileName}
              </div>
              <div className="text-xs text-muted-foreground">
                {fileType}
              </div>
            </div>
          </div>
          <a 
            href={fileUrl || "#"} 
            download={fileName}
            className={cn(
              "bg-primary hover:bg-primary/90 text-white px-3 py-1 rounded text-sm font-medium shadow-sm flex items-center smooth-transition",
              !fileUrl && "opacity-50 pointer-events-none"
            )}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" x2="12" y1="15" y2="3" />
            </svg>
            Download
          </a>
        </div>
        
        <div className="flex items-start pt-4 border-t border-border">
          <Info className="w-5 h-5 text-muted-foreground mr-3 mt-0.5" />
          <div className="text-xs text-muted-foreground text-left">
            Your file has been processed securely on our servers and will be automatically deleted after 24 hours for your privacy.
          </div>
        </div>
        
        {additionalInfo && (
          <div className="mt-4">
            {additionalInfo}
          </div>
        )}
      </div>
      
      <div className="flex flex-col sm:flex-row gap-4 justify-center">
        <button 
          className="bg-secondary hover:bg-secondary/80 text-foreground px-6 py-3 rounded-lg font-medium shadow-sm flex items-center justify-center smooth-transition"
          onClick={onReset}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-2">
            <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
            <path d="M3 3v5h5" />
            <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
            <path d="M16 21h5v-5" />
          </svg>
          Process Another File
        </button>
        <Link
          to="/"
          className="bg-white hover:bg-white/90 text-foreground border border-border px-6 py-3 rounded-lg font-medium shadow-sm flex items-center justify-center smooth-transition"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-2">
            <path d="M3 9h18v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9Z" />
            <path d="M3 9V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v4" />
            <path d="M13 13h4" />
            <path d="M13 17h4" />
            <path d="M9 13h.01" />
            <path d="M9 17h.01" />
          </svg>
          Back to All Tools
        </Link>
      </div>
    </div>
  );
};

export default OperationComplete;
