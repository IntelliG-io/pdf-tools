import React from "react";

export interface ToolData {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  bgColor: string;
  steps: string[];
  accepts: string;
  path: string;
}

export const outputFormats = [
  { id: "word", name: "Word", extension: ".docx", icon: "W", color: "bg-blue-600" },
  { id: "excel", name: "Excel", extension: ".xlsx", icon: "X", color: "bg-green-600" },
  { id: "powerpoint", name: "PowerPoint", extension: ".pptx", icon: "P", color: "bg-red-600" },
  { id: "jpg", name: "JPG", extension: ".jpg", icon: "J", color: "bg-purple-600" },
  { id: "png", name: "PNG", extension: ".png", icon: "P", color: "bg-yellow-600" },
  { id: "text", name: "Text", extension: ".txt", icon: "T", color: "bg-gray-600" }
];

export const imageFormats = [
  { id: "jpg", name: "JPG", extension: ".jpg", quality: true },
  { id: "png", name: "PNG", extension: ".png", transparency: true },
  { id: "tiff", name: "TIFF", extension: ".tiff" },
  { id: "bmp", name: "BMP", extension: ".bmp" }
];

export const imageQualityOptions = [
  { id: "low", name: "Low", description: "Smaller file size, lower quality", dpi: "96 DPI" },
  { id: "medium", name: "Medium", description: "Balanced size and quality", dpi: "150 DPI" },
  { id: "high", name: "High", description: "Better quality, larger files", dpi: "300 DPI" },
  { id: "best", name: "Best", description: "Highest quality, largest files", dpi: "600 DPI" }
];

export const pdfTools: ToolData[] = [
  {
    id: "pdf-to-image",
    title: "PDF to Image",
    description: "Convert PDF pages to JPG, PNG, or other image formats",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <circle cx="9" cy="9" r="2" />
        <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
      </svg>
    ),
    color: "text-fuchsia-600",
    bgColor: "bg-fuchsia-100",
    steps: [
      "Upload your PDF file",
      "Configure image conversion options",
      "Convert and download your images"
    ],
    accepts: ".pdf",
    path: "/tools/pdf-to-image"
  },
  {
    id: "watermark-pdf",
    title: "Watermark PDF",
    description: "Add text watermarks to your PDF documents",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
        <path d="M7 7h.01" />
        <path d="m14 7-4 4" />
        <path d="m7 14 1.75-1.75" />
        <path d="m16 16 .5-.5" />
        <path d="m9 15 .5.5" />
        <path d="M17 7h.01" />
        <path d="M12 16h.01" />
      </svg>
    ),
    color: "text-sky-600",
    bgColor: "bg-sky-100",
    steps: [
      "Upload your PDF file",
      "Configure watermark options",
      "Download your watermarked PDF"
    ],
    accepts: ".pdf",
    path: "/tools/watermark-pdf"
  },
  {
    id: "number-pages",
    title: "Number Pages",
    description: "Add customizable page numbers to your PDF documents",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
        <line x1="9" x2="15" y1="9" y2="9" />
        <line x1="9" x2="15" y1="12" y2="12" />
        <line x1="9" x2="15" y1="15" y2="15" />
      </svg>
    ),
    color: "text-indigo-600",
    bgColor: "bg-indigo-100",
    steps: [
      "Upload your PDF file",
      "Configure page numbering options",
      "Download your numbered PDF"
    ],
    accepts: ".pdf",
    path: "/tools/number-pages"
  },
  {
    id: "rotate-pdf",
    title: "Rotate PDF",
    description: "Rotate pages in your PDF documents to the desired orientation",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.85.84 6.71 2.26" />
        <path d="M21 3v4h-4" />
        <path d="M16 3h5v5" />
      </svg>
    ),
    color: "text-purple-600",
    bgColor: "bg-purple-100",
    steps: [
      "Upload your PDF file",
      "Select pages and rotation angles",
      "Download your rotated PDF"
    ],
    accepts: ".pdf",
    path: "/tools/rotate-pdf"
  },
  {
    id: "pdf-to-docx",
    title: "PDF to Word",
    description: "Convert your PDF files to editable Word documents",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
        <path d="M14 2v6h6"></path>
        <path d="M16 13H8"></path>
        <path d="M16 17H8"></path>
        <path d="M10 9H8"></path>
      </svg>
    ),
    color: "text-blue-700",
    bgColor: "bg-blue-100",
    steps: [
      "Upload your PDF file",
      "Choose conversion options",
      "Convert and download your Word document"
    ],
    accepts: ".pdf",
    path: "/tools/pdf-to-docx"
  },
  {
    id: "convert-pdf",
    title: "Convert PDF",
    description: "Transform your PDF files to Word, Excel, PowerPoint and more",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M13 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8" />
        <path d="M13 3v5h5" />
        <path d="m17 17-4-4" />
        <path d="M4 21v-9" />
        <path d="M20 12H8" />
      </svg>
    ),
    color: "text-blue-600",
    bgColor: "bg-blue-100",
    steps: [
      "Upload your PDF file",
      "Select the output format you need",
      "Convert and download your new file"
    ],
    accepts: ".pdf",
    path: "/tools/convert-pdf"
  },
  {
    id: "compress-pdf",
    title: "Compress PDF",
    description: "Reduce file size while maintaining quality",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 22V2h16v20H4z"/>
        <path d="M10 14V6m0 0L7 9m3-3 3 3"/>
        <path d="M10 14v2h4v-2h-4z"/>
      </svg>
    ),
    color: "text-red-600",
    bgColor: "bg-red-100",
    steps: [
      "Upload your PDF file",
      "Select compression level",
      "Download compressed PDF"
    ],
    accepts: ".pdf",
    path: "/tools/compress-pdf"
  },
  {
    id: "merge-pdf",
    title: "Merge PDF",
    description: "Combine multiple PDFs into a single document",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect width="8" height="8" x="8" y="8" rx="1" />
        <path d="M4 10V6a2 2 0 0 1 2-2h4" />
        <path d="M14 4h4a2 2 0 0 1 2 2v4" />
        <path d="M20 14v4a2 2 0 0 1-2 2h-4" />
        <path d="M10 20H6a2 2 0 0 1-2-2v-4" />
      </svg>
    ),
    color: "text-green-600",
    bgColor: "bg-green-100",
    steps: [
      "Upload multiple PDF files",
      "Arrange them in the order you want",
      "Merge and download the combined PDF"
    ],
    accepts: ".pdf",
    path: "/tools/merge-pdf"
  },
  {
    id: "split-pdf",
    title: "Split PDF",
    description: "Extract pages from your PDF into a new file",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 3v4a1 1 0 0 0 1 1h4" />
        <path d="M17 21h-7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l7 7v9a2 2 0 0 1-2 2Z" />
        <path d="m10 12-6 6" />
        <path d="m4 12 6 6" />
      </svg>
    ),
    color: "text-amber-600",
    bgColor: "bg-amber-100",
    steps: [
      "Upload your PDF file",
      "Select the pages or range to extract",
      "Split and download the new PDF"
    ],
    accepts: ".pdf",
    path: "/tools/split-pdf"
  }
];

export function getToolById(toolId: string): ToolData | undefined {
  return pdfTools.find(tool => tool.id === toolId) || pdfTools[0];
}
