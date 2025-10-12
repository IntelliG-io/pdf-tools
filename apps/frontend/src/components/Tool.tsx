
import React from "react";
import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface ToolProps {
  title: string;
  description: string;
  icon: LucideIcon;
  bgClass?: string;
  route: string;
  className?: string;
  comingSoon?: boolean;
  style?: React.CSSProperties;
}

const Tool: React.FC<ToolProps> = ({
  title,
  description,
  icon: Icon,
  bgClass = "bg-primary/10",
  route,
  className,
  comingSoon = false,
  style,
}) => {
  if (comingSoon) {
    return (
      <div 
        className={cn(
          "group relative overflow-hidden p-6 rounded-xl glass-card opacity-80 cursor-not-allowed",
          className
        )}
        style={style}
      >
      <div className="absolute -right-20 -top-20 w-40 h-40 rounded-full blur-3xl opacity-20 group-hover:opacity-30 smooth-transition" 
        style={{ background: `radial-gradient(circle, hsl(var(--primary)) 0%, transparent 70%)` }}
      />
      
      <div className={cn("w-12 h-12 rounded-lg flex items-center justify-center mb-4 text-primary", bgClass)}>
        <Icon className="w-6 h-6" />
      </div>
      
      <h3 className="text-lg font-medium mb-2 group-hover:text-primary smooth-transition">{title}</h3>
      
      <p className="text-sm text-muted-foreground mb-4">{description}</p>
      
        <div className="flex items-center justify-center mt-4">
          <div className="px-3 py-1 text-xs font-semibold text-primary bg-primary/10 rounded-full">
            Coming Soon
          </div>
        </div>
      </div>
    );
  }
  
  return (
    <Link
      to={route}
      className={cn(
        "group relative overflow-hidden p-6 rounded-xl glass-card hover:scale-[1.02] hover:shadow-md smooth-transition",
        className
      )}
      style={style}
    >
      <div className="absolute -right-20 -top-20 w-40 h-40 rounded-full blur-3xl opacity-20 group-hover:opacity-30 smooth-transition" 
        style={{ background: `radial-gradient(circle, hsl(var(--primary)) 0%, transparent 70%)` }}
      />
      
      <div className={cn("w-12 h-12 rounded-lg flex items-center justify-center mb-4 text-primary", bgClass)}>
        <Icon className="w-6 h-6" />
      </div>
      
      <h3 className="text-lg font-medium mb-2 group-hover:text-primary smooth-transition">{title}</h3>
      
      <p className="text-sm text-muted-foreground mb-4">{description}</p>
      
      <div className="flex items-center text-xs font-medium text-primary opacity-0 group-hover:opacity-100 transform translate-y-1 group-hover:translate-y-0 smooth-transition">
        <span>Open tool</span>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="ml-1 w-3 h-3 group-hover:translate-x-1 smooth-transition"
        >
          <path d="M5 12h14" />
          <path d="m12 5 7 7-7 7" />
        </svg>
      </div>
    </Link>
  );
};

export default Tool;
