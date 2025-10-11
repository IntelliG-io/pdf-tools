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
import { Link } from "react-router-dom";

// Define compression levels with their descriptions
const compressionLevels = [
  {
    id: "low",
    name: "Low Compression",
    description: "Best quality, minimal size reduction",
    expectedReduction: "10-20%",
    icon: "🟢"
  },
  {
    id: "medium",
    name: "Medium Compression",
    description: "Balanced quality and file size",
    expectedReduction: "30-50%",
    icon: "🟡"
  },
  {
    id: "high",
    name: "High Compression",
    description: "Smaller file size, acceptable quality",
    expectedReduction: "50-70%",
    icon: "🟠"
  },
  {
    id: "maximum",
    name: "Maximum Compression",
    description: "Smallest possible size, reduced quality",
    expectedReduction: "70-90%",
    icon: "🔴"
  }
];

const CompressPDF: React.FC = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [step, setStep] = useState(1);
  const [selectedLevel, setSelectedLevel] = useState<string>("medium"); // Default to medium
  const [compressedFileUrl, setCompressedFileUrl] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [processingComplete, setProcessingComplete] = useState(false);
  const [fileSize, setFileSize] = useState<{ original: number; compressed: number | null }>({
    original: 0,
    compressed: null
  });
  
  // Get the tool data
  const tool = getToolById("compress-pdf");
  const { toast } = useToast();
  
  // Create a ref to hold compression stats
  const compressionRatioRef = React.useRef(86); // Default to 86% based on logs
  
  // Initialize PDF operations with completely rewritten onSuccess handler
  const { compressPdf, isLoading, error, getFriendlyErrorMessage } = usePdfOperations({
    onSuccess: (result: any, filename: string) => {
      console.log('Full compression result:', result);
      
      // Handle both direct Blob result and structured result with stats
      let pdfData: Blob;
      let compressionRatio = 0;
      let compressedSize = 0;
      
      // Check if result is a Blob directly or has a file property
      if (result instanceof Blob) {
        // Direct Blob result
        pdfData = result;
        compressedSize = result.size;
        // We don't have stats in this case, use a default ratio
        compressionRatio = Math.max(0, Math.round((1 - (result.size / fileSize.original)) * 100));
      } else if (result && typeof result === 'object') {
        // Structured result with file and stats
        if (result.file instanceof Blob) {
          pdfData = result.file;
          compressedSize = result.file.size;
          
          // Get stats if available
          if (result.compressionStats && typeof result.compressionStats === 'object') {
            compressionRatio = result.compressionStats.compressionRatio || 0;
          } else {
            // Calculate ratio if stats not provided
            compressionRatio = Math.max(0, Math.round((1 - (compressedSize / fileSize.original)) * 100));
          }
        } else {
          // Invalid result structure, use the result as is if it's a Blob
          console.error('Invalid compression result structure:', result);
          if (!(result instanceof Blob)) {
            throw new Error('Invalid compression result format');
          }
          pdfData = result;
          compressedSize = result.size;
          compressionRatio = 0;
        }
      } else {
        console.error('Unexpected compression result type:', typeof result);
        throw new Error('Unexpected compression result type');
      }
      
      // Create URL for the compressed PDF
      const url = window.URL.createObjectURL(pdfData);
      setCompressedFileUrl(url);
      
      // Update component state
      setProcessing(false);
      setProcessingComplete(true);
      setStep(3);
      
      // Store compressed file size
      setFileSize(prev => ({
        ...prev,
        compressed: compressedSize
      }));
      
      // Store compression ratio in the ref for component-wide access
      compressionRatioRef.current = compressionRatio;
      
      // Format level name
      const selectedLevelLabel = 
        selectedLevel === 'maximum' ? 'maximum' :
        selectedLevel === 'high' ? 'high' :
        selectedLevel === 'medium' ? 'medium' : 'low';
      
      // Format the ratio with one decimal place
      const formattedRatio = Number(compressionRatio).toFixed(1);
      
      // Customize message based on ratio
      let message = '';
      if (compressionRatio <= 0) {
        message = `File processed with ${selectedLevelLabel} settings`;
      } else if (compressionRatio < 20) {
        message = `File compressed by ${formattedRatio}%`;
      } else if (compressionRatio < 50) {
        message = `File compressed by ${formattedRatio}%`;
      } else {
        message = `Great result! File compressed by ${formattedRatio}%`;
      }
      
      // Show success message
      toast({
        title: "Compression Complete!",
        description: `${message} using ${selectedLevelLabel} compression`,
        duration: 5000,
      });
    },
    onError: (error: Error) => {
      setProcessing(false);
      toast({
        title: "Error",
        description: error.message || "An error occurred while compressing your PDF file.",
        variant: "destructive",
        duration: 5000,
      });
    }
  });
  
  // Clean up URL objects when component unmounts
  useEffect(() => {
    return () => {
      if (compressedFileUrl) {
        URL.revokeObjectURL(compressedFileUrl);
      }
    };
  }, [compressedFileUrl]);
  
  // Constants
  const MAX_FILE_SIZE = 15 * 1024 * 1024; // 15MB in bytes
  
  // Handle file uploads
  const handleFilesSelected = (selectedFiles: File[]) => {
    // Only take the first file for compression
    if (selectedFiles.length > 0) {
      const file = selectedFiles[0];
      
      // Check file size limit
      if (file.size > MAX_FILE_SIZE) {
        toast({
          title: "File too large",
          description: "Maximum file size is 15MB. Please select a smaller file or upgrade to premium.",
          variant: "destructive",
          duration: 5000,
        });
        return;
      }
      
      setFiles([file]);
      
      // Store original file size
      setFileSize({
        original: file.size,
        compressed: null
      });
      
      setStep(2);
    }
  };
  
  // Handle compression level selection and start compression
  const handleCompress = async () => {
    if (files.length === 0) {
      toast({
        title: "No file selected",
        description: "Please upload a PDF file to compress.",
        variant: "destructive",
      });
      return;
    }
    
    setProcessing(true);
    
    try {
      // Ensure the compression level is properly passed
      console.log(`Frontend sending compression level: ${selectedLevel}`);
      
      // Call the compressPdf method with the file and selected compression level
      await compressPdf(files[0], { 
        imageCompression: selectedLevel 
      });
    } catch (err) {
      // Error handling is done by the usePdfOperations hook
      console.error("Compression failed:", err);
    }
  };
  
  // Reset the form to start over
  const handleReset = () => {
    // Clean up the URL object to avoid memory leaks
    if (compressedFileUrl) {
      URL.revokeObjectURL(compressedFileUrl);
    }
    
    setFiles([]);
    setSelectedLevel("medium");
    setStep(1);
    setCompressedFileUrl(null);
    setProcessingComplete(false);
    setProcessing(false);
    setFileSize({
      original: 0,
      compressed: null
    });
  };
  
  // Get compressed file name
  const getCompressedFileName = () => {
    if (!files.length) return "compressed.pdf";
    
    const originalName = files[0].name;
    const nameParts = originalName.split('.');
    
    // Remove the extension
    nameParts.pop();
    
    // Add 'compressed' suffix and pdf extension
    return `${nameParts.join('.')}_compressed.pdf`;
  };
  
  // Format file size to human-readable format
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };
  
  // Render premium upgrade notice
  const renderPremiumUpgradeNotice = () => (
    <div className="mt-8 p-6 border border-amber-200 bg-amber-50 rounded-lg max-w-md mx-auto">
      <h3 className="font-medium text-lg mb-2">Need to compress larger files?</h3>
      <p className="text-sm text-muted-foreground mb-4">
        Upgrade to our premium plan to compress files up to 100MB and access advanced compression features.
      </p>
      <Link
        to="/pricing"
        className="bg-primary hover:bg-primary/90 text-white px-4 py-2 rounded-md font-medium shadow-sm inline-flex items-center justify-center text-sm"
      >
        View Premium Plans
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="ml-1.5">
          <path d="M5 12h14"></path>
          <path d="m12 5 7 7-7 7"></path>
        </svg>
      </Link>
    </div>
  );
  
  // Render compression level selection
  const renderCompressionLevels = () => (
    <div className="space-y-4 max-w-2xl mx-auto">
      <h3 className="font-medium text-lg mb-4">Select Compression Level</h3>
      
      <div className="grid gap-4">
        {compressionLevels.map((level) => (
          <div 
            key={level.id}
            className={`p-4 rounded-lg cursor-pointer border-2 hover:bg-secondary/20 transition-colors
              ${selectedLevel === level.id ? 'border-primary bg-primary/5' : 'border-border'}`}
            onClick={() => setSelectedLevel(level.id)}
          >
            <div className="flex items-center gap-3">
              <div className="text-2xl">{level.icon}</div>
              <div>
                <h4 className="font-medium">{level.name}</h4>
                <p className="text-sm text-muted-foreground">{level.description}</p>
                <p className="text-xs text-muted-foreground mt-1">Expected reduction: {level.expectedReduction}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
      
      <div className="mt-8 flex items-center justify-center">
        <ProcessingButton 
          isProcessing={processing}
          text="Compress PDF"
          onClick={handleCompress}
          disabled={isLoading || processing}
        />
      </div>
    </div>
  );
  
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
              maxSize={15} // Set the max size to 15MB to match our limit
            />
            <div className="mt-4 text-center text-sm text-muted-foreground">
              <p>Maximum file size: <span className="font-medium">15MB</span></p>
              <p className="text-xs mt-1">Need to compress larger files? <a href="/pricing" className="text-primary hover:underline">Upgrade to premium</a></p>
            </div>
          </div>
        );
      case 2:
        return renderCompressionLevels();
      case 3:
        return (
          <OperationComplete 
            fileName={getCompressedFileName()}
            fileType="Compressed PDF"
            fileUrl={compressedFileUrl}
            onReset={handleReset}
            additionalInfo={
              fileSize.compressed ? (
                <div className="text-center mt-4 p-4 bg-secondary/30 rounded-lg">
                  <p className="text-sm font-medium">
                    File size reduced by {Number(compressionRatioRef.current).toFixed(1)}%
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Original: {formatFileSize(fileSize.original)} → 
                    Compressed: {formatFileSize(fileSize.compressed)}
                  </p>
                </div>
              ) : null
            }
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
              title={tool.title || "Compress PDF"}
              description={tool.description || "Reduce PDF file size while maintaining quality"}
              icon={tool.icon}
              color={tool.color || "text-red-600"}
              bgColor={tool.bgColor || "bg-red-100"}
            />
            
            <StepProgress
              steps={tool.steps || [
                "Upload your PDF file",
                "Select compression level", 
                "Download compressed PDF"
              ]}
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

export default CompressPDF;
