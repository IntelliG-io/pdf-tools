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
import { downloadFile } from "@/services/api";
import { imageFormats, imageQualityOptions } from "@/constants/toolData";

// PDF to Image tool
const PdfToImage: React.FC = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [step, setStep] = useState(1);
  const [convertedFileUrl, setConvertedFileUrl] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [processingComplete, setProcessingComplete] = useState(false);
  const [pageCount, setPageCount] = useState(0);
  
  // Conversion options
  const [imageFormat, setImageFormat] = useState<string>("jpg");
  const [imageQuality, setImageQuality] = useState<string>("medium");
  const [grayscale, setGrayscale] = useState<boolean>(false);
  const [transparent, setTransparent] = useState<boolean>(false);
  const [pageRange, setPageRange] = useState<{ from?: number; to?: number }>({});
  const [specificPages, setSpecificPages] = useState<string>("");
  const [pageSelectionMode, setPageSelectionMode] = useState<string>("all");
  
  const tool = getToolById("pdf-to-image");
  const { toast } = useToast();
  
  // Initialize PDF operations
  const { convertPdfToImage, isLoading, error, getFriendlyErrorMessage } = usePdfOperations({
    onSuccess: (data: Blob, filename: string) => {
      // Create URL for the blob data (it's a ZIP file)
      const url = window.URL.createObjectURL(new Blob([data], {
        type: 'application/zip'
      }));
      setConvertedFileUrl(url);
      setProcessingComplete(true);
      
      toast({
        title: "Success!",
        description: `Your PDF has been converted to ${imageFormat.toUpperCase()} images.`,
        duration: 5000,
      });
      
      setProcessing(false);
      setStep(3);
    },
    onError: (error: Error) => {
      setProcessing(false);
      toast({
        title: "Error",
        description: error.message || "An error occurred while converting your PDF file.",
        variant: "destructive",
        duration: 5000,
      });
    }
  });
  
  // Clean up URL objects when component unmounts
  useEffect(() => {
    return () => {
      if (convertedFileUrl) {
        URL.revokeObjectURL(convertedFileUrl);
      }
    };
  }, [convertedFileUrl]);
  
  // Handle file uploads
  const handleFilesSelected = (selectedFiles: File[]) => {
    // Only take the first file for conversion
    if (selectedFiles.length > 0) {
      setFiles([selectedFiles[0]]);
      setStep(2);
    }
  };
  
  // Handle PDF to Image conversion
  const handleConvert = async () => {
    if (files.length === 0) {
      toast({
        title: "Error",
        description: "Please upload a PDF file first.",
        variant: "destructive",
        duration: 3000,
      });
      return;
    }
    
    setProcessing(true);
    
    try {
      // Create conversion options based on selected settings
      const options: any = {
        format: imageFormat,
        quality: imageQuality,
        grayscale: grayscale,
      };
      
      // Add transparency option for PNG format
      if (imageFormat === "png" && transparent) {
        options.transparent = transparent;
      }
      
      // Handle page selection
      if (pageSelectionMode === "range") {
        options.pageRange = pageRange;
      } else if (pageSelectionMode === "specific") {
        // Parse specific pages string to an array of numbers
        const pages = specificPages
          .split(",")
          .map(page => page.trim())
          .filter(page => /^\d+$/.test(page))
          .map(page => parseInt(page, 10));
        
        if (pages.length > 0) {
          options.specificPages = pages;
        }
      }
      
      // Perform the conversion
      const result = await convertPdfToImage(files[0], options);
      setPageCount(result.pageCount);
      
    } catch (error) {
      console.error("Conversion error:", error);
      // Error is already handled by usePdfOperations
    }
  };
  
  // Reset the form to start over
  const handleReset = () => {
    // Clean up the URL object to avoid memory leaks
    if (convertedFileUrl) {
      URL.revokeObjectURL(convertedFileUrl);
    }
    
    setFiles([]);
    setImageFormat("jpg");
    setImageQuality("medium");
    setGrayscale(false);
    setTransparent(false);
    setPageRange({});
    setSpecificPages("");
    setPageSelectionMode("all");
    setStep(1);
    setConvertedFileUrl(null);
    setProcessingComplete(false);
    setProcessing(false);
    setPageCount(0);
  };
  
  // Get file name with appropriate extension
  const getConvertedFileName = () => {
    if (!files.length) return "images.zip";
    
    const originalName = files[0].name.split('.')[0] || "document";
    return `${originalName}_images.zip`;
  };
  
  // Render different content based on the current step
  const renderStep = () => {
    switch (step) {
      case 1:
        return (
          <div className="max-w-xl mx-auto w-full">
            <FileUpload 
              onFilesSelected={handleFilesSelected}
              accept=".pdf"
              multiple={false}
            />
          </div>
        );
      case 2:
        return (
          <div className="max-w-xl mx-auto w-full bg-white p-6 rounded-lg shadow-md">
            <h3 className="text-lg font-medium mb-4">Conversion Options</h3>
            
            {files.length > 0 && (
              <div className="mb-6 p-3 bg-gray-50 rounded flex items-center">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-500 mr-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <path d="M14 2v6h6"></path>
                </svg>
                <span className="text-sm">{files[0].name}</span>
              </div>
            )}
            
            {/* Image Format Selection */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Image Format
              </label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {imageFormats.map(format => (
                  <button
                    key={format.id}
                    type="button"
                    className={`px-4 py-2 text-sm font-medium rounded-md ${
                      imageFormat === format.id 
                        ? "bg-fuchsia-100 text-fuchsia-700 border-2 border-fuchsia-500" 
                        : "bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200"
                    }`}
                    onClick={() => setImageFormat(format.id)}
                  >
                    {format.name}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Quality Selection */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Image Quality
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {imageQualityOptions.map(quality => (
                  <button
                    key={quality.id}
                    type="button"
                    className={`px-4 py-2 text-sm font-medium rounded-md ${
                      imageQuality === quality.id 
                        ? "bg-fuchsia-100 text-fuchsia-700 border-2 border-fuchsia-500" 
                        : "bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200"
                    }`}
                    onClick={() => setImageQuality(quality.id)}
                  >
                    {quality.name}
                    <span className="block text-xs mt-1 font-normal">
                      {quality.description}
                    </span>
                    <span className="block text-xs mt-1 font-normal">
                      {quality.dpi}
                    </span>
                  </button>
                ))}
              </div>
            </div>
            
            {/* Additional Options */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Additional Options
              </label>
              <div className="space-y-3">
                <div className="flex items-center">
                  <input
                    id="grayscale"
                    type="checkbox"
                    className="h-4 w-4 text-fuchsia-600 focus:ring-fuchsia-500 border-gray-300 rounded"
                    checked={grayscale}
                    onChange={(e) => setGrayscale(e.target.checked)}
                  />
                  <label htmlFor="grayscale" className="ml-2 block text-sm text-gray-700">
                    Convert to grayscale
                  </label>
                </div>
                
                {imageFormat === "png" && (
                  <div className="flex items-center">
                    <input
                      id="transparent"
                      type="checkbox"
                      className="h-4 w-4 text-fuchsia-600 focus:ring-fuchsia-500 border-gray-300 rounded"
                      checked={transparent}
                      onChange={(e) => setTransparent(e.target.checked)}
                    />
                    <label htmlFor="transparent" className="ml-2 block text-sm text-gray-700">
                      Enable transparency (PNG only)
                    </label>
                  </div>
                )}
              </div>
            </div>
            
            {/* Page Selection */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Pages to Convert
              </label>
              <div className="space-y-3">
                <div className="flex items-center">
                  <input
                    id="all-pages"
                    type="radio"
                    name="page-selection"
                    className="h-4 w-4 text-fuchsia-600 focus:ring-fuchsia-500 border-gray-300"
                    checked={pageSelectionMode === "all"}
                    onChange={() => setPageSelectionMode("all")}
                  />
                  <label htmlFor="all-pages" className="ml-2 block text-sm text-gray-700">
                    All pages
                  </label>
                </div>
                
                <div className="flex items-center">
                  <input
                    id="page-range"
                    type="radio"
                    name="page-selection"
                    className="h-4 w-4 text-fuchsia-600 focus:ring-fuchsia-500 border-gray-300"
                    checked={pageSelectionMode === "range"}
                    onChange={() => setPageSelectionMode("range")}
                  />
                  <label htmlFor="page-range" className="ml-2 block text-sm text-gray-700">
                    Page range
                  </label>
                </div>
                
                {pageSelectionMode === "range" && (
                  <div className="pl-6 grid grid-cols-2 gap-3">
                    <div>
                      <label htmlFor="from-page" className="block text-xs text-gray-700 mb-1">
                        From
                      </label>
                      <input
                        id="from-page"
                        type="number"
                        min="1"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-fuchsia-500 focus:border-fuchsia-500 sm:text-sm"
                        value={pageRange.from || ""}
                        onChange={(e) => 
                          setPageRange({...pageRange, from: e.target.value ? parseInt(e.target.value, 10) : undefined})
                        }
                      />
                    </div>
                    <div>
                      <label htmlFor="to-page" className="block text-xs text-gray-700 mb-1">
                        To
                      </label>
                      <input
                        id="to-page"
                        type="number"
                        min={pageRange.from || 1}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-fuchsia-500 focus:border-fuchsia-500 sm:text-sm"
                        value={pageRange.to || ""}
                        onChange={(e) =>
                          setPageRange({...pageRange, to: e.target.value ? parseInt(e.target.value, 10) : undefined})
                        }
                      />
                    </div>
                  </div>
                )}
                
                <div className="flex items-center">
                  <input
                    id="specific-pages"
                    type="radio"
                    name="page-selection"
                    className="h-4 w-4 text-fuchsia-600 focus:ring-fuchsia-500 border-gray-300"
                    checked={pageSelectionMode === "specific"}
                    onChange={() => setPageSelectionMode("specific")}
                  />
                  <label htmlFor="specific-pages" className="ml-2 block text-sm text-gray-700">
                    Specific pages
                  </label>
                </div>
                
                {pageSelectionMode === "specific" && (
                  <div className="pl-6">
                    <input
                      type="text"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-fuchsia-500 focus:border-fuchsia-500 sm:text-sm"
                      placeholder="e.g., 1, 3, 5-7"
                      value={specificPages}
                      onChange={(e) => setSpecificPages(e.target.value)}
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Enter page numbers separated by commas (e.g., 1, 3, 5)
                    </p>
                  </div>
                )}
              </div>
            </div>
            
            <div className="mt-8">
              <ProcessingButton
                onClick={handleConvert}
                processing={processing}
                text="Convert to Images"
                processingText="Converting..."
              />
            </div>
          </div>
        );
      case 3:
        return (
          <OperationComplete 
            fileName={getConvertedFileName()}
            fileType="ZIP Archive"
            fileUrl={convertedFileUrl}
            onReset={handleReset}
            customMessage={`Successfully converted to ${pageCount} image${pageCount !== 1 ? 's' : ''}.`}
          />
        );
      default:
        return null;
    }
  };
  
  return (
    <Layout>
      <div className="py-16 container mx-auto px-4 sm:px-6">
        <ToolHeader 
          title={tool?.title || "PDF to Image"}
          description={tool?.description || "Convert PDF pages to JPG, PNG, or other image formats"}
          icon={tool?.icon}
          color={tool?.color || "text-fuchsia-600"}
          bgColor={tool?.bgColor || "bg-fuchsia-100"}
        />
        
        <StepProgress
          steps={tool?.steps || [
            "Upload your PDF file",
            "Configure image conversion options",
            "Convert and download your images"
          ]}
          currentStep={step}
        />
        
        <div className="max-w-4xl mx-auto">
          {renderStep()}
        </div>
      </div>
    </Layout>
  );
};

export default PdfToImage;
