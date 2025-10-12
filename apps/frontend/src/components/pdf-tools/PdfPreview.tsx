import React, { useState, useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';

interface PdfPreviewProps {
  file: File | null;
  selectedPage: number;
  rotations: { page: number; degrees: number }[];
  className?: string;
  totalPages: number;
}

const PdfPreview: React.FC<PdfPreviewProps> = ({ 
  file, 
  selectedPage, 
  rotations, 
  className,
  totalPages 
}) => {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Generate URL for the PDF file
  useEffect(() => {
    if (file) {
      setPreviewLoading(true);
      const url = URL.createObjectURL(file);
      setPdfUrl(url);
      
      return () => {
        URL.revokeObjectURL(url);
      };
    } else {
      setPdfUrl(null);
    }
  }, [file]);

  // Find the rotation for the selected page
  const getRotationForPage = (page: number): number => {
    const rotation = rotations.find(r => r.page === page);
    return rotation ? rotation.degrees : 0;
  };

  const currentRotation = getRotationForPage(selectedPage);

  // Calculate container adjustments based on rotation
  const getContainerStyles = () => {
    // For 90 or 270 degree rotations, we need to adjust the aspect ratio
    if (currentRotation === 90 || currentRotation === 270) {
      return {
        paddingBottom: '133.33%', // 4:3 aspect ratio inverted
        height: 0,
        width: '75%', // Adjust width to maintain proper sizing
        margin: '0 auto',
      };
    }
    return {};
  };

  // Loading state when PDF is being loaded
  if (previewLoading && !pdfUrl) {
    return (
      <div className={cn("flex items-center justify-center w-full h-64 bg-muted/20 rounded-lg border border-dashed", className)}>
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full mx-auto mb-2"></div>
          <p className="text-sm text-muted-foreground">Loading document preview...</p>
        </div>
      </div>
    );
  }

  // No file selected
  if (!file || !pdfUrl) {
    return (
      <div className={cn("flex items-center justify-center w-full h-64 bg-muted/20 rounded-lg border border-dashed", className)}>
        <div className="text-center">
          <p className="text-sm text-muted-foreground">No document selected</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("w-full overflow-hidden rounded-lg border", className)}>
      <div className="bg-muted/30 p-2 border-b flex items-center justify-between">
        <div className="text-sm font-medium">Page {selectedPage} Preview</div>
        <div className="text-xs text-muted-foreground">
          {currentRotation > 0 && `Rotation: ${currentRotation}°`}
        </div>
      </div>
      <div className="relative bg-white p-4 flex items-center justify-center">
        {/* Paper background with grid for better orientation */}
        <div className="absolute inset-4 bg-gray-50" style={{ 
          backgroundImage: 'linear-gradient(rgba(0, 0, 0, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 0, 0, 0.05) 1px, transparent 1px)',
          backgroundSize: '20px 20px'
        }}></div>
        
        {/* Rotation indicators */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-2 left-1/2 -translate-x-1/2 text-xs font-bold text-gray-400">Top</div>
          <div className="absolute bottom-2 left-1/2 -translate-x-1/2 text-xs font-bold text-gray-400">Bottom</div>
          <div className="absolute left-2 top-1/2 -translate-y-1/2 text-xs font-bold text-gray-400">Left</div>
          <div className="absolute right-2 top-1/2 -translate-y-1/2 text-xs font-bold text-gray-400">Right</div>
        </div>
        
        {/* Container with proper aspect ratio */}
        <div 
          ref={containerRef}
          className="relative w-full z-10 overflow-hidden bg-white shadow-md border"
          style={{
            aspectRatio: currentRotation === 90 || currentRotation === 270 ? '3/4' : '4/3',
            ...getContainerStyles()
          }}
        >
          {/* This wrapper is what gets rotated */}
          <div 
            className="absolute inset-0 flex items-center justify-center"
            style={{
              transform: `rotate(${currentRotation}deg)`,
              transformOrigin: 'center center',
              transition: 'transform 0.5s ease',
              // Adjust dimensions for rotated state
              width: currentRotation === 90 || currentRotation === 270 ? '133.33%' : '100%',
              height: currentRotation === 90 || currentRotation === 270 ? '75%' : '100%',
              left: currentRotation === 90 || currentRotation === 270 ? '-16.665%' : '0',
              top: currentRotation === 90 || currentRotation === 270 ? '12.5%' : '0',
            }}
          >
            {/* Page corners for visual reference */}
            <div className="absolute top-0 left-0 w-8 h-8 border-t-4 border-l-4 border-blue-500 opacity-50 z-10"></div>
            <div className="absolute top-0 right-0 w-8 h-8 border-t-4 border-r-4 border-blue-500 opacity-50 z-10"></div>
            <div className="absolute bottom-0 left-0 w-8 h-8 border-b-4 border-l-4 border-blue-500 opacity-50 z-10"></div>
            <div className="absolute bottom-0 right-0 w-8 h-8 border-b-4 border-r-4 border-blue-500 opacity-50 z-10"></div>
            
            <iframe
              src={`${pdfUrl}#page=${selectedPage}`}
              className="w-full h-full"
              style={{
                border: 'none',
                backgroundColor: 'white',
                boxShadow: '0 0 10px rgba(0,0,0,0.1)'
              }}
              title={`PDF Preview - Page ${selectedPage}`}
              onLoad={() => setPreviewLoading(false)}
            />
          </div>
        </div>
      </div>
      <div className="bg-muted/30 p-2 border-t text-xs text-muted-foreground text-center">
        {file.name} - Page {selectedPage} of {totalPages} - {Math.round(file.size / 1024)} KB
      </div>
    </div>
  );
};

export default PdfPreview;
