import React from 'react';
import { cn } from '@/lib/utils';
import PdfPagePreview from './PdfPagePreview';

interface PdfRotationPreviewProps {
  file: File | null;
  rotations: { page: number; degrees: number }[];
  className?: string;
}

/**
 * Component that displays a grid of rotated PDF pages based on rotation configurations
 */
const PdfRotationPreview: React.FC<PdfRotationPreviewProps> = ({
  file,
  rotations,
  className
}) => {
  if (!file || rotations.length === 0) {
    return (
      <div className={cn("flex items-center justify-center w-full h-64 bg-muted/10 rounded border border-dashed", className)}>
        <div className="text-center">
          <p className="text-sm text-muted-foreground">No pages configured for rotation</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("w-full", className)}>
      <h3 className="text-sm font-medium mb-3">Preview of Rotated Pages</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        {rotations.map((rotation, index) => (
          <div 
            key={`preview-container-${rotation.page}-${index}`} 
            className={cn(
              "border rounded shadow-sm overflow-hidden",
              rotation.degrees === 0 ? "border-dashed border-muted" : ""
            )}
          >
            <PdfPagePreview
              key={`page-preview-${rotation.page}-${index}`}
              file={file}
              pageNumber={rotation.page}
              rotation={rotation.degrees}
              className="aspect-[3/4] h-auto"
            />
          </div>
        ))}
      </div>
      {rotations.length > 0 && (
        <p className="text-xs text-muted-foreground mt-2 text-center">
          These previews show how your pages will appear after applying the rotations
          {rotations.some(r => r.degrees === 0) && " (pages with 0° rotation will remain unchanged)"}
        </p>
      )}
    </div>
  );
};

export default PdfRotationPreview;
