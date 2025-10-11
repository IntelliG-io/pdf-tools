import React from "react";
import { cn } from "@/lib/utils";

interface PDFFileListProps {
  files: File[];
  fileOrder: number[];
  onMoveFile: (index: number, direction: 'up' | 'down') => void;
}

const PDFFileList: React.FC<PDFFileListProps> = ({
  files,
  fileOrder,
  onMoveFile
}) => {
  return (
    <div className="border rounded-lg p-4 bg-secondary/30">
      {fileOrder.map((fileIndex, orderIndex) => {
        const file = files[fileIndex];
        return (
          <div key={orderIndex} className="flex items-center p-3 bg-background rounded-lg mb-2 group">
            <div className="p-2 bg-secondary rounded">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
                <path d="M13 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8" />
                <path d="M13 3v5h5" />
              </svg>
            </div>
            <div className="ml-3 flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{file.name}</div>
            </div>
            <div className="flex items-center">
              <button 
                className={cn(
                  "p-1 smooth-transition",
                  orderIndex > 0 
                    ? "text-muted-foreground hover:text-foreground" 
                    : "text-muted-foreground/30 cursor-not-allowed"
                )}
                onClick={() => onMoveFile(orderIndex, 'up')}
                disabled={orderIndex === 0}
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m5 9 4-4 4 4" />
                  <path d="M9 5v14" />
                </svg>
              </button>
              <button 
                className={cn(
                  "p-1 smooth-transition",
                  orderIndex < files.length - 1 
                    ? "text-muted-foreground hover:text-foreground" 
                    : "text-muted-foreground/30 cursor-not-allowed"
                )}
                onClick={() => onMoveFile(orderIndex, 'down')}
                disabled={orderIndex === files.length - 1}
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m5 15 4 4 4-4" />
                  <path d="M9 5v14" />
                </svg>
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default PDFFileList;
