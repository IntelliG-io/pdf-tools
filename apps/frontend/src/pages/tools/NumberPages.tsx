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
import { cn } from "@/lib/utils";
import { Text, Settings, HelpCircle, Plus, Trash, List } from "lucide-react";

interface PageNumberOptions {
  position: string;
  startNumber?: number;
  prefix?: string;
  suffix?: string;
  fontSize?: number;
  opacity?: number;
  fontColor?: { r: number; g: number; b: number };
  margin?: number;
  skipFirstPage?: boolean;
  skipLastPage?: boolean;
  pageRange?: { start?: number; end?: number };
}

const NumberPages: React.FC = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [step, setStep] = useState(1);
  const [numberedPdfUrl, setNumberedPdfUrl] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [processingComplete, setProcessingComplete] = useState(false);
  const [totalPages, setTotalPages] = useState<number>(0);
  const [pageNumberOptions, setPageNumberOptions] = useState<PageNumberOptions>({
    position: 'bottom-center',
    startNumber: 1,
    prefix: '',
    suffix: '',
    fontSize: 12,
    opacity: 1.0,
    fontColor: { r: 0, g: 0, b: 0 },
    margin: 25,
    skipFirstPage: false,
    skipLastPage: false,
    pageRange: { start: undefined, end: undefined }
  });
  
  // Get the tool data
  const tool = getToolById("number-pages");
  const { toast } = useToast();
  
  // Initialize PDF operations
  const { addPageNumbers, isLoading, error, getFriendlyErrorMessage } = usePdfOperations({
    onSuccess: (data: Blob, filename: string) => {
      // Create URL for the blob data
      const url = window.URL.createObjectURL(new Blob([data], { type: 'application/pdf' }));
      
      setNumberedPdfUrl(url);
      setProcessing(false);
      setProcessingComplete(true);
      setStep(3);
      
      toast({
        title: "Success!",
        description: "Your PDF with page numbers is ready for download.",
        duration: 5000,
      });
    },
    onError: (error: Error) => {
      setProcessing(false);
      toast({
        title: "Error",
        description: error.message || "An error occurred while adding page numbers to your PDF file.",
        variant: "destructive",
        duration: 5000,
      });
    }
  });
  
  // Clean up URL objects when component unmounts
  useEffect(() => {
    return () => {
      if (numberedPdfUrl) {
        URL.revokeObjectURL(numberedPdfUrl);
      }
    };
  }, [numberedPdfUrl]);
  
  // Handle file uploads
  const handleFilesSelected = (selectedFiles: File[]) => {
    // Only take the first file for page numbering
    if (selectedFiles.length > 0) {
      const file = selectedFiles[0];
      
      // Validate file is a PDF
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        toast({
          title: "Invalid File Type",
          description: "Please select a PDF file for page numbering.",
          variant: "destructive",
          duration: 5000,
        });
        return;
      }
      
      setFiles([file]);
      
      // Simple estimate of page count based on file size
      // In a real application, you'd use the pdf-lib library to get the exact page count
      const estimatedPages = Math.max(1, Math.floor(file.size / 50000));
      setTotalPages(estimatedPages);
      
      if (step === 1) {
        setStep(2);
      }
    }
  };
  
  // Update number options
  const updateNumberOptions = (field: keyof PageNumberOptions, value: any) => {
    setPageNumberOptions(prev => ({
      ...prev,
      [field]: value
    }));
  };
  
  // Update color value
  const updateColorValue = (colorComponent: 'r' | 'g' | 'b', value: number) => {
    setPageNumberOptions(prev => ({
      ...prev,
      fontColor: {
        ...prev.fontColor,
        [colorComponent]: value / 255  // Convert 0-255 to 0-1
      }
    }));
  };
  
  // Update page range
  const updatePageRange = (field: 'start' | 'end', value: number | undefined) => {
    setPageNumberOptions(prev => ({
      ...prev,
      pageRange: {
        ...prev.pageRange,
        [field]: value
      }
    }));
  };
  
  // Handle adding page numbers
  const handleAddPageNumbers = async () => {
    setProcessing(true);
    
    // Reset any previous URL
    setNumberedPdfUrl(null);
    
    try {
      if (files.length !== 1) {
        toast({
          title: "Error",
          description: "Please select exactly one PDF file to add page numbers.",
          variant: "destructive",
          duration: 5000,
        });
        setProcessing(false);
        return;
      }
      
      // Validate options
      if (!pageNumberOptions.position) {
        toast({
          title: "Error",
          description: "Please select a position for the page numbers.",
          variant: "destructive",
          duration: 5000,
        });
        setProcessing(false);
        return;
      }
      
      // Clone the options to avoid modifying state directly
      const options = { ...pageNumberOptions };
      
      // Always ensure startNumber is at least 1
      options.startNumber = Math.max(1, options.startNumber || 1);
      
      // Clean up the page range if empty values are provided
      if (options.pageRange) {
        const pageRange: {start?: number, end?: number} = {};
        
        if (options.pageRange.start && options.pageRange.start > 0) {
          pageRange.start = options.pageRange.start;
        }
        
        if (options.pageRange.end && options.pageRange.end > 0) {
          pageRange.end = options.pageRange.end;
        }
        
        options.pageRange = Object.keys(pageRange).length > 0 ? pageRange : undefined;
      }
      
      // Send to API
      await addPageNumbers(files[0], options);
    } catch (err) {
      // Show error toast
      toast({
        title: "Error",
        description: error ? getFriendlyErrorMessage(error) : "An error occurred while adding page numbers to your PDF file.",
        variant: "destructive",
        duration: 5000,
      });
      console.error("Error adding page numbers:", err);
      setProcessing(false);
    }
  };
  
  // Reset the form to start over
  const handleReset = () => {
    // Clean up the URL object to avoid memory leaks
    if (numberedPdfUrl) {
      URL.revokeObjectURL(numberedPdfUrl);
    }
    
    setFiles([]);
    setPageNumberOptions({
      position: 'bottom-center',
      startNumber: 1,
      prefix: '',
      suffix: '',
      fontSize: 12,
      opacity: 1.0,
      fontColor: { r: 0, g: 0, b: 0 },
      margin: 25,
      skipFirstPage: false,
      skipLastPage: false,
      pageRange: { start: undefined, end: undefined }
    });
    setStep(1);
    setNumberedPdfUrl(null);
    setProcessingComplete(false);
    setProcessing(false);
    setTotalPages(0);
  };
  
  // Positions for page numbers
  const positions = [
    { value: 'top-left', label: 'Top Left' },
    { value: 'top-center', label: 'Top Center' },
    { value: 'top-right', label: 'Top Right' },
    { value: 'bottom-left', label: 'Bottom Left' },
    { value: 'bottom-center', label: 'Bottom Center' },
    { value: 'bottom-right', label: 'Bottom Right' },
  ];
  
  // Color presets
  const colorPresets = [
    { label: 'Black', r: 0, g: 0, b: 0 },
    { label: 'Dark Gray', r: 77, g: 77, b: 77 },
    { label: 'Gray', r: 128, g: 128, b: 128 },
    { label: 'Blue', r: 0, g: 0, b: 255 },
    { label: 'Red', r: 255, g: 0, b: 0 },
    { label: 'Green', r: 0, g: 128, b: 0 },
  ];
  
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
            <h3 className="text-lg font-medium mb-4">Configure Page Numbers</h3>
            <div className="border rounded-lg p-6 bg-secondary/30">
              <div className="space-y-4">
                {/* Position */}
                <div>
                  <label className="block text-sm font-medium mb-1">Position</label>
                  <div className="grid grid-cols-3 gap-2">
                    {positions.map((pos) => (
                      <button
                        key={pos.value}
                        type="button"
                        onClick={() => updateNumberOptions('position', pos.value)}
                        className={cn(
                          "py-2 px-3 rounded-md text-sm",
                          pageNumberOptions.position === pos.value
                            ? "bg-primary text-primary-foreground"
                            : "bg-secondary hover:bg-secondary/80"
                        )}
                      >
                        {pos.label}
                      </button>
                    ))}
                  </div>
                </div>
                
                {/* Basic settings */}
                <div className="grid grid-cols-2 gap-4">
                  {/* Start Number */}
                  <div>
                    <label className="block text-sm font-medium mb-1">Start Number</label>
                    <input
                      type="number"
                      min="1"
                      className={cn(
                        "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm",
                        "ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium",
                        "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2",
                        "focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      )}
                      value={pageNumberOptions.startNumber}
                      onChange={(e) => updateNumberOptions('startNumber', parseInt(e.target.value) || 1)}
                    />
                  </div>
                  
                  {/* Font Size */}
                  <div>
                    <label className="block text-sm font-medium mb-1">Font Size</label>
                    <select
                      className={cn(
                        "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm",
                        "ring-offset-background focus-visible:outline-none focus-visible:ring-2",
                        "focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      )}
                      value={pageNumberOptions.fontSize}
                      onChange={(e) => updateNumberOptions('fontSize', parseInt(e.target.value))}
                    >
                      {[8, 10, 12, 14, 16, 18, 20, 24, 28, 32].map((size) => (
                        <option key={size} value={size}>{size} pt</option>
                      ))}
                    </select>
                  </div>
                </div>
                
                {/* Text customization */}
                <div className="grid grid-cols-2 gap-4">
                  {/* Prefix */}
                  <div>
                    <label className="block text-sm font-medium mb-1">Prefix</label>
                    <input
                      type="text"
                      placeholder="Page "
                      className={cn(
                        "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm",
                        "ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium",
                        "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2",
                        "focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      )}
                      value={pageNumberOptions.prefix}
                      onChange={(e) => updateNumberOptions('prefix', e.target.value)}
                    />
                  </div>
                  
                  {/* Suffix */}
                  <div>
                    <label className="block text-sm font-medium mb-1">Suffix</label>
                    <input
                      type="text"
                      placeholder=" of 10"
                      className={cn(
                        "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm",
                        "ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium",
                        "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2",
                        "focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      )}
                      value={pageNumberOptions.suffix}
                      onChange={(e) => updateNumberOptions('suffix', e.target.value)}
                    />
                  </div>
                </div>
                
                {/* Color and Opacity */}
                <div>
                  <label className="block text-sm font-medium mb-1">Color</label>
                  <div className="grid grid-cols-6 gap-2 mb-3">
                    {colorPresets.map((color) => (
                      <button
                        key={color.label}
                        type="button"
                        className={cn(
                          "w-full h-8 rounded-md border",
                          pageNumberOptions.fontColor.r === color.r/255 && 
                          pageNumberOptions.fontColor.g === color.g/255 && 
                          pageNumberOptions.fontColor.b === color.b/255 
                            ? "ring-2 ring-ring ring-offset-1" 
                            : "hover:ring-1 hover:ring-ring"
                        )}
                        style={{
                          backgroundColor: `rgb(${color.r}, ${color.g}, ${color.b})`
                        }}
                        title={color.label}
                        aria-label={`${color.label} color`}
                        onClick={() => updateNumberOptions('fontColor', {
                          r: color.r/255,
                          g: color.g/255,
                          b: color.b/255
                        })}
                      />
                    ))}
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium mb-1">Opacity: {Math.round(pageNumberOptions.opacity * 100)}%</label>
                    <input
                      type="range"
                      min="10"
                      max="100"
                      step="5"
                      className="w-full"
                      value={pageNumberOptions.opacity * 100}
                      onChange={(e) => updateNumberOptions('opacity', parseInt(e.target.value) / 100)}
                    />
                  </div>
                </div>
                
                {/* Margin */}
                <div>
                  <label className="block text-sm font-medium mb-1">Margin from Edge: {pageNumberOptions.margin}px</label>
                  <input
                    type="range"
                    min="5"
                    max="50"
                    step="5"
                    className="w-full"
                    value={pageNumberOptions.margin}
                    onChange={(e) => updateNumberOptions('margin', parseInt(e.target.value))}
                  />
                </div>
                
                {/* Checkboxes for skipping pages */}
                <div className="space-y-2">
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="skipFirstPage"
                      className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                      checked={pageNumberOptions.skipFirstPage}
                      onChange={(e) => updateNumberOptions('skipFirstPage', e.target.checked)}
                    />
                    <label htmlFor="skipFirstPage" className="ml-2 text-sm">
                      Skip first page (e.g., for title pages)
                    </label>
                  </div>
                  
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="skipLastPage"
                      className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                      checked={pageNumberOptions.skipLastPage}
                      onChange={(e) => updateNumberOptions('skipLastPage', e.target.checked)}
                    />
                    <label htmlFor="skipLastPage" className="ml-2 text-sm">
                      Skip last page (e.g., for back covers)
                    </label>
                  </div>
                </div>
                
                {/* Page Range */}
                <div>
                  <div className="flex items-center mb-1">
                    <label className="block text-sm font-medium">Specific Page Range</label>
                    <div className="ml-1 text-xs text-muted-foreground">(Optional)</div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <input
                        type="number"
                        min="1"
                        max={totalPages || 999}
                        placeholder="Start page"
                        className={cn(
                          "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm",
                          "ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium",
                          "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2",
                          "focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                        )}
                        value={pageNumberOptions.pageRange?.start || ''}
                        onChange={(e) => {
                          const value = e.target.value ? parseInt(e.target.value) : undefined;
                          updatePageRange('start', value);
                        }}
                      />
                    </div>
                    
                    <div>
                      <input
                        type="number"
                        min="1"
                        max={totalPages || 999}
                        placeholder="End page"
                        className={cn(
                          "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm",
                          "ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium",
                          "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2",
                          "focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                        )}
                        value={pageNumberOptions.pageRange?.end || ''}
                        onChange={(e) => {
                          const value = e.target.value ? parseInt(e.target.value) : undefined;
                          updatePageRange('end', value);
                        }}
                      />
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    Leave empty to number all pages (estimated {totalPages} pages)
                  </div>
                </div>
                
                {/* Preview */}
                <div className="bg-background p-4 rounded-lg border">
                  <div className="text-sm font-medium mb-2 flex items-center">
                    <Text className="w-4 h-4 mr-2" />
                    Preview
                  </div>
                  <div className="h-20 border border-dashed border-muted-foreground rounded-lg flex items-center justify-center relative">
                    {/* Simulate page positioning */}
                    <div className={cn(
                      "absolute px-2 py-1",
                      pageNumberOptions.position === 'top-left' && "top-2 left-2",
                      pageNumberOptions.position === 'top-center' && "top-2 left-1/2 transform -translate-x-1/2",
                      pageNumberOptions.position === 'top-right' && "top-2 right-2",
                      pageNumberOptions.position === 'bottom-left' && "bottom-2 left-2",
                      pageNumberOptions.position === 'bottom-center' && "bottom-2 left-1/2 transform -translate-x-1/2",
                      pageNumberOptions.position === 'bottom-right' && "bottom-2 right-2",
                    )}>
                      <span 
                        style={{
                          fontSize: `${pageNumberOptions.fontSize}px`, 
                          opacity: pageNumberOptions.opacity,
                          color: `rgb(${Math.round(pageNumberOptions.fontColor.r * 255)}, ${Math.round(pageNumberOptions.fontColor.g * 255)}, ${Math.round(pageNumberOptions.fontColor.b * 255)})`
                        }}
                      >
                        {pageNumberOptions.prefix}{pageNumberOptions.startNumber}{pageNumberOptions.suffix}
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground">Page content</div>
                  </div>
                </div>
              </div>
              
              <div className="bg-primary/5 p-4 rounded-lg mt-4 text-sm">
                <div className="flex items-start">
                  <HelpCircle className="w-5 h-5 text-primary mr-2 flex-shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-medium">Page Numbering Tips</h4>
                    <ul className="text-muted-foreground mt-1 space-y-1">
                      <li>Use prefix "Page " and suffix " of X" for "Page 1 of X" format</li>
                      <li>For legal documents, try bottom-center position</li>
                      <li>Skip first page for title pages or covers</li>
                      <li>Use a lower opacity for a more subtle appearance</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
            
            <ProcessingButton 
              onClick={handleAddPageNumbers}
              isProcessing={processing}
              text="Add Page Numbers"
            />
          </div>
        );
      case 3:
        return (
          <OperationComplete 
            fileName={`${files[0]?.name.replace('.pdf', '')}_numbered.pdf`}
            fileType="PDF Document"
            fileUrl={numberedPdfUrl}
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

export default NumberPages;
