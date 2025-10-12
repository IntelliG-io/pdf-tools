import React, { useState, useEffect } from "react";
import Layout from "@/components/Layout";
import FileUpload from "@/components/FileUpload";
import { useToast } from "@/hooks/use-toast";
import usePdfOperations from "@/hooks/use-pdf-operations";
import { getToolById } from "@/constants/toolData";
import ToolHeader from "@/components/pdf-tools/ToolHeader";
import StepProgress from "@/components/pdf-tools/StepProgress";
import ProcessingButton from "@/components/pdf-tools/ProcessingButton";
import OperationComplete from "@/components/pdf-tools/OperationComplete";
import { HelpCircle, Scissors, FileOutput, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";

// Define split modes
type SplitMode = 'ranges' | 'pages' | 'everyNPages' | 'all';

interface PageRange {
  start: number;
  end: number;
}

const SplitPDF: React.FC = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [step, setStep] = useState(1);
  const [splitPdfUrl, setSplitPdfUrl] = useState<string | null>(null);
  const [splitPdfZipUrl, setSplitPdfZipUrl] = useState<string | null>(null);
  const [downloadFilename, setDownloadFilename] = useState<string>("");
  const [processing, setProcessing] = useState(false);
  const [processingComplete, setProcessingComplete] = useState(false);
  const [pageRange, setPageRange] = useState<string>("");
  const [splitMode, setSplitMode] = useState<SplitMode>("ranges");
  const [specificPages, setSpecificPages] = useState<string>("");
  const [everyNPages, setEveryNPages] = useState<number>(2);
  const [advancedOptions, setAdvancedOptions] = useState<boolean>(false);
  const [filenamePrefix, setFilenamePrefix] = useState<string>("split");
  
  // Get the tool data
  const tool = getToolById("split-pdf");
  const { toast } = useToast();
  
  // Initialize PDF operations
  const { splitPdf, isLoading, error, getFriendlyErrorMessage } = usePdfOperations({
    onSuccess: (data: Blob, filename: string) => {
      // Check if it's a ZIP file or PDF
      const isZip = filename.endsWith('.zip') || 
                   (data.type && data.type.toLowerCase() === 'application/zip');
      
      // Create URL for the blob data
      const url = window.URL.createObjectURL(new Blob([data], { 
        type: isZip ? 'application/zip' : 'application/pdf' 
      }));
      
      if (isZip) {
        setSplitPdfZipUrl(url);
      } else {
        setSplitPdfUrl(url);
      }
      // Store the server-provided filename so the download button uses the correct extension
      setDownloadFilename(filename);
      
      setProcessing(false);
      setProcessingComplete(true);
      setStep(3);
      
      toast({
        title: "Success!",
        description: isZip 
          ? "Your split PDFs are ready for download as a ZIP file."
          : "Your split PDF is ready for download.",
        duration: 5000,
      });
    },
    onError: (error: Error) => {
      setProcessing(false);
      toast({
        title: "Error",
        description: error.message || "An error occurred while splitting your PDF file.",
        variant: "destructive",
        duration: 5000,
      });
    }
  });
  
  // Clean up URL objects when component unmounts
  useEffect(() => {
    return () => {
      if (splitPdfUrl) {
        URL.revokeObjectURL(splitPdfUrl);
      }
      if (splitPdfZipUrl) {
        URL.revokeObjectURL(splitPdfZipUrl);
      }
    };
  }, [splitPdfUrl, splitPdfZipUrl]);
  
  // Handle file uploads
  const handleFilesSelected = (selectedFiles: File[]) => {
    // Only take the first file for splitting
    if (selectedFiles.length > 0) {
      const file = selectedFiles[0];
      
      // Validate file is a PDF
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        toast({
          title: "Invalid File Type",
          description: "Please select a PDF file for splitting.",
          variant: "destructive",
          duration: 5000,
        });
        return;
      }
      
      setFiles([file]);
      
      if (step === 1) {
        setStep(2);
      }
    }
  };
  
  // Parse a page range string into an array of PageRange objects
  const parsePageRanges = (rangeStr: string): PageRange[] => {
    const ranges: PageRange[] = [];
    
    if (!rangeStr.trim()) {
      return ranges;
    }
    
    // Parse page ranges
    const rangeParts = rangeStr.split(',').map(part => part.trim());
    
    for (const part of rangeParts) {
      if (part.includes('-')) {
        const [start, end] = part.split('-').map(num => parseInt(num.trim(), 10));
        if (!isNaN(start) && !isNaN(end) && start > 0 && end >= start) {
          ranges.push({ start, end });
        }
      } else {
        const pageNum = parseInt(part, 10);
        if (!isNaN(pageNum) && pageNum > 0) {
          ranges.push({ start: pageNum, end: pageNum });
        }
      }
    }
    
    return ranges;
  };
  
  // Parse a string with specific page numbers into an array of numbers
  const parseSpecificPages = (pagesStr: string): number[] => {
    if (!pagesStr.trim()) {
      return [];
    }
    
    return pagesStr
      .split(',')
      .map(p => parseInt(p.trim(), 10))
      .filter(p => !isNaN(p) && p > 0);
  };
  
  // Handle the split process
  const handleSplitFile = async () => {
    setProcessing(true);
    
    // Reset any previous URLs
    setSplitPdfUrl(null);
    setSplitPdfZipUrl(null);
    
    try {
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
      
      // Set up options for the split operation
      const options: Record<string, any> = {
        mode: splitMode
      };
      
      // Always pass a non-empty filenamePrefix if provided
      const trimmedPrefix = (filenamePrefix || '').trim();
      if (trimmedPrefix) {
        options.filenamePrefix = trimmedPrefix;
      }

      // Add additional advanced flags when enabled
      if (advancedOptions) {
        options.preserveBookmarks = true;
      }
      
      // Handle different split modes
      switch (splitMode) {
        case "ranges":
          const ranges = parsePageRanges(pageRange);
          if (ranges.length > 0) {
            options.ranges = ranges;
          } else {
            toast({
              title: "Error",
              description: "Please enter valid page ranges (e.g., 1-3, 5, 8-10).",
              variant: "destructive",
              duration: 5000,
            });
            setProcessing(false);
            return;
          }
          break;
          
        case "pages":
          const pages = parseSpecificPages(specificPages);
          if (pages.length > 0) {
            options.pages = pages;
          } else {
            toast({
              title: "Error",
              description: "Please enter valid page numbers to split at (e.g., 3, 5, 8).",
              variant: "destructive",
              duration: 5000,
            });
            setProcessing(false);
            return;
          }
          break;
          
        case "everyNPages":
          if (everyNPages < 1) {
            toast({
              title: "Error",
              description: "Please enter a valid number of pages (greater than 0).",
              variant: "destructive",
              duration: 5000,
            });
            setProcessing(false);
            return;
          }
          options.everyNPages = everyNPages;
          break;
          
        case "all":
          // No additional options needed
          break;
      }
      
      // Add a flag to get a ZIP file for multiple output files
      if (splitMode === "all" || (splitMode === "ranges" && parsePageRanges(pageRange).length > 1)) {
        options.outputFormat = "zip";
      }
      
      await splitPdf(files[0], options);
    } catch (err) {
      // Show error toast
      toast({
        title: "Error",
        description: error ? getFriendlyErrorMessage(error) : "An error occurred while splitting your PDF file.",
        variant: "destructive",
        duration: 5000,
      });
      console.error("Error splitting PDF:", err);
      setProcessing(false);
    }
  };
  
  // Reset the form to start over
  const handleReset = () => {
    // Clean up the URL objects to avoid memory leaks
    if (splitPdfUrl) {
      URL.revokeObjectURL(splitPdfUrl);
    }
    
    if (splitPdfZipUrl) {
      URL.revokeObjectURL(splitPdfZipUrl);
    }
    
    setFiles([]);
    setPageRange("");
    setSpecificPages("");
    setEveryNPages(2);
    setSplitMode("ranges");
    setStep(1);
    setSplitPdfUrl(null);
    setSplitPdfZipUrl(null);
    setProcessingComplete(false);
    setProcessing(false);
    setAdvancedOptions(false);
    setFilenamePrefix("split");
  };
  
  // Render different content based on the current step
  const renderStep = () => {
    switch (step) {
      case 1:
        return (
          <div className="max-w-xl mx-auto w-full animate-fade-in animate-once">
            <FileUpload 
              onFilesSelected={handleFilesSelected}
              accept={tool?.accepts || ".pdf"}
              multiple={false}
            />
          </div>
        );
      case 2:
        return (
          <div className="max-w-xl mx-auto w-full animate-fade-in animate-once">
            <h3 className="text-lg font-medium mb-4">Select Pages to Extract</h3>
            <div className="border rounded-lg p-6 bg-secondary/30">
              
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Split Method</label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div 
                    className={cn(
                      "flex flex-col items-center justify-center p-4 rounded-lg border-2 cursor-pointer transition-all",
                      splitMode === "ranges" 
                        ? "border-primary/80 bg-primary/5" 
                        : "border-border hover:border-primary/50"
                    )}
                    onClick={() => setSplitMode("ranges")}
                  >
                    <Scissors className="w-6 h-6 mb-2 text-primary" />
                    <span className="font-medium">Extract Page Ranges</span>
                    <span className="text-xs text-muted-foreground text-center mt-1">
                      Extract specific page ranges to a new PDF
                    </span>
                  </div>
                  
                  <div 
                    className={cn(
                      "flex flex-col items-center justify-center p-4 rounded-lg border-2 cursor-pointer transition-all",
                      splitMode === "pages" 
                        ? "border-primary/80 bg-primary/5" 
                        : "border-border hover:border-primary/50"
                    )}
                    onClick={() => setSplitMode("pages")}
                  >
                    <FileOutput className="w-6 h-6 mb-2 text-primary" />
                    <span className="font-medium">Split at Specific Pages</span>
                    <span className="text-xs text-muted-foreground text-center mt-1">
                      Split the PDF into multiple parts
                    </span>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
                  <div 
                    className={cn(
                      "flex flex-col items-center justify-center p-4 rounded-lg border-2 cursor-pointer transition-all",
                      splitMode === "everyNPages" 
                        ? "border-primary/80 bg-primary/5" 
                        : "border-border hover:border-primary/50"
                    )}
                    onClick={() => setSplitMode("everyNPages")}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6 mb-2 text-primary">
                      <path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M3 9v10a2 2 0 0 0 2 2h4M21 9v10a2 2 0 0 1-2 2h-4" />
                    </svg>
                    <span className="font-medium">Split Every N Pages</span>
                    <span className="text-xs text-muted-foreground text-center mt-1">
                      Split after every N pages
                    </span>
                  </div>
                  
                  <div 
                    className={cn(
                      "flex flex-col items-center justify-center p-4 rounded-lg border-2 cursor-pointer transition-all",
                      splitMode === "all" 
                        ? "border-primary/80 bg-primary/5" 
                        : "border-border hover:border-primary/50"
                    )}
                    onClick={() => setSplitMode("all")}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6 mb-2 text-primary">
                      <rect x="2" y="6" width="4" height="12" rx="1" />
                      <rect x="10" y="6" width="4" height="12" rx="1" />
                      <rect x="18" y="6" width="4" height="12" rx="1" />
                    </svg>
                    <span className="font-medium">Extract All Pages</span>
                    <span className="text-xs text-muted-foreground text-center mt-1">
                      Split into individual pages
                    </span>
                  </div>
                </div>
              </div>
              
              {/* Configuration options based on selected split mode */}
              <div className="mt-6 pt-4 border-t border-border">
                {splitMode === "ranges" && (
                  <div className="mb-4">
                    <label className="block text-sm font-medium mb-2">Page Ranges</label>
                    <div className="flex items-center gap-3">
                      <input 
                        type="text" 
                        placeholder="e.g. 1-3, 5, 8-10" 
                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                        value={pageRange}
                        onChange={(e) => setPageRange(e.target.value)}
                      />
                      <div className="relative group">
                        <HelpCircle className="w-5 h-5 text-muted-foreground" />
                        <div className="absolute right-0 w-64 p-3 bg-foreground text-background text-xs rounded-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity z-10">
                          Enter page numbers and/or page ranges separated by commas. For example: 1,3,5-12
                        </div>
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Each range will be extracted as a separate PDF file.
                    </p>
                  </div>
                )}
                
                {splitMode === "pages" && (
                  <div className="mb-4">
                    <label className="block text-sm font-medium mb-2">Split at Pages</label>
                    <div className="flex items-center gap-3">
                      <input 
                        type="text" 
                        placeholder="e.g. 3, 5, 8" 
                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                        value={specificPages}
                        onChange={(e) => setSpecificPages(e.target.value)}
                      />
                      <div className="relative group">
                        <HelpCircle className="w-5 h-5 text-muted-foreground" />
                        <div className="absolute right-0 w-64 p-3 bg-foreground text-background text-xs rounded-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity z-10">
                          Enter page numbers where the PDF should be split. For example: 3,5,8 would create 4 PDFs (pages 1-2, 3-4, 5-7, and 8-end).
                        </div>
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      The PDF will be split at these page numbers, creating multiple PDFs.
                    </p>
                  </div>
                )}
                
                {splitMode === "everyNPages" && (
                  <div className="mb-4">
                    <label className="block text-sm font-medium mb-2">Pages per Document</label>
                    <div className="flex items-center gap-3">
                      <input 
                        type="number" 
                        min="1"
                        className="flex h-10 w-32 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                        value={everyNPages}
                        onChange={(e) => setEveryNPages(parseInt(e.target.value, 10))}
                      />
                      <div className="relative group">
                        <HelpCircle className="w-5 h-5 text-muted-foreground" />
                        <div className="absolute right-0 w-64 p-3 bg-foreground text-background text-xs rounded-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity z-10">
                          Enter the number of pages each new PDF should contain. For example: If set to 2, a 6-page PDF would be split into 3 PDFs with 2 pages each.
                        </div>
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Each new PDF will contain this many pages.
                    </p>
                  </div>
                )}
                
                {splitMode === "all" && (
                  <div className="mb-4">
                    <p className="text-sm text-muted-foreground">
                      Each page of the PDF will be extracted as a separate PDF file. The files will be delivered as a ZIP archive.
                    </p>
                  </div>
                )}
              </div>
              
              {/* Advanced options section */}
              <div className="mt-4 pt-4 border-t border-border">
                <button
                  type="button"
                  className="flex items-center text-sm font-medium text-primary hover:text-primary/80 focus:outline-none"
                  onClick={() => setAdvancedOptions(!advancedOptions)}
                >
                  {advancedOptions ? (
                    <ChevronUp className="h-4 w-4 mr-1" />
                  ) : (
                    <ChevronDown className="h-4 w-4 mr-1" />
                  )}
                  Advanced Options
                </button>
                
                {advancedOptions && (
                  <div className="mt-4 space-y-4 animate-fade-in animate-once">
                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Filename Prefix
                      </label>
                      <input
                        type="text"
                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                        placeholder="e.g. chapter, section, part"
                        value={filenamePrefix}
                        onChange={(e) => setFilenamePrefix(e.target.value)}
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        This prefix will be added to all created PDF files.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            <ProcessingButton 
              onClick={handleSplitFile}
              isProcessing={processing}
              disabled={
                (splitMode === "ranges" && !pageRange.trim()) ||
                (splitMode === "pages" && !specificPages.trim()) ||
                (splitMode === "everyNPages" && everyNPages < 1)
              }
              text="Split PDF"
            />
          </div>
        );
      case 3:
        return (
          <OperationComplete 
            fileName={downloadFilename || (splitPdfZipUrl ? "split-files.zip" : "split.pdf")}
            fileType={splitPdfZipUrl ? "ZIP Archive" : "PDF Document"}
            fileUrl={splitPdfZipUrl || splitPdfUrl}
            onReset={handleReset}
          />
        );
      default:
        return null;
    }
  };
  
  return (
    <Layout>
      <div className="py-16 container mx-auto px-4 sm:px-6">
        {tool && (
          <>
            <ToolHeader 
              title={tool.title}
              description={tool.description}
              icon={tool.icon}
              color={tool.color}
              bgColor={tool.bgColor}
            />
            
            <StepProgress
              steps={tool.steps}
              currentStep={step}
            />
          </>
        )}
        
        <div className="max-w-4xl mx-auto">
          {renderStep()}
        </div>
      </div>
    </Layout>
  );
};

export default SplitPDF;
