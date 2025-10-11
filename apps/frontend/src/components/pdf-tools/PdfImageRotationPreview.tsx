import React from 'react';
import { cn } from '@/lib/utils';
import PdfImagePreview from './PdfImagePreview';

interface PdfImageRotationPreviewProps {
  images: string[];
  rotations: { page: number; degrees: number }[];
  className?: string;
}

/**
 * Component that displays a grid of rotated PDF page images based on rotation configurations
 */
const PdfImageRotationPreview: React.FC<PdfImageRotationPreviewProps> = ({
  images,
  rotations,
  className
}) => {
  if (!images || images.length === 0 || rotations.length === 0) {
    return (
      <div className={cn("flex items-center justify-center w-full h-64 bg-muted/10 rounded border border-dashed", className)}>
        <div className="text-center">
          <p className="text-sm text-muted-foreground">No pages configured for rotation</p>
        </div>
      </div>
    );
  }

  // Filter rotations to only include pages that we have images for
  const validRotations = rotations.filter(rotation => 
    rotation.page > 0 && rotation.page <= images.length
  );

  return (
    <div className={cn("w-full", className)}>
      <h3 className="text-sm font-medium mb-3">Preview of Rotated Pages</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        {validRotations.map((rotation, index) => (
          <div 
            key={`preview-container-${rotation.page}-${index}`} 
            className={cn(
              "overflow-hidden",
              rotation.degrees === 0 ? "border-dashed border-muted" : ""
            )}
          >
            <PdfImagePreview
              key={`image-preview-${rotation.page}-${index}`}
              imageUrl={images[rotation.page - 1] || null}
              pageNumber={rotation.page}
              rotation={rotation.degrees}
              className="aspect-[3/4] h-auto"
            />
          </div>
        ))}
      </div>
      {validRotations.length > 0 && (
        <p className="text-xs text-muted-foreground mt-2 text-center">
          These previews show how your pages will appear after applying the rotations
          {validRotations.some(r => r.degrees === 0) && " (pages with 0° rotation will remain unchanged)"}
        </p>
      )}
    </div>
  );
};

export default PdfImageRotationPreview;
