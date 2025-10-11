import React from 'react';
import { ArrowRight, Loader2 } from 'lucide-react';

interface ProcessingButtonProps {
  onClick: () => void;
  isProcessing: boolean;
  disabled?: boolean;
  text: string;
}

const ProcessingButton: React.FC<ProcessingButtonProps> = ({
  onClick,
  isProcessing,
  disabled = false,
  text
}) => {
  return (
    <div className="mt-6">
      <button 
        className="bg-primary hover:bg-primary/90 text-white px-6 py-3 rounded-lg font-medium shadow-lg shadow-primary/20 flex items-center justify-center smooth-transition disabled:opacity-50 disabled:cursor-not-allowed"
        onClick={onClick}
        disabled={isProcessing || disabled}
      >
        {isProcessing ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Processing...
          </>
        ) : (
          <>
            {text}
            <ArrowRight className="ml-2 w-4 h-4" />
          </>
        )}
      </button>
    </div>
  );
};

export default ProcessingButton;
