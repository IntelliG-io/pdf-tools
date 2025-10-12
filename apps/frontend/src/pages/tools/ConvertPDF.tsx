import React, { useState, useEffect } from "react";
import Layout from "@/components/Layout";
import FileUpload from "@/components/FileUpload";
import { useToast } from "@/hooks/use-toast";
import usePdfOperations from "@/hooks/use-pdf-operations";
import { getToolById, outputFormats } from "@/constants/toolData";
import ToolHeader from "@/components/pdf-tools/ToolHeader";
import StepProgress from "@/components/pdf-tools/StepProgress";
import FormatSelection from "@/components/pdf-tools/FormatSelection";
import ProcessingButton from "@/components/pdf-tools/ProcessingButton";
import OperationComplete from "@/components/pdf-tools/OperationComplete";

const ConvertPDF: React.FC = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [step, setStep] = useState(1);
  const [selectedFormat, setSelectedFormat] = useState<string | null>(null);
  const [convertedFileUrl, setConvertedFileUrl] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [processingComplete, setProcessingComplete] = useState(false);
  
  // Get the tool data
  const tool = getToolById("convert-pdf");
  const { toast } = useToast();
  
  // Initialize PDF operations
  const { isLoading, error, getFriendlyErrorMessage } = usePdfOperations({
    onSuccess: (data: Blob, filename: string) => {
      // Create URL for the blob data
      const url = window.URL.createObjectURL(new Blob([data]));
      setConvertedFileUrl(url);
      setProcessing(false);
      setProcessingComplete(true);
      setStep(3);
      
      toast({
        title: "Success!",
        description: "Your converted file is ready for download.",
        duration: 5000,
      });
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
      
      if (step === 1) {
        setStep(2);
      }
    }
  };
  
  // Handle format selection
  const handleFormatSelect = (formatId: string) => {
    setSelectedFormat(formatId);
    setStep(3);
    
    // In a real implementation, you would call the conversion API here
    // For this example, we'll simulate a successful conversion
    setProcessing(true);
    
    // Simulate API call with timeout
    setTimeout(() => {
      setProcessing(false);
      setProcessingComplete(true);
      
      // Create a dummy blob for demonstration
      const blob = new Blob(['Dummy converted file content'], { type: 'application/octet-stream' });
      const url = URL.createObjectURL(blob);
      setConvertedFileUrl(url);
      
      toast({
        title: "Success!",
        description: "Your file has been converted successfully.",
        duration: 5000,
      });
    }, 2000);
  };
  
  // Reset the form to start over
  const handleReset = () => {
    // Clean up the URL object to avoid memory leaks
    if (convertedFileUrl) {
      URL.revokeObjectURL(convertedFileUrl);
    }
    
    setFiles([]);
    setSelectedFormat(null);
    setStep(1);
    setConvertedFileUrl(null);
    setProcessingComplete(false);
    setProcessing(false);
  };
  
  // Get file name with the selected format's extension
  const getConvertedFileName = () => {
    if (!files.length || !selectedFormat) return "converted.pdf";
    
    const originalName = files[0].name.split('.')[0] || "document";
    const format = outputFormats.find(f => f.id === selectedFormat);
    
    return `${originalName}${format?.extension || ".pdf"}`;
  };
  
  // Get file type description
  const getFileTypeDescription = () => {
    if (!selectedFormat) return "Converted Document";
    
    const format = outputFormats.find(f => f.id === selectedFormat);
    return `${format?.name || "PDF"} Document`;
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
          <FormatSelection 
            formats={outputFormats}
            selectedFormat={selectedFormat}
            onSelectFormat={handleFormatSelect}
          />
        );
      case 3:
        return (
          <OperationComplete 
            fileName={getConvertedFileName()}
            fileType={getFileTypeDescription()}
            fileUrl={convertedFileUrl}
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

export default ConvertPDF;
