import React from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface StepProgressProps {
  steps: string[];
  currentStep: number;
}

const StepProgress: React.FC<StepProgressProps> = ({ steps, currentStep }) => {
  return (
    <div className="max-w-2xl mx-auto mb-16">
      <div className="flex items-center justify-center">
        {steps.map((stepText, index) => (
          <React.Fragment key={index}>
            <div className="flex flex-col items-center">
              <div 
                className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center text-sm mb-2 smooth-transition",
                  currentStep > index + 1 
                    ? "bg-primary text-white" 
                    : currentStep === index + 1 
                      ? "bg-primary/10 text-primary border border-primary" 
                      : "bg-secondary text-muted-foreground"
                )}
              >
                {currentStep > index + 1 ? (
                  <Check className="w-4 h-4" />
                ) : (
                  index + 1
                )}
              </div>
              <span 
                className={cn(
                  "text-xs text-center max-w-[100px] hidden sm:block smooth-transition",
                  currentStep === index + 1 ? "text-primary font-medium" : "text-muted-foreground"
                )}
              >
                {stepText}
              </span>
            </div>
            
            {index < steps.length - 1 && (
              <div 
                className={cn(
                  "w-16 h-px mx-2 smooth-transition",
                  currentStep > index + 1 ? "bg-primary" : "bg-border"
                )}
              />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};

export default StepProgress;
