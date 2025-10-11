import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { cn } from "@/lib/utils";

interface ToolHeaderProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  bgColor: string;
}

const ToolHeader: React.FC<ToolHeaderProps> = ({
  title,
  description,
  icon,
  color,
  bgColor,
}) => {
  return (
    <div className="mb-10">
      <Link to="/" className="flex items-center text-muted-foreground hover:text-foreground smooth-transition text-sm mb-8">
        <ArrowLeft className="w-4 h-4 mr-1" />
        Back to Home
      </Link>
      
      <div className="text-center max-w-2xl mx-auto mb-16">
        <div className={cn("w-16 h-16 rounded-lg mx-auto flex items-center justify-center mb-4", bgColor)}>
          <div className={color}>{icon}</div>
        </div>
        <h1 className="text-3xl font-bold mb-3">{title}</h1>
        <p className="text-muted-foreground text-lg">{description}</p>
      </div>
    </div>
  );
};

export default ToolHeader;
