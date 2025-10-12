import React, { useState, useEffect } from "react";
import Layout from "@/components/Layout";
import FileUpload from "@/components/FileUpload";
import { useToast } from "@/hooks/use-toast";
import usePdfOperations from "@/hooks/use-pdf-operations";
import { getToolById } from "@/constants/toolData";
import ToolHeader from "@/components/pdf-tools/ToolHeader";
import StepProgress from "@/components/pdf-tools/StepProgress";
import PDFFileList from "@/components/pdf-tools/PDFFileList";
import ProcessingButton from "@/components/pdf-tools/ProcessingButton";
import OperationComplete from "@/components/pdf-tools/OperationComplete";



const MergePDF: React.FC = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [fileOrder, setFileOrder] = useState<number[]>([]);
  const [step, setStep] = useState(1);
  const [mergedPdfUrl, setMergedPdfUrl] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [processingComplete, setProcessingComplete] = useState(false);

  
  // Get the tool data
  const tool = getToolById("merge-pdf");
  const { toast } = useToast();



  // Initialize PDF operations
  const { mergePdfs, isLoading, error, getFriendlyErrorMessage } = usePdfOperations({
    onSuccess: async (data: Blob, filename: string) => {
      setProcessing(false);
      setProcessingComplete(true);

      // Try File System Access API for native save dialog
      if (typeof window.showSaveFilePicker === "function") {
        try {
          const fileHandle = await window.showSaveFilePicker({
            suggestedName: filename || "merged.pdf",
            types: [
              {
                description: "PDF Document",
                accept: { "application/pdf": [".pdf"] },
              },
            ],
          });
          const writable = await fileHandle.createWritable();
          await writable.write(data);
          await writable.close();
          toast({
            title: "Success!",
            description: "Your merged PDF has been saved.",
            duration: 5000,
          });
          setStep(1); // Reset to step 1 after save
          return;
        } catch (e) {
          // If user cancels, fall back to download link
        }
      }
      // Fallback for unsupported browsers or if user cancels
      const url = window.URL.createObjectURL(new Blob([data]));
      setMergedPdfUrl(url);
      setStep(3);
      toast({
        title: "Success!",
        description: "Your merged PDF is ready for download.",
        duration: 5000,
      });
    },
    onError: (error: Error) => {
      setProcessing(false);
      toast({
        title: "Error",
        description: error.message || "An error occurred while merging your PDF files.",
        variant: "destructive",
        duration: 5000,
      });
    }
  });
  
  // Clean up URL objects when component unmounts
  useEffect(() => {
    return () => {
      if (mergedPdfUrl) {
        URL.revokeObjectURL(mergedPdfUrl);
      }
    };
  }, [mergedPdfUrl]);
  
  // Handle file uploads
  const handleFilesSelected = (selectedFiles: File[]) => {
    setFiles(selectedFiles);
    
    // Initialize file order with sequential indices
    setFileOrder(selectedFiles.map((_, index) => index));
    
    if (selectedFiles.length > 0 && step === 1) {
      setStep(2);
    }
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
  
  // Handle the merge process
  const handleMergeFiles = async () => {
    setProcessing(true);
    
    // Reset any previous errors
    setMergedPdfUrl(null);
    
    try {
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
        addBookmarks: true
      };
      
      await mergePdfs(orderedFiles, options);
    } catch (err) {
      // Show error toast
      toast({
        title: "Error",
        description: error ? getFriendlyErrorMessage(error) : "An error occurred while merging your PDF files.",
        variant: "destructive",
        duration: 5000,
      });
      console.error("Error merging PDFs:", err);
    }
  };
  
  // Reset the form to start over
  const handleReset = () => {
    // Clean up the URL object to avoid memory leaks
    if (mergedPdfUrl) {
      URL.revokeObjectURL(mergedPdfUrl);
    }
    setFiles([]);
    setFileOrder([]);
    setStep(1);
    setMergedPdfUrl(null);
    setProcessingComplete(false);
    setProcessing(false);
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
              multiple={true}
            />
          </div>
        );
      case 2:
        return (
          <div className="max-w-xl mx-auto w-full animate-fade-in animate-once">
            <h3 className="text-lg font-medium mb-4">Arrange PDF Order</h3>
            <PDFFileList 
              files={files}
              fileOrder={fileOrder}
              onMoveFile={moveFile}
            />
            <ProcessingButton 
              onClick={handleMergeFiles}
              isProcessing={processing}
              disabled={files.length < 2}
              text="Merge Files"
            />
          </div>
        );
      case 3:
        return (
          <OperationComplete 
            fileName="merged.pdf"
            fileType="PDF Document"
            fileUrl={mergedPdfUrl}
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

export default MergePDF;
