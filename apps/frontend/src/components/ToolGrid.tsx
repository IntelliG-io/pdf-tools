
import React from "react";
import { cn } from "@/lib/utils";
import Tool from "./Tool";
import { 
  FileOutput, 
  Combine, 
  Scissors, 
  Lock, 
  Signature, 
  FileImage, 
  FileText, 
  Crop, 
  RotateCcw,
  Download,
  Stamp,
  FileCheck,
  PenLine,
  FileHeart,
  Layers,
  FileDigit
} from "lucide-react";

interface ToolGridProps {
  className?: string;
  featured?: boolean;
}

const ToolGrid: React.FC<ToolGridProps> = ({ className, featured = false }) => {
  const tools = [
    // Available tools - these will show first
    {
      title: "Merge PDF",
      description: "Combine multiple PDFs into one document",
      icon: Combine,
      bgClass: "bg-green-100",
      route: "/tools/merge-pdf",
      comingSoon: false,
      id: "merge-pdf"
    },
    {
      title: "Split PDF",
      description: "Extract pages from your PDF into a new file",
      icon: Scissors,
      bgClass: "bg-amber-100",
      route: "/tools/split-pdf",
      comingSoon: false,
      id: "split-pdf"
    },
    {
      title: "Compress PDF",
      description: "Reduce file size while maintaining quality",
      icon: FileHeart,
      bgClass: "bg-red-100",
      route: "/tools/compress-pdf",
      comingSoon: false,
      id: "compress-pdf"
    },
    {
      title: "Protect PDF",
      description: "Add password protection and permissions",
      icon: Lock,
      bgClass: "bg-slate-100",
      route: "/tools/protect-pdf",
      comingSoon: false,
      id: "protect-pdf"
    },
    
    // Coming soon - conversion tools
    {
      title: "PDF to DOCX",
      description: "Convert PDF documents to editable Word files",
      icon: FileOutput,
      bgClass: "bg-blue-100",
      route: "/tools/pdf-to-docx",
      comingSoon: false,
      id: "pdf-to-docx"
    },
    {
      title: "DOCX to PDF",
      description: "Convert Word documents to PDF format",
      icon: FileOutput,
      bgClass: "bg-blue-200",
      route: "/tools/docx-to-pdf",
      comingSoon: true,
      id: "docx-to-pdf"
    },
    {
      title: "PDF to PPTX",
      description: "Convert PDF to PowerPoint presentations",
      icon: FileOutput,
      bgClass: "bg-blue-300",
      route: "/tools/pdf-to-pptx",
      comingSoon: true,
      id: "pdf-to-pptx"
    },
    {
      title: "PPTX to PDF",
      description: "Convert PowerPoint presentations to PDF",
      icon: FileOutput,
      bgClass: "bg-blue-400",
      route: "/tools/pptx-to-pdf",
      comingSoon: true,
      id: "pptx-to-pdf"
    },
    {
      title: "PDF to XLSX",
      description: "Convert PDF tables to Excel spreadsheets",
      icon: FileOutput,
      bgClass: "bg-blue-500",
      route: "/tools/pdf-to-xlsx",
      comingSoon: true,
      id: "pdf-to-xlsx"
    },
    {
      title: "XLSX to PDF",
      description: "Convert Excel spreadsheets to PDF",
      icon: FileOutput,
      bgClass: "bg-blue-600",
      route: "/tools/xlsx-to-pdf",
      comingSoon: true,
      id: "xlsx-to-pdf"
    },
    
    // Other coming soon tools
    {
      title: "PDF to Image",
      description: "Convert each PDF page to an image",
      icon: FileImage,
      bgClass: "bg-fuchsia-100",
      route: "/tools/pdf-to-image",
      comingSoon: false,
      id: "pdf-to-image"
    },
    {
      title: "Image to PDF",
      description: "Create a PDF from multiple images",
      icon: Crop,
      bgClass: "bg-purple-100",
      route: "/tool/image-to-pdf",
      comingSoon: true,
      id: "image-to-pdf"
    },
    {
      title: "Sign PDF",
      description: "Electronically sign documents",
      icon: Signature,
      bgClass: "bg-pink-100",
      route: "/tool/sign-pdf",
      comingSoon: true,
      id: "sign-pdf"
    },
    {
      title: "OCR PDF",
      description: "Make scanned documents searchable",
      icon: FileText,
      bgClass: "bg-emerald-100",
      route: "/tool/ocr-pdf",
      comingSoon: true,
      id: "ocr-pdf"
    },
    {
      title: "Rotate PDF",
      description: "Change page orientation as needed",
      icon: RotateCcw,
      bgClass: "bg-purple-100", 
      route: "/tools/rotate-pdf",
      comingSoon: false,
      id: "rotate-pdf"
    },
    {
      title: "Number Pages",
      description: "Add page numbers to your documents",
      icon: FileDigit,
      bgClass: "bg-violet-100",
      route: "/tools/number-pages",
      comingSoon: false,
      id: "number-pages"
    },
    {
      title: "Watermark PDF",
      description: "Add text watermarks to your PDF documents",
      icon: Stamp,
      bgClass: "bg-sky-100",
      route: "/tools/watermark-pdf",
      comingSoon: false,
      id: "watermark-pdf"
    },
    {
      title: "Edit PDF",
      description: "Modify text and images in your PDF",
      icon: PenLine,
      bgClass: "bg-orange-100",
      route: "/tool/edit-pdf",
      comingSoon: true,
      id: "edit-pdf"
    }
  ];

  return (
    <div className={cn("container mx-auto px-4 sm:px-6 py-16", className)}>
      {!featured && (
        <div className="text-center mb-16">
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Everything you need to work with PDFs in one place. Simple, powerful, beautifully designed.
          </p>
        </div>
      )}
      
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {(featured ? tools.filter(tool => !tool.comingSoon).slice(0, 8) : tools).map((tool) => (
          <Tool
            key={tool.id}
            title={tool.title}
            description={tool.description}
            icon={tool.icon}
            bgClass={tool.bgClass}
            route={tool.route}
            comingSoon={tool.comingSoon}
            className="animate-fade-in animate-once"
            style={{ animationDelay: `${tools.indexOf(tool) * 50}ms` }}
          />
        ))}
      </div>
    </div>
  );
};

export default ToolGrid;
