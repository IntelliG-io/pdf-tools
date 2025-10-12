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
import {
  HelpCircle,
  Scissors,
  FileOutput,
  ChevronDown,
  ChevronUp,
  ListOrdered,
  Files,
  type LucideIcon,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

// Define split modes
type SplitMode = 'ranges' | 'pages' | 'everyNPages' | 'all';

interface PageRange {
  start: number;
  end: number;
}

interface SplitMethodConfig {
  title: string;
  description: string;
  hint: string;
  icon: LucideIcon;
  input?: {
    label: string;
    placeholder: string;
    description: string;
    tooltip: string;
    type: "text" | "number";
    min?: number;
  };
}

const splitMethods: Record<SplitMode, SplitMethodConfig> = {
  ranges: {
    title: "Extract Page Ranges",
    description: "Target specific chapters or sections.",
    hint: "Provide individual pages or ranges separated by commas.",
    icon: Scissors,
    input: {
      label: "Page ranges",
      placeholder: "e.g. 1-3, 5, 8-10",
      description: "Each range will be exported as its own PDF file.",
      tooltip: "Enter page numbers and/or page ranges separated by commas. For example: 1,3,5-12",
      type: "text",
    },
  },
  pages: {
    title: "Split at Specific Pages",
    description: "Break the PDF wherever you need new files.",
    hint: "List the pages where a new document should begin.",
    icon: FileOutput,
    input: {
      label: "Split after pages",
      placeholder: "e.g. 3, 5, 8",
      description: "We'll create a new PDF at each page number you provide.",
      tooltip:
        "Enter page numbers where the PDF should be split. Example: 3,5,8 creates 4 PDFs (pages 1-2, 3-4, 5-7, and 8-end).",
      type: "text",
    },
  },
  everyNPages: {
    title: "Split Every N Pages",
    description: "Generate evenly sized documents.",
    hint: "Tell us how many pages each new document should include.",
    icon: ListOrdered,
    input: {
      label: "Pages per document",
      placeholder: "Enter a number",
      description: "We'll keep creating new PDFs until we run out of pages.",
      tooltip:
        "Enter the number of pages each new PDF should contain. Example: 2 splits a 6-page PDF into three 2-page documents.",
      type: "number",
      min: 1,
    },
  },
  all: {
    title: "Extract All Pages",
    description: "Turn every page into its own PDF.",
    hint: "Perfect when you need each page as its own document.",
    icon: Files,
  },
};

const rangeInputConfig = splitMethods.ranges.input!;
const specificPagesInputConfig = splitMethods.pages.input!;
const everyNPagesInputConfig = splitMethods.everyNPages.input!;

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
          case "ranges": {
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
          }

          case "pages": {
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
          }
          
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
      case 2: {
        const activeMethod = splitMethods[splitMode];
        const ActiveIcon = activeMethod.icon;

        return (
          <div className="max-w-4xl mx-auto w-full animate-fade-in animate-once">
            <TooltipProvider delayDuration={150}>
              <div className="space-y-6">
                <div className="space-y-1">
                  <h3 className="text-xl font-semibold">Select Pages to Extract</h3>
                  <p className="text-sm text-muted-foreground">
                    Choose how you want to split your PDF and configure the details for the selected method.
                  </p>
                </div>

                <div className="grid gap-6 lg:grid-cols-[1.05fr_1fr]">
                  <Card className="h-full">
                    <CardHeader>
                      <CardTitle className="text-lg">Split method</CardTitle>
                      <CardDescription>
                        Choose the workflow that best matches what you need to export.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <RadioGroup
                        value={splitMode}
                        onValueChange={(value: SplitMode) => setSplitMode(value)}
                        className="grid gap-3 md:grid-cols-2"
                      >
                        {(Object.entries(splitMethods) as [SplitMode, SplitMethodConfig][]).map(([mode, method]) => {
                          const Icon = method.icon;
                          return (
                            <div key={mode}>
                              <RadioGroupItem value={mode} id={`split-mode-${mode}`} className="sr-only" />
                              <label
                                htmlFor={`split-mode-${mode}`}
                                className={cn(
                                  "flex h-full cursor-pointer flex-col gap-4 rounded-lg border p-4 text-left transition-colors",
                                  "bg-background hover:border-primary/40 hover:bg-primary/5",
                                  splitMode === mode && "border-primary bg-primary/5 shadow-sm ring-2 ring-primary/20",
                                )}
                              >
                                <div className="flex items-start gap-3">
                                  <div className="rounded-md bg-primary/10 p-2 text-primary">
                                    <Icon className="h-5 w-5" />
                                  </div>
                                  <div className="flex flex-col gap-1">
                                    <p className="font-medium leading-none">{method.title}</p>
                                  </div>
                                </div>
                                <p className="text-xs text-muted-foreground">{method.hint}</p>
                                {splitMode === mode && (
                                  <Badge
                                    variant="outline"
                                    className="mt-auto w-fit border-primary/40 bg-primary/10 text-primary"
                                  >
                                    Selected
                                  </Badge>
                                )}
                              </label>
                            </div>
                          );
                        })}
                      </RadioGroup>
                    </CardContent>
                  </Card>

                  <Card className="h-full">
                    <CardHeader className="flex flex-row items-start gap-3">
                      <div className="rounded-md bg-primary/10 p-2 text-primary">
                        <ActiveIcon className="h-5 w-5" />
                      </div>
                      <div className="space-y-1">
                        <CardTitle className="text-lg">{activeMethod.title}</CardTitle>
                        <CardDescription>{activeMethod.description}</CardDescription>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <p className="text-sm text-muted-foreground">{activeMethod.hint}</p>

                      {splitMode === "ranges" && (
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <Label htmlFor="page-range" className="text-sm font-medium">
                              {rangeInputConfig.label}
                            </Label>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <button
                                  type="button"
                                  className="rounded-full p-1 text-muted-foreground transition-colors hover:text-foreground"
                                >
                                  <HelpCircle className="h-4 w-4" />
                                  <span className="sr-only">Page range help</span>
                                </button>
                              </TooltipTrigger>
                              <TooltipContent side="top" align="end" className="max-w-xs text-xs">
                                {rangeInputConfig.tooltip}
                              </TooltipContent>
                            </Tooltip>
                          </div>
                          <Input
                            id="page-range"
                            placeholder={rangeInputConfig.placeholder}
                            value={pageRange}
                            onChange={(e) => setPageRange(e.target.value)}
                          />
                          <p className="text-xs text-muted-foreground">{rangeInputConfig.description}</p>
                        </div>
                      )}

                      {splitMode === "pages" && (
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <Label htmlFor="split-pages" className="text-sm font-medium">
                              {specificPagesInputConfig.label}
                            </Label>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <button
                                  type="button"
                                  className="rounded-full p-1 text-muted-foreground transition-colors hover:text-foreground"
                                >
                                  <HelpCircle className="h-4 w-4" />
                                  <span className="sr-only">Specific pages help</span>
                                </button>
                              </TooltipTrigger>
                              <TooltipContent side="top" align="end" className="max-w-xs text-xs">
                                {specificPagesInputConfig.tooltip}
                              </TooltipContent>
                            </Tooltip>
                          </div>
                          <Input
                            id="split-pages"
                            placeholder={specificPagesInputConfig.placeholder}
                            value={specificPages}
                            onChange={(e) => setSpecificPages(e.target.value)}
                          />
                          <p className="text-xs text-muted-foreground">{specificPagesInputConfig.description}</p>
                        </div>
                      )}

                      {splitMode === "everyNPages" && (
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <Label htmlFor="every-n-pages" className="text-sm font-medium">
                              {everyNPagesInputConfig.label}
                            </Label>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <button
                                  type="button"
                                  className="rounded-full p-1 text-muted-foreground transition-colors hover:text-foreground"
                                >
                                  <HelpCircle className="h-4 w-4" />
                                  <span className="sr-only">Pages per document help</span>
                                </button>
                              </TooltipTrigger>
                              <TooltipContent side="top" align="end" className="max-w-xs text-xs">
                                {everyNPagesInputConfig.tooltip}
                              </TooltipContent>
                            </Tooltip>
                          </div>
                          <Input
                            id="every-n-pages"
                            type="number"
                            min={everyNPagesInputConfig.min}
                            placeholder={everyNPagesInputConfig.placeholder}
                            value={everyNPages}
                            onChange={(e) => {
                              const value = parseInt(e.target.value, 10);
                              setEveryNPages(Number.isNaN(value) ? 0 : value);
                            }}
                          />
                          <p className="text-xs text-muted-foreground">{everyNPagesInputConfig.description}</p>
                        </div>
                      )}

                      {splitMode === "all" && (
                        <div className="rounded-lg border border-dashed border-primary/30 bg-primary/5 px-4 py-5">
                          <p className="text-sm font-medium text-primary">Each page becomes its own PDF</p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            We'll package the individual files together in a single ZIP download for you.
                          </p>
                        </div>
                      )}

                      <Separator />

                      <div className="space-y-3">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-auto px-0 text-sm font-medium text-primary hover:text-primary"
                          onClick={() => setAdvancedOptions(!advancedOptions)}
                        >
                          {advancedOptions ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          Advanced options
                        </Button>

                        {advancedOptions && (
                          <div className="space-y-3 rounded-lg border bg-muted/40 p-4">
                            <div className="space-y-2">
                              <Label htmlFor="filename-prefix" className="text-sm font-medium">
                                Filename prefix
                              </Label>
                              <Input
                                id="filename-prefix"
                                type="text"
                                placeholder="e.g. chapter, section, part"
                                value={filenamePrefix}
                                onChange={(e) => setFilenamePrefix(e.target.value)}
                              />
                              <p className="text-xs text-muted-foreground">
                                This prefix will be added to all created PDF files.
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
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
            </TooltipProvider>
          </div>
        );
      }
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
