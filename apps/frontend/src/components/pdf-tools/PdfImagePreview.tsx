import React from 'react';
import { cn } from '@/lib/utils';
import { Loader } from 'lucide-react';

interface PdfImagePreviewProps {
  imageUrl: string | null;
  pageNumber: number;
  rotation: number;
  className?: string;
}

/**
 * A component that displays a single PDF page image with the specified rotation
 */
const PdfImagePreview: React.FC<PdfImagePreviewProps> = ({
  imageUrl,
  pageNumber,
  rotation,
  className
}) => {
  // Loading or error state
  if (!imageUrl) {
    return (
      <div className={cn("flex items-center justify-center w-full h-full bg-muted/10 rounded border border-dashed", className)}>
        <div className="text-center">
          <Loader className="w-4 h-4 animate-spin mx-auto mb-2" />
          <p className="text-xs text-muted-foreground">Loading page {pageNumber}...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("relative flex flex-col border rounded overflow-hidden", className)}>
      {/* Header */}
      <div className={cn(
        "px-3 py-1.5 text-xs font-medium border-b flex items-center justify-between",
        rotation > 0 ? "bg-muted/20" : "bg-white/60"
      )}>
        <span>Page {pageNumber}</span>
        <div className={cn(
          "flex items-center",
          rotation > 0 ? "text-primary" : "text-muted-foreground"
        )}>
          {rotation > 0 ? (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1">
                <path d="M21 2v6h-6"></path>
                <path d="M3 12a9 9 0 0 1 15-6.7L21 8"></path>
                <path d="M3 12a9 9 0 0 0 6.7 15L13 21"></path>
                <path d="M14 21h6v-6"></path>
              </svg>
              <span>{rotation}°</span>
            </>
          ) : (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1">
                <rect x="4" y="4" width="16" height="16" rx="2"></rect>
              </svg>
              <span>No rotation</span>
            </>
          )}
        </div>
      </div>
      
      {/* Content area with fixed aspect ratio */}
      <div className="relative w-full aspect-[3/4] bg-white">
        {/* This is the actual content that rotates */}
        <div 
          className="absolute inset-0 flex items-center justify-center"
          style={{
            transform: rotation ? `rotate(${rotation}deg)` : 'none',
            transformOrigin: 'center center',
            transition: 'transform 0.3s ease',
          }}
        >
          <img 
            src={imageUrl} 
            alt={`Page ${pageNumber}`} 
            className={cn(
              "max-h-full max-w-full object-contain",
              rotation === 90 || rotation === 270 ? "scale-75" : "scale-90"
            )}
          />
        </div>
      </div>
    </div>
  );
};

export default PdfImagePreview;
