import React, { useState, useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';
import { RotateCw } from 'lucide-react';

interface PdfPagePreviewProps {
  file: File | null;
  pageNumber: number;
  rotation: number;
  className?: string;
}

/**
 * A component that displays a single PDF page with the specified rotation
 */
const PdfPagePreview: React.FC<PdfPagePreviewProps> = ({
  file,
  pageNumber,
  rotation,
  className
}) => {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Generate URL for the PDF file
  useEffect(() => {
    if (file) {
      setLoading(true);
      setError(null);
      const url = URL.createObjectURL(file);
      setPdfUrl(url);
      
      return () => {
        URL.revokeObjectURL(url);
      };
    } else {
      setPdfUrl(null);
    }
  }, [file]);

  // Loading state
  if (loading && !pdfUrl) {
    return (
      <div className={cn("flex items-center justify-center w-full h-full bg-muted/10 rounded border", className)}>
        <div className="text-center">
          <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full mx-auto mb-2"></div>
          <p className="text-xs text-muted-foreground">Loading page {pageNumber}...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={cn("flex items-center justify-center w-full h-full bg-destructive/10 rounded border border-destructive/20", className)}>
        <div className="text-center p-4">
          <p className="text-xs text-destructive">Error: {error}</p>
        </div>
      </div>
    );
  }

  // No file selected
  if (!file || !pdfUrl) {
    return (
      <div className={cn("flex items-center justify-center w-full h-full bg-muted/10 rounded border border-dashed", className)}>
        <div className="text-center">
          <p className="text-xs text-muted-foreground">No preview available</p>
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
          {rotation === 0 ? (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1">
                <rect x="4" y="4" width="16" height="16" rx="2"></rect>
              </svg>
              <span>No rotation</span>
            </>
          ) : (
            <>
              <RotateCw className="w-3 h-3 mr-1" />
              <span>{rotation}°</span>
            </>
          )}
        </div>
      </div>
      
      {/* Content area with fixed aspect ratio */}
      <div className="relative w-full flex-1 bg-white" style={{ minHeight: "180px" }}>
        {/* This is the actual content that rotates */}
        <div 
          className="absolute inset-0 flex items-center justify-center"
          style={{
            transform: rotation ? `rotate(${rotation}deg)` : 'none',
            transformOrigin: 'center center',
            transition: 'transform 0.3s ease',
            // Adjust scale for rotated pages
            scale: rotation === 90 || rotation === 270 ? '0.85' : '1'
          }}
        >
          <iframe
            ref={iframeRef}
            src={`${pdfUrl}#page=${pageNumber}&view=FitH&scrollbar=0`}
            className="absolute inset-0 w-full h-full border-0"
            onLoad={() => {
              setLoading(false);
              
              // Try to access iframe contents to remove scrollbars
              try {
                if (iframeRef.current) {
                  const iframeDocument = iframeRef.current.contentDocument || 
                                        (iframeRef.current.contentWindow?.document);
                  if (iframeDocument) {
                    // Add custom CSS to iframe document to hide scrollbars
                    const style = iframeDocument.createElement('style');
                    style.textContent = `
                      body, html {
                        margin: 0 !important;
                        padding: 0 !important;
                        overflow: hidden !important;
                      }
                      ::-webkit-scrollbar {
                        display: none !important;
                      }
                      /* PDF.js specific */
                      .pdfViewer .page {
                        margin: 0 !important;
                        border: none !important;
                      }
                      #viewerContainer, #viewer {
                        overflow: hidden !important;
                      }
                    `;
                    iframeDocument.head.appendChild(style);
                  }
                }
              } catch (e) {
                // Silently fail - this might happen due to cross-origin issues
                console.log("Could not modify iframe style", e);
              }
            }}
            onError={() => setError("Failed to load PDF page")}
            title={`PDF Page ${pageNumber}`}
            style={{
              pointerEvents: "none" // Prevent scrolling by disabling interaction
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default PdfPagePreview;
