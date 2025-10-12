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
import { Text, Settings, HelpCircle, Stamp, RotateCw, Move } from "lucide-react";

interface WatermarkOptions {
  type: string;
  text?: string;
  position: string;
  fontSize?: number;
  opacity?: number;
  color?: { r: number; g: number; b: number };
  rotation?: number;
  allPages?: boolean;
  pageRange?: { start?: number; end?: number };
}

const WatermarkPDF: React.FC = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [step, setStep] = useState(1);
  const [watermarkedPdfUrl, setWatermarkedPdfUrl] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [processingComplete, setProcessingComplete] = useState(false);
  const [totalPages, setTotalPages] = useState<number>(0);
  const [watermarkOptions, setWatermarkOptions] = useState<WatermarkOptions>({
    type: 'text',
    text: 'CONFIDENTIAL',
    position: 'center',
    fontSize: 48,
    opacity: 0.3,
    color: { r: 0, g: 0, b: 0 },
    rotation: 45,
    allPages: true,
    pageRange: { start: undefined, end: undefined }
  });
  
  // Get the tool data
  const tool = getToolById("watermark-pdf");
  const { toast } = useToast();
  
  // Initialize PDF operations
  const { addWatermark, isLoading, error, getFriendlyErrorMessage } = usePdfOperations({
    onSuccess: (data: Blob, filename: string) => {
      // Create URL for the blob data
      const url = window.URL.createObjectURL(new Blob([data], { type: 'application/pdf' }));
      
      setWatermarkedPdfUrl(url);
      setProcessing(false);
      setProcessingComplete(true);
      setStep(3);
      
      toast({
        title: "Success!",
        description: "Your watermarked PDF is ready for download.",
        duration: 5000,
      });
    },
    onError: (error: Error) => {
      setProcessing(false);
      toast({
        title: "Error",
        description: error.message || "An error occurred while adding watermark to your PDF file.",
        variant: "destructive",
        duration: 5000,
      });
    }
  });
  
  // Clean up URL objects when component unmounts
  useEffect(() => {
    return () => {
      if (watermarkedPdfUrl) {
        URL.revokeObjectURL(watermarkedPdfUrl);
      }
    };
  }, [watermarkedPdfUrl]);
  
  // Handle file uploads
  const handleFilesSelected = (selectedFiles: File[]) => {
    // Only take the first file for watermarking
    if (selectedFiles.length > 0) {
      const file = selectedFiles[0];
      
      // Validate file is a PDF
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        toast({
          title: "Invalid File Type",
          description: "Please select a PDF file for watermarking.",
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
  
  // Update watermark options
  const updateWatermarkOptions = (field: keyof WatermarkOptions, value: any) => {
    setWatermarkOptions(prev => ({
      ...prev,
      [field]: value
    }));
  };
  
  // Update color value
  const updateColorValue = (colorComponent: 'r' | 'g' | 'b', value: number) => {
    setWatermarkOptions(prev => ({
      ...prev,
      color: {
        ...prev.color,
        [colorComponent]: value / 255  // Convert 0-255 to 0-1
      }
    }));
  };
  
  // Update page range
  const updatePageRange = (field: 'start' | 'end', value: number | undefined) => {
    setWatermarkOptions(prev => ({
      ...prev,
      pageRange: {
        ...prev.pageRange,
        [field]: value
      }
    }));
  };
  
  // Handle adding watermark
  const handleAddWatermark = async () => {
    setProcessing(true);
    
    // Reset any previous URL
    setWatermarkedPdfUrl(null);
    
    try {
      if (files.length !== 1) {
        toast({
          title: "Error",
          description: "Please select exactly one PDF file to add watermark.",
          variant: "destructive",
          duration: 5000,
        });
        setProcessing(false);
        return;
      }
      
      // Validate options
      if (!watermarkOptions.position) {
        toast({
          title: "Error",
          description: "Please select a position for the watermark.",
          variant: "destructive",
          duration: 5000,
        });
        setProcessing(false);
        return;
      }
      
      if (watermarkOptions.type === 'text' && !watermarkOptions.text) {
        toast({
          title: "Error",
          description: "Please enter text for the watermark.",
          variant: "destructive",
          duration: 5000,
        });
        setProcessing(false);
        return;
      }
      
      // Clone the options to avoid modifying state directly
      const options = { ...watermarkOptions };
      
      // Clean up the page range if empty values are provided
      if (!options.allPages && options.pageRange) {
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
      await addWatermark(files[0], options);
    } catch (err) {
      // Show error toast
      toast({
        title: "Error",
        description: error ? getFriendlyErrorMessage(error) : "An error occurred while adding watermark to your PDF file.",
        variant: "destructive",
        duration: 5000,
      });
      console.error("Error adding watermark:", err);
      setProcessing(false);
    }
  };
  
  // Reset the form to start over
  const handleReset = () => {
    // Clean up the URL object to avoid memory leaks
    if (watermarkedPdfUrl) {
      URL.revokeObjectURL(watermarkedPdfUrl);
    }
    
    setFiles([]);
    setWatermarkOptions({
      type: 'text',
      text: 'CONFIDENTIAL',
      position: 'center',
      fontSize: 48,
      opacity: 0.3,
      color: { r: 0, g: 0, b: 0 },
      rotation: 45,
      allPages: true,
      pageRange: { start: undefined, end: undefined }
    });
    setStep(1);
    setWatermarkedPdfUrl(null);
    setProcessingComplete(false);
    setProcessing(false);
    setTotalPages(0);
  };
  
  // Positions for watermark
  const positions = [
    { value: 'top-left', label: 'Top Left' },
    { value: 'top-center', label: 'Top Center' },
    { value: 'top-right', label: 'Top Right' },
    { value: 'center-left', label: 'Center Left' },
    { value: 'center', label: 'Center' },
    { value: 'center-right', label: 'Center Right' },
    { value: 'bottom-left', label: 'Bottom Left' },
    { value: 'bottom-center', label: 'Bottom Center' },
    { value: 'bottom-right', label: 'Bottom Right' },
  ];
  
  // Common watermark text presets
  const textPresets = [
    "CONFIDENTIAL",
    "DRAFT",
    "SAMPLE",
    "DO NOT COPY",
    "FOR REVIEW ONLY",
    "INTERNAL USE ONLY",
  ];
  
  // Color presets
  const colorPresets = [
    { label: 'Black', r: 0, g: 0, b: 0 },
    { label: 'Dark Gray', r: 77, g: 77, b: 77 },
    { label: 'Gray', r: 128, g: 128, b: 128 },
    { label: 'Red', r: 255, g: 0, b: 0 },
    { label: 'Blue', r: 0, g: 0, b: 255 },
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
            <h3 className="text-lg font-medium mb-4">Configure Watermark</h3>
            <div className="border rounded-lg p-6 bg-secondary/30">
              <div className="space-y-4">
                {/* Watermark Type (currently only text is supported) */}
                <div>
                  <label className="block text-sm font-medium mb-1">Watermark Type</label>
                  <div className="flex gap-4">
                    <button
                      type="button"
                      onClick={() => updateWatermarkOptions('type', 'text')}
                      className={cn(
                        "py-2 px-4 rounded-md text-sm flex items-center",
                        watermarkOptions.type === 'text'
                          ? "bg-primary text-primary-foreground"
                          : "bg-secondary hover:bg-secondary/80"
                      )}
                    >
                      <Text className="w-4 h-4 mr-2" />
                      Text
                    </button>
                  </div>
                </div>
                
                {/* Watermark Text */}
                {watermarkOptions.type === 'text' && (
                  <div>
                    <label className="block text-sm font-medium mb-1">Watermark Text</label>
                    <input
                      type="text"
                      className={cn(
                        "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm",
                        "ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium",
                        "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2",
                        "focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      )}
                      value={watermarkOptions.text}
                      onChange={(e) => updateWatermarkOptions('text', e.target.value)}
                      placeholder="Enter watermark text"
                    />
                    
                    {/* Text presets */}
                    <div className="mt-2 flex flex-wrap gap-2">
                      {textPresets.map((preset) => (
                        <button
                          key={preset}
                          type="button"
                          onClick={() => updateWatermarkOptions('text', preset)}
                          className={cn(
                            "py-1 px-2 rounded-md text-xs",
                            watermarkOptions.text === preset
                              ? "bg-primary text-primary-foreground"
                              : "bg-secondary hover:bg-secondary/80"
                          )}
                        >
                          {preset}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Watermark Position */}
                <div>
                  <div className="flex items-center mb-1">
                    <label className="block text-sm font-medium">Position</label>
                    <Move className="w-4 h-4 ml-1 text-muted-foreground" />
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    {positions.map((pos) => (
                      <button
                        key={pos.value}
                        type="button"
                        onClick={() => updateWatermarkOptions('position', pos.value)}
                        className={cn(
                          "py-2 px-3 rounded-md text-sm",
                          watermarkOptions.position === pos.value
                            ? "bg-primary text-primary-foreground"
                            : "bg-secondary hover:bg-secondary/80"
                        )}
                      >
                        {pos.label}
                      </button>
                    ))}
                  </div>
                </div>
                
                {/* Rotation (for text watermarks) */}
                {watermarkOptions.type === 'text' && watermarkOptions.position === 'center' && (
                  <div>
                    <div className="flex items-center mb-1">
                      <label className="block text-sm font-medium">Rotation: {watermarkOptions.rotation}°</label>
                      <RotateCw className="w-4 h-4 ml-1 text-muted-foreground" />
                    </div>
                    <input
                      type="range"
                      min="-180"
                      max="180"
                      step="5"
                      className="w-full"
                      value={watermarkOptions.rotation}
                      onChange={(e) => updateWatermarkOptions('rotation', parseInt(e.target.value))}
                    />
                  </div>
                )}
                
                {/* Font Size (for text watermarks) */}
                {watermarkOptions.type === 'text' && (
                  <div>
                    <label className="block text-sm font-medium mb-1">Font Size: {watermarkOptions.fontSize}pt</label>
                    <input
                      type="range"
                      min="12"
                      max="96"
                      step="6"
                      className="w-full"
                      value={watermarkOptions.fontSize}
                      onChange={(e) => updateWatermarkOptions('fontSize', parseInt(e.target.value))}
                    />
                  </div>
                )}
                
                {/* Opacity */}
                <div>
                  <label className="block text-sm font-medium mb-1">Opacity: {Math.round(watermarkOptions.opacity * 100)}%</label>
                  <input
                    type="range"
                    min="5"
                    max="100"
                    step="5"
                    className="w-full"
                    value={watermarkOptions.opacity * 100}
                    onChange={(e) => updateWatermarkOptions('opacity', parseInt(e.target.value) / 100)}
                  />
                </div>
                
                {/* Color */}
                <div>
                  <label className="block text-sm font-medium mb-1">Color</label>
                  <div className="grid grid-cols-6 gap-2 mb-3">
                    {colorPresets.map((color) => (
                      <button
                        key={color.label}
                        type="button"
                        className={cn(
                          "w-full h-8 rounded-md border",
                          watermarkOptions.color.r === color.r/255 && 
                          watermarkOptions.color.g === color.g/255 && 
                          watermarkOptions.color.b === color.b/255 
                            ? "ring-2 ring-ring ring-offset-1" 
                            : "hover:ring-1 hover:ring-ring"
                        )}
                        style={{
                          backgroundColor: `rgb(${color.r}, ${color.g}, ${color.b})`
                        }}
                        title={color.label}
                        aria-label={`${color.label} color`}
                        onClick={() => updateWatermarkOptions('color', {
                          r: color.r/255,
                          g: color.g/255,
                          b: color.b/255
                        })}
                      />
                    ))}
                  </div>
                </div>
                
                {/* Page Range */}
                <div>
                  <div className="flex items-center mb-2">
                    <label className="text-sm font-medium">Page Coverage</label>
                  </div>
                  
                  <div className="flex items-center mb-2">
                    <input
                      type="checkbox"
                      id="allPages"
                      className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                      checked={watermarkOptions.allPages}
                      onChange={(e) => updateWatermarkOptions('allPages', e.target.checked)}
                    />
                    <label htmlFor="allPages" className="ml-2 text-sm">
                      Apply to all pages
                    </label>
                  </div>
                  
                  {!watermarkOptions.allPages && (
                    <div className="grid grid-cols-2 gap-4 mt-2">
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
                          value={watermarkOptions.pageRange?.start || ''}
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
                          value={watermarkOptions.pageRange?.end || ''}
                          onChange={(e) => {
                            const value = e.target.value ? parseInt(e.target.value) : undefined;
                            updatePageRange('end', value);
                          }}
                        />
                      </div>
                    </div>
                  )}
                  
                  <div className="text-xs text-muted-foreground mt-1">
                    {watermarkOptions.allPages 
                      ? `Watermark will be applied to all ${totalPages} pages` 
                      : 'Specify a range of pages to watermark'}
                  </div>
                </div>
                
                {/* Preview */}
                <div className="bg-background p-4 rounded-lg border">
                  <div className="text-sm font-medium mb-2 flex items-center">
                    <Stamp className="w-4 h-4 mr-2" />
                    Preview
                  </div>
                  <div className="h-32 border border-dashed border-muted-foreground rounded-lg flex items-center justify-center relative">
                    {/* Simulate watermark positioning */}
                    <div className={cn(
                      "absolute px-2 py-1",
                      watermarkOptions.position === 'top-left' && "top-2 left-2",
                      watermarkOptions.position === 'top-center' && "top-2 left-1/2 transform -translate-x-1/2",
                      watermarkOptions.position === 'top-right' && "top-2 right-2",
                      watermarkOptions.position === 'center-left' && "top-1/2 left-2 transform -translate-y-1/2",
                      watermarkOptions.position === 'center' && "top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2",
                      watermarkOptions.position === 'center-right' && "top-1/2 right-2 transform -translate-y-1/2",
                      watermarkOptions.position === 'bottom-left' && "bottom-2 left-2",
                      watermarkOptions.position === 'bottom-center' && "bottom-2 left-1/2 transform -translate-x-1/2",
                      watermarkOptions.position === 'bottom-right' && "bottom-2 right-2",
                    )}>
                      <span 
                        style={{
                          fontSize: `${watermarkOptions.fontSize}px`, 
                          opacity: watermarkOptions.opacity,
                          color: `rgb(${Math.round(watermarkOptions.color.r * 255)}, ${Math.round(watermarkOptions.color.g * 255)}, ${Math.round(watermarkOptions.color.b * 255)})`,
                          transform: watermarkOptions.position === 'center' && watermarkOptions.rotation ? `rotate(${watermarkOptions.rotation}deg)` : 'none'
                        }}
                      >
                        {watermarkOptions.text}
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
                    <h4 className="font-medium">Watermark Tips</h4>
                    <ul className="text-muted-foreground mt-1 space-y-1">
                      <li>Use a lower opacity (20-40%) for less intrusive watermarks</li>
                      <li>Center position with rotation works well for "across page" watermarks</li>
                      <li>For legal documents, consider "DRAFT" or "CONFIDENTIAL" text</li>
                      <li>Dark gray color is often less distracting than pure black</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
            
            <ProcessingButton 
              onClick={handleAddWatermark}
              isProcessing={processing}
              text="Add Watermark"
            />
          </div>
        );
      case 3:
        return (
          <OperationComplete 
            fileName={`${files[0]?.name.replace('.pdf', '')}_watermarked.pdf`}
            fileType="PDF Document"
            fileUrl={watermarkedPdfUrl}
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

export default WatermarkPDF;