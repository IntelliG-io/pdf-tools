import React, { useState, useEffect, useRef, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { File as FileIcon, FileText } from 'lucide-react';
import * as pdfjsLib from 'pdfjs-dist';

// Set the worker path to use web worker for PDF parsing
pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;

interface PdfFirstPagePreviewProps {
  file: File | null;
  className?: string;
}

/**
 * A component that displays only the first page of a PDF document
 * using PDF.js to render it on a canvas
 */
const PdfFirstPagePreview: React.FC<PdfFirstPagePreviewProps> = ({
  file,
  className
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pageRendered, setPageRendered] = useState(false);
  const [fallbackUrl, setFallbackUrl] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  // Generate URL for the fallback iframe when there's an error
  useEffect(() => {
    if (file && error) {
      const url = URL.createObjectURL(file);
      setFallbackUrl(url);
      
      return () => {
        URL.revokeObjectURL(url);
      };
    }
  }, [file, error]);

  // Function to render the first page of the PDF
  const renderPage = useCallback(async (pdfFile: File) => {
    try {
      setLoading(true);
      setError(null);
      setPageRendered(false);

      const fileData = await pdfFile.arrayBuffer();
      const pdf = await pdfjsLib.getDocument({ data: fileData }).promise;
      
      // Get only the first page
      const page = await pdf.getPage(1);
      
      // Prepare canvas for rendering
      const canvas = canvasRef.current;
      if (!canvas) return;
      
      const context = canvas.getContext('2d');
      if (!context) return;
      
      // Calculate the scale to fit the canvas within its container
      const viewport = page.getViewport({ scale: 1.0 });
      const containerWidth = canvas.parentElement?.clientWidth || 800;
      const containerHeight = canvas.parentElement?.clientHeight || 600;
      
      // Determine the appropriate scale based on both width and height constraints
      // to maintain aspect ratio while fitting in the container
      const scaleX = containerWidth / viewport.width;
      const scaleY = containerHeight / viewport.height;
      const scale = Math.min(scaleX, scaleY) * 0.95; // Add a small margin (95%)
      
      const scaledViewport = page.getViewport({ scale });
      
      // Set canvas dimensions to match the scaled viewport
      canvas.width = scaledViewport.width;
      canvas.height = scaledViewport.height;
      
      // Center the canvas if it's smaller than the container
      if (canvas.parentElement) {
        canvas.style.display = 'block';
        canvas.style.margin = '0 auto';
      }
      
      // Render the PDF page to the canvas
      const renderContext = {
        canvasContext: context,
        viewport: scaledViewport
      };
      
      await page.render(renderContext).promise;
      setPageRendered(true);
      setLoading(false);
    } catch (err) {
      console.error('Error rendering PDF:', err);
      setError('Failed to render PDF preview');
      setLoading(false);
    }
  }, []);

  // Effect to render the PDF when the file changes
  useEffect(() => {
    if (file) {
      renderPage(file);
    } else {
      setPageRendered(false);
    }
  }, [file, renderPage]);

  // Create a resize observer to handle container size changes
  useEffect(() => {
    if (!canvasRef.current || !file) return;

    const resizeObserver = new ResizeObserver(() => {
      // Re-render the page when the container size changes
      if (file) {
        renderPage(file);
      }
    });

    // Start observing once the canvas element and its parent exist
    const canvasParent = canvasRef.current.parentElement;
    if (canvasParent) {
      resizeObserver.observe(canvasParent);
    }

    return () => {
      resizeObserver.disconnect();
    };
  }, [file, renderPage]);

  // Loading state
  if (loading) {
    return (
      <div className={cn("flex items-center justify-center w-full h-full bg-muted/10 rounded border", className)}>
        <div className="text-center p-4">
          <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full mx-auto mb-3"></div>
          <p className="text-sm text-muted-foreground">Loading document preview...</p>
        </div>
      </div>
    );
  }

  // Error state with fallback to iframe
  if (error) {
    
    return (
      <div className={cn("overflow-hidden rounded-lg border", className)}>
        <div className="bg-muted/20 px-3 py-2 border-b flex items-center justify-between">
          <div className="flex items-center">
            <FileText className="w-4 h-4 text-primary mr-2" />
            <span className="text-sm font-medium truncate max-w-[200px]">{file?.name}</span>
          </div>
          <span className="text-xs text-muted-foreground">{file ? Math.round(file.size / 1024) : 0} KB</span>
        </div>
        <div className="relative bg-white">
          <div className="aspect-[4/3] w-full">
            {fallbackUrl ? (
              <>
                <p className="text-xs text-amber-600 p-2 bg-amber-50">
                  Using compatibility mode for preview. Only showing first page.
                </p>
                <iframe 
                  src={`${fallbackUrl}#page=1&view=FitH&toolbar=0&navpanes=0`}
                  className="w-full h-full border-0"
                  title="PDF Preview (Fallback)"
                  style={{ height: 'calc(100% - 24px)' }}
                />
              </>
            ) : (
              <div className="flex items-center justify-center h-full">
                <p className="text-sm text-destructive">Failed to render PDF preview</p>
              </div>
            )}
          </div>
        </div>
        <div className="bg-muted/20 px-3 py-2 border-t">
          <p className="text-xs text-center text-muted-foreground">Document first page preview</p>
        </div>
      </div>
    );
  }

  // No file selected
  if (!file) {
    return (
      <div className={cn("flex items-center justify-center w-full h-full bg-muted/10 rounded border border-dashed", className)}>
        <div className="text-center p-4">
          <FileIcon className="w-10 h-10 text-muted-foreground mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">No document selected</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("overflow-hidden rounded-lg border", className)}>
      <div className="bg-muted/20 px-3 py-2 border-b flex items-center justify-between">
        <div className="flex items-center">
          <FileText className="w-4 h-4 text-primary mr-2" />
          <span className="text-sm font-medium truncate max-w-[200px]">{file.name}</span>
        </div>
        <span className="text-xs text-muted-foreground">{Math.round(file.size / 1024)} KB</span>
      </div>
      <div className="relative bg-white">
        <div className="aspect-[4/3] w-full flex items-center justify-center">
          {!pageRendered && !loading ? (
            <p className="text-sm text-muted-foreground">Preparing preview...</p>
          ) : (
            <canvas 
              ref={canvasRef} 
              className="max-w-full max-h-full object-contain shadow-md rounded-sm border"
              style={{ 
                backgroundColor: 'white',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
              }}
            />
          )}
        </div>
      </div>
      <div className="bg-muted/20 px-3 py-2 border-t">
        <p className="text-xs text-center text-muted-foreground">Document first page preview</p>
      </div>
    </div>
  );
};

export default PdfFirstPagePreview;
