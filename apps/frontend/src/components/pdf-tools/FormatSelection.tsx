import React from "react";
import { cn } from "@/lib/utils";

export interface FormatOption {
  id: string;
  name: string;
  extension: string;
  icon: string;
  color: string;
}

interface FormatSelectionProps {
  formats: FormatOption[];
  selectedFormat: string | null;
  onSelectFormat: (formatId: string) => void;
}

const FormatSelection: React.FC<FormatSelectionProps> = ({
  formats,
  selectedFormat,
  onSelectFormat
}) => {
  return (
    <div className="max-w-xl mx-auto w-full animate-fade-in animate-once">
      <h3 className="text-lg font-medium mb-4">Select Output Format</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        {formats.map((format) => (
          <button
            key={format.id}
            className={cn(
              "p-4 rounded-lg border flex flex-col items-center text-center smooth-transition",
              selectedFormat === format.id
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/50 hover:bg-secondary/50"
            )}
            onClick={() => onSelectFormat(format.id)}
          >
            <div className={cn("w-10 h-10 flex items-center justify-center rounded text-white font-bold mb-2", format.color)}>
              {format.icon}
            </div>
            <span className="font-medium">{format.name}</span>
            <span className="text-xs text-muted-foreground">{format.extension}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default FormatSelection;
