
import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import Layout from "@/components/Layout";
import FileUpload from "@/components/FileUpload";
import { ArrowLeft, ArrowRight, HelpCircle, Check, Info, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import usePdfOperations from "@/hooks/use-pdf-operations";
import { useToast } from "@/hooks/use-toast";

interface ToolData {
  [key: string]: {
    title: string;
    description: string;
    icon: React.ReactNode;
    color: string;
    bgColor: string;
    steps: string[];
    accepts: string;
  };
}

const toolData: ToolData = {
  "convert-pdf": {
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
    accepts: ".pdf"
  },
  "merge-pdf": {
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
    accepts: ".pdf"
  },
  "split-pdf": {
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
    accepts: ".pdf"
  }
};

const Tool = () => {
  const { toolId } = useParams<{ toolId: string }>();
  const [selectedFormat, setSelectedFormat] = useState<string | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [fileOrder, setFileOrder] = useState<number[]>([]);
  const [step, setStep] = useState(1);
  const [mergedPdfUrl, setMergedPdfUrl] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [processingComplete, setProcessingComplete] = useState(false);
  
  const { toast } = useToast();
  
  // Clean up URL objects when component unmounts
  useEffect(() => {
    return () => {
      if (mergedPdfUrl) {
        URL.revokeObjectURL(mergedPdfUrl);
      }
    };
  }, [mergedPdfUrl]);
  const { mergePdfs, splitPdf, isLoading, error, getFriendlyErrorMessage } = usePdfOperations({
    onSuccess: (data: Blob, filename: string) => {
      // Create URL for the blob data
      const url = window.URL.createObjectURL(new Blob([data]));
      setMergedPdfUrl(url);
      setProcessing(false);
      setProcessingComplete(true);
      setStep(3);
      
      toast({
        title: "Success!",
        description: `Your ${toolId === "merge-pdf" ? "merged" : "split"} PDF is ready for download.`,
        duration: 5000,
      });
    },
    onError: (error: Error) => {
      setProcessing(false);
      toast({
        title: "Error",
        description: error.message || "An error occurred while processing your PDF files.",
        variant: "destructive",
        duration: 5000,
      });
    }
  });
  
  // Default to convert-pdf if toolId is not in our data
  const currentTool = toolData[toolId || ""] || toolData["convert-pdf"];
  
  const handleFilesSelected = (selectedFiles: File[]) => {
    setFiles(selectedFiles);
    
    // Initialize file order with sequential indices
    setFileOrder(selectedFiles.map((_, index) => index));
    
    if (selectedFiles.length > 0 && step === 1) {
      setStep(2);
    }
  };
  
  const handleFormatSelect = (format: string) => {
    setSelectedFormat(format);
    setStep(3);
  };
  
  // Handle moving files up/down in the order
  const moveFile = (index: number, direction: 'up' | 'down') => {
    if (
      (direction === 'up' && index === 0) || 
      (direction === 'down' && index === files.length - 1)
    ) {
      return; // Already at the extremes
    }
    
    const newOrder = [...fileOrder];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    
    // Swap the indices
    [newOrder[index], newOrder[targetIndex]] = [newOrder[targetIndex], newOrder[index]];
    
    setFileOrder(newOrder);
  };
  
  const handleProcessFiles = async () => {
    setProcessing(true);
    
    // Reset any previous errors
    setMergedPdfUrl(null);
    
    try {
      if (toolId === "merge-pdf") {
        if (files.length < 2) {
          toast({
            title: "Error",
            description: "You need at least 2 PDF files to merge.",
            variant: "destructive",
            duration: 5000,
          });
          setProcessing(false);
          return;
        }
        
        // Reorder files according to the user's arrangement
        const orderedFiles = fileOrder.map(index => files[index]);
        
        // Set up options for the merge operation
        const options = {
          documentInfo: {
            title: "Merged Document",
            author: "PaperFlow",
            subject: "Combined PDF Document",
            keywords: "merged, pdf, document"
          },
          // No need to pass fileOrder since we're already sending the files in the desired order
          addBookmarks: true
        };
        
        await mergePdfs(orderedFiles, options);
      } else if (toolId === "split-pdf") {
        if (files.length !== 1) {
          toast({
            title: "Error",
            description: "Please select exactly one PDF file to split.",
            variant: "destructive",
            duration: 5000,
          });
          setProcessing(false);
          return;
        }
        
        await splitPdf(files[0]);
      }
    } catch (err) {
      // Show error toast
      toast({
        title: "Error",
        description: error ? getFriendlyErrorMessage(error) : "An error occurred while processing your PDF files.",
        variant: "destructive",
        duration: 5000,
      });
      console.error("Error processing PDFs:", err);
    }
  };
  
  const outputFormats = [
    { id: "word", name: "Word", extension: ".docx", icon: "W", color: "bg-blue-600" },
    { id: "excel", name: "Excel", extension: ".xlsx", icon: "X", color: "bg-green-600" },
    { id: "powerpoint", name: "PowerPoint", extension: ".pptx", icon: "P", color: "bg-red-600" },
    { id: "jpg", name: "JPG", extension: ".jpg", icon: "J", color: "bg-purple-600" },
    { id: "png", name: "PNG", extension: ".png", icon: "P", color: "bg-yellow-600" },
    { id: "text", name: "Text", extension: ".txt", icon: "T", color: "bg-gray-600" }
  ];
  
  const renderStep = () => {
    switch (step) {
      case 1:
        return (
          <div className="max-w-xl mx-auto w-full animate-fade-in animate-once">
            <FileUpload 
              onFilesSelected={handleFilesSelected}
              accept={currentTool.accepts}
              multiple={toolId === "merge-pdf"}
            />
          </div>
        );
      case 2:
        if (toolId === "convert-pdf") {
          return (
            <div className="max-w-xl mx-auto w-full animate-fade-in animate-once">
              <h3 className="text-lg font-medium mb-4">Select Output Format</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {outputFormats.map((format) => (
                  <button
                    key={format.id}
                    className={cn(
                      "p-4 rounded-lg border flex flex-col items-center text-center smooth-transition",
                      selectedFormat === format.id
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/50 hover:bg-secondary/50"
                    )}
                    onClick={() => handleFormatSelect(format.id)}
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
        } else if (toolId === "merge-pdf") {
          return (
            <div className="max-w-xl mx-auto w-full animate-fade-in animate-once">
              <h3 className="text-lg font-medium mb-4">Arrange PDF Order</h3>
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
                        onClick={() => moveFile(orderIndex, 'up')}
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
                        onClick={() => moveFile(orderIndex, 'down')}
                        disabled={orderIndex === files.length - 1}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="m5 15 4 4 4-4" />
                          <path d="M9 5v14" />
                        </svg>
                      </button>
                    </div>
                  </div>
                )
                })}
              </div>
              <div className="mt-6">
                <button 
                  className="bg-primary hover:bg-primary/90 text-white px-6 py-3 rounded-lg font-medium shadow-lg shadow-primary/20 flex items-center justify-center smooth-transition"
                  onClick={handleProcessFiles}
                  disabled={processing || files.length < 2}
                >
                  {processing ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      Merge Files
                      <ArrowRight className="ml-2 w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        } else if (toolId === "split-pdf") {
          return (
            <div className="max-w-xl mx-auto w-full animate-fade-in animate-once">
              <h3 className="text-lg font-medium mb-4">Select Pages to Extract</h3>
              <div className="border rounded-lg p-6 bg-secondary/30">
                <div className="mb-4">
                  <label className="block text-sm font-medium mb-2">Page Range</label>
                  <div className="flex items-center gap-3">
                    <input 
                      type="text" 
                      placeholder="e.g. 1-3, 5, 8-10" 
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    />
                    <div className="relative group">
                      <HelpCircle className="w-5 h-5 text-muted-foreground" />
                      <div className="absolute right-0 w-64 p-3 bg-foreground text-background text-xs rounded-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible smooth-transition z-10">
                        Enter page numbers and/or page ranges separated by commas. For example: 1,3,5-12
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="mb-4">
                  <label className="block text-sm font-medium mb-2">Split Options</label>
                  <div className="space-y-2">
                    <div className="flex items-center">
                      <input id="all-pages" type="radio" name="split-option" className="h-4 w-4 border-gray-300 text-primary focus:ring-primary/20" />
                      <label htmlFor="all-pages" className="ml-2 text-sm">Extract all pages as separate PDFs</label>
                    </div>
                    <div className="flex items-center">
                      <input id="range-pages" type="radio" name="split-option" className="h-4 w-4 border-gray-300 text-primary focus:ring-primary/20" defaultChecked />
                      <label htmlFor="range-pages" className="ml-2 text-sm">Extract specified range as one PDF</label>
                    </div>
                  </div>
                </div>
              </div>
              <div className="mt-6">
                <button 
                  className="bg-primary hover:bg-primary/90 text-white px-6 py-3 rounded-lg font-medium shadow-lg shadow-primary/20 flex items-center justify-center smooth-transition"
                  onClick={handleProcessFiles}
                  disabled={processing || files.length !== 1}
                >
                  {processing ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      Split PDF
                      <ArrowRight className="ml-2 w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        }
        return null;
      case 3:
        return (
          <div className="max-w-xl mx-auto w-full animate-fade-in animate-once text-center">
            <div className="mb-6">
              <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Check className="w-10 h-10 text-green-600" />
              </div>
              <h3 className="text-2xl font-bold mb-2">Processing Complete!</h3>
              <p className="text-muted-foreground mb-6">
                Your file has been successfully processed and is ready for download.
              </p>
            </div>
            
            <div className="p-6 border rounded-lg bg-secondary/30 mb-8">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center">
                  <div className="p-2 bg-primary/10 rounded">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
                        <path d="M13 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8" />
                        <path d="M13 3v5h5" />
                      </svg>
                  </div>
                  <div className="ml-3">
                    <div className="text-sm font-medium">
                      {toolId === "convert-pdf" 
                        ? `${files[0]?.name.split('.')[0]}.${selectedFormat}` 
                        : toolId === "merge-pdf"
                          ? "merged_document.pdf"
                          : "split_document.pdf"}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {toolId === "convert-pdf" 
                        ? `${selectedFormat?.toUpperCase()} Document` 
                        : "PDF Document"}
                    </div>
                  </div>
                </div>
                <a 
                  href={mergedPdfUrl || "#"} 
                  download={toolId === "merge-pdf" ? "merged.pdf" : "split.pdf"}
                  className={cn(
                    "bg-primary hover:bg-primary/90 text-white px-3 py-1 rounded text-sm font-medium shadow-sm flex items-center smooth-transition",
                    !mergedPdfUrl && "opacity-50 pointer-events-none"
                  )}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" x2="12" y1="15" y2="3" />
                  </svg>
                  Download
                </a>
              </div>
              
              <div className="flex items-start pt-4 border-t border-border">
                <Info className="w-5 h-5 text-muted-foreground mr-3 mt-0.5" />
                <div className="text-xs text-muted-foreground text-left">
                  Your file has been processed securely on our servers and will be automatically deleted after 24 hours for your privacy.
                </div>
              </div>
            </div>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button 
                className="bg-secondary hover:bg-secondary/80 text-foreground px-6 py-3 rounded-lg font-medium shadow-sm flex items-center justify-center smooth-transition"
                onClick={() => {
                  // Clean up the URL object to avoid memory leaks
                  if (mergedPdfUrl) {
                    URL.revokeObjectURL(mergedPdfUrl);
                  }
                  
                  setFiles([]);
                  setFileOrder([]);
                  setSelectedFormat(null);
                  setStep(1);
                  setMergedPdfUrl(null);
                  setProcessingComplete(false);
                  setProcessing(false);
                }}
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-2">
                  <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                  <path d="M3 3v5h5" />
                  <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
                  <path d="M16 21h5v-5" />
                </svg>
                Process Another File
              </button>
              <Link
                to="/"
                className="bg-white hover:bg-white/90 text-foreground border border-border px-6 py-3 rounded-lg font-medium shadow-sm flex items-center justify-center smooth-transition"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-2">
                  <path d="M3 9h18v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9Z" />
                  <path d="M3 9V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v4" />
                  <path d="M13 13h4" />
                  <path d="M13 17h4" />
                  <path d="M9 13h.01" />
                  <path d="M9 17h.01" />
                </svg>
                Back to All Tools
              </Link>
            </div>
          </div>
        );
      default:
        return null;
    }
  };
  
  return (
    <Layout>
      <div className="py-16 container mx-auto px-4 sm:px-6">
        <div className="mb-10">
          <Link to="/" className="flex items-center text-muted-foreground hover:text-foreground smooth-transition text-sm mb-8">
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back to Home
          </Link>
          
          <div className="text-center max-w-2xl mx-auto mb-16">
            <div className={cn("w-16 h-16 rounded-lg mx-auto flex items-center justify-center mb-4", currentTool.bgColor)}>
              <div className={currentTool.color}>{currentTool.icon}</div>
            </div>
            <h1 className="text-3xl font-bold mb-3">{currentTool.title}</h1>
            <p className="text-muted-foreground text-lg">{currentTool.description}</p>
          </div>
          
          <div className="max-w-2xl mx-auto mb-16">
            <div className="flex items-center justify-center">
              {currentTool.steps.map((stepText, index) => (
                <React.Fragment key={index}>
                  <div className="flex flex-col items-center">
                    <div 
                      className={cn(
                        "w-8 h-8 rounded-full flex items-center justify-center text-sm mb-2 smooth-transition",
                        step > index + 1 
                          ? "bg-primary text-white" 
                          : step === index + 1 
                            ? "bg-primary/10 text-primary border border-primary" 
                            : "bg-secondary text-muted-foreground"
                      )}
                    >
                      {step > index + 1 ? (
                        <Check className="w-4 h-4" />
                      ) : (
                        index + 1
                      )}
                    </div>
                    <span 
                      className={cn(
                        "text-xs text-center max-w-[100px] hidden sm:block smooth-transition",
                        step === index + 1 ? "text-primary font-medium" : "text-muted-foreground"
                      )}
                    >
                      {stepText}
                    </span>
                  </div>
                  
                  {index < currentTool.steps.length - 1 && (
                    <div 
                      className={cn(
                        "w-16 h-px mx-2 smooth-transition",
                        step > index + 1 ? "bg-primary" : "bg-border"
                      )}
                    />
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>
        
        <div className="max-w-4xl mx-auto">
          {renderStep()}
        </div>
      </div>
    </Layout>
  );
};

export default Tool;
