import React from 'react';
import { ChevronLeft, ChevronRight, RotateCw } from 'lucide-react';
import { cn } from '@/lib/utils';

interface PageSelectorProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  className?: string;
  rotations: { page: number; degrees: number }[];
}

const PageSelector: React.FC<PageSelectorProps> = ({
  currentPage,
  totalPages,
  onPageChange,
  className,
  rotations
}) => {
  const handlePreviousPage = () => {
    if (currentPage > 1) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      onPageChange(currentPage + 1);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value);
    if (!isNaN(value) && value >= 1 && value <= totalPages) {
      onPageChange(value);
    }
  };

  // Helper to check if a page has a rotation
  const getPageRotation = (page: number) => {
    return rotations?.find(r => r.page === page)?.degrees || 0;
  };

  // Generate page buttons
  const generatePageButtons = () => {
    const buttons = [];
    const maxVisibleButtons = 5;

    if (totalPages <= maxVisibleButtons) {
      // Show all pages if total is less than the max visible
      for (let i = 1; i <= totalPages; i++) {
        const rotation = getPageRotation(i);
        buttons.push(
          <button
            key={i}
            onClick={() => onPageChange(i)}
            className={cn(
              "relative h-8 w-8 flex items-center justify-center rounded hover:bg-muted transition-colors",
              currentPage === i ? "bg-primary text-primary-foreground" : "text-foreground",
              rotation > 0 && "ring-1 ring-primary ring-offset-1"
            )}
          >
            {i}
            {rotation > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-primary rounded-full flex items-center justify-center">
                <RotateCw className="w-3 h-3 text-white" />
              </span>
            )}
          </button>
        );
      }
    } else {
      // Show first, last, and pages around current
      const firstPageRotation = getPageRotation(1);
      buttons.push(
        <button
          key={1}
          onClick={() => onPageChange(1)}
          className={cn(
            "relative h-8 w-8 flex items-center justify-center rounded hover:bg-muted transition-colors",
            currentPage === 1 ? "bg-primary text-primary-foreground" : "text-foreground",
            firstPageRotation > 0 && "ring-1 ring-primary ring-offset-1"
          )}
        >
          1
          {firstPageRotation > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-primary rounded-full flex items-center justify-center">
              <RotateCw className="w-3 h-3 text-white" />
            </span>
          )}
        </button>
      );

      // Calculate range of pages to show
      let startPage = Math.max(2, currentPage - 1);
      let endPage = Math.min(totalPages - 1, startPage + 2);
      
      // Adjust start if end is too close to total
      if (endPage === totalPages - 1) {
        startPage = Math.max(2, endPage - 2);
      }

      // Show ellipsis if needed
      if (startPage > 2) {
        buttons.push(
          <span key="ellipsis1" className="h-8 w-8 flex items-center justify-center text-muted-foreground">
            ...
          </span>
        );
      }

      // Show pages around current
      for (let i = startPage; i <= endPage; i++) {
        const pageRotation = getPageRotation(i);
        buttons.push(
          <button
            key={i}
            onClick={() => onPageChange(i)}
            className={cn(
              "relative h-8 w-8 flex items-center justify-center rounded hover:bg-muted transition-colors",
              currentPage === i ? "bg-primary text-primary-foreground" : "text-foreground",
              pageRotation > 0 && "ring-1 ring-primary ring-offset-1"
            )}
          >
            {i}
            {pageRotation > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-primary rounded-full flex items-center justify-center">
                <RotateCw className="w-3 h-3 text-white" />
              </span>
            )}
          </button>
        );
      }

      // Show ellipsis if needed
      if (endPage < totalPages - 1) {
        buttons.push(
          <span key="ellipsis2" className="h-8 w-8 flex items-center justify-center text-muted-foreground">
            ...
          </span>
        );
      }

      // Last page
      if (totalPages > 1) {
        const lastPageRotation = getPageRotation(totalPages);
        buttons.push(
          <button
            key={totalPages}
            onClick={() => onPageChange(totalPages)}
            className={cn(
              "relative h-8 w-8 flex items-center justify-center rounded hover:bg-muted transition-colors",
              currentPage === totalPages ? "bg-primary text-primary-foreground" : "text-foreground",
              lastPageRotation > 0 && "ring-1 ring-primary ring-offset-1"
            )}
          >
            {totalPages}
            {lastPageRotation > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-primary rounded-full flex items-center justify-center">
                <RotateCw className="w-3 h-3 text-white" />
              </span>
            )}
          </button>
        );
      }
    }

    return buttons;
  };

  return (
    <div className={cn("flex items-center justify-center space-x-2", className)}>
      <button
        onClick={handlePreviousPage}
        disabled={currentPage <= 1}
        className={cn(
          "h-8 w-8 flex items-center justify-center rounded hover:bg-muted transition-colors",
          currentPage <= 1 ? "text-muted-foreground opacity-50 cursor-not-allowed" : "text-foreground"
        )}
        aria-label="Previous page"
      >
        <ChevronLeft className="h-4 w-4" />
      </button>

      <div className="flex items-center space-x-1">
        {generatePageButtons()}
      </div>

      <button
        onClick={handleNextPage}
        disabled={currentPage >= totalPages}
        className={cn(
          "h-8 w-8 flex items-center justify-center rounded hover:bg-muted transition-colors",
          currentPage >= totalPages ? "text-muted-foreground opacity-50 cursor-not-allowed" : "text-foreground"
        )}
        aria-label="Next page"
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  );
};

export default PageSelector;
