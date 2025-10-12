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
import PdfRotationPreview from "@/components/pdf-tools/PdfRotationPreview";
import PdfFirstPagePreview from "@/components/pdf-tools/PdfFirstPagePreview";
import PdfImageRotationPreview from "@/components/pdf-tools/PdfImageRotationPreview";
import { cn } from "@/lib/utils";
import { RotateCw, RotateCcw, HelpCircle, Plus, Trash, Image, Loader } from "lucide-react";
import { getPdfInfo } from "@/services/api";

interface PageRotation {
  page: number;
  degrees: number;
}

const RotatePDF: React.FC = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [step, setStep] = useState(1);
  const [rotatedPdfUrl, setRotatedPdfUrl] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [processingComplete, setProcessingComplete] = useState(false);
  const [rotations, setRotations] = useState<PageRotation[]>([{ page: 1, degrees: 90 }]);
  const [totalPages, setTotalPages] = useState<number>(0);
  const [pdfImages, setPdfImages] = useState<string[]>([]);
  const [isConvertingToImages, setIsConvertingToImages] = useState(false);
  
  // Get the tool data
  const tool = getToolById("rotate-pdf");
  const { toast } = useToast();
  
  // Initialize PDF operations
  const { 
    rotatePdf, 
    convertPdfToImage, 
    convertPdfPageToImage,
    isLoading, 
    error, 
    getFriendlyErrorMessage 
  } = usePdfOperations({
    onSuccess: (data: Blob, filename: string) => {
      // Create URL for the blob data
      const url = window.URL.createObjectURL(new Blob([data], { type: 'application/pdf' }));
      
      setRotatedPdfUrl(url);
      setProcessing(false);
      setProcessingComplete(true);
      setStep(3);
      
      toast({
        title: "Success!",
        description: "Your rotated PDF is ready for download.",
        duration: 5000,
      });
    },
    onError: (error: Error) => {
      setProcessing(false);
      setIsConvertingToImages(false);
      toast({
        title: "Error",
        description: error.message || "An error occurred while processing your PDF file.",
        variant: "destructive",
        duration: 5000,
      });
    }
  });
  
  // Function to convert PDF to images
  const convertPdfToImages = async (file: File) => {
    if (!file) return;
    
    setIsConvertingToImages(true);
    setPdfImages([]);
    
    try {
      // Get total pages information
      const imageOptions = {
        format: 'jpg',
        quality: 'medium'
      };
      
      // Approach: Convert each page separately to display them immediately
      const imageUrls: string[] = [];
      
      for (let i = 1; i <= totalPages; i++) {
        const imageBlob = await convertPdfPageToImage(file, i, imageOptions);
        const imageUrl = URL.createObjectURL(imageBlob);
        imageUrls.push(imageUrl);
        setPdfImages([...imageUrls]);
      }
      
      setIsConvertingToImages(false);
    } catch (error) {
      console.error("Error converting PDF to images:", error);
      setIsConvertingToImages(false);
      toast({
        title: "Error",
        description: "Failed to convert PDF to images. Please try again.",
        variant: "destructive",
        duration: 5000,
      });
    }
  };
  
  // Clean up URL objects when component unmounts
  useEffect(() => {
    return () => {
      // Clean up rotated PDF URL
      if (rotatedPdfUrl) {
        URL.revokeObjectURL(rotatedPdfUrl);
      }
      
      // Clean up all image URLs
      pdfImages.forEach(url => {
        URL.revokeObjectURL(url);
      });
    };
  }, [rotatedPdfUrl, pdfImages]);
  
  // Handle file uploads
  const handleFilesSelected = async (selectedFiles: File[]) => {
    // Only take the first file for rotation
    if (selectedFiles.length > 0) {
      const file = selectedFiles[0];
      
      // Validate file is a PDF
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        toast({
          title: "Invalid File Type",
          description: "Please select a PDF file for rotation.",
          variant: "destructive",
          duration: 5000,
        });
        return;
      }
      
      setFiles([file]);
      setPdfImages([]); // Reset previous images
      
      try {
        // Get accurate page count from the PDF info API
        const pdfInfo = await getPdfInfo(file);
        if (pdfInfo && typeof pdfInfo.pageCount === 'number') {
          setTotalPages(pdfInfo.pageCount);
          
          // After getting the page count, start converting to images
          convertPdfToImages(file);
        } else {
          // Fallback to simple estimate
          const estimatedPages = Math.max(1, Math.floor(file.size / 50000));
          setTotalPages(estimatedPages);
          
          // Start converting to images with estimated page count
          convertPdfToImages(file);
        }
      } catch (error) {
        console.error("Error getting PDF info:", error);
        // Fallback to simple estimate based on file size
        const estimatedPages = Math.max(1, Math.floor(file.size / 50000));
        setTotalPages(estimatedPages);
        
        // Start converting to images with estimated page count
        convertPdfToImages(file);
      }
      
      if (step === 1) {
        setStep(2);
      }
    }
  };
  

  
  // Add a new rotation
  const addRotation = () => {
    // Set page to a value that hasn't been used yet, or default to 1
    const usedPages = new Set(rotations.map(r => r.page));
    let newPage = 1;
    
    // Find the first unused page number
    for (let i = 1; i <= totalPages; i++) {
      if (!usedPages.has(i)) {
        newPage = i;
        break;
      }
    }
    
    const newRotation = { page: newPage, degrees: 90 };
    setRotations([...rotations, newRotation]);
  };
  
  // Remove a rotation
  const removeRotation = (index: number) => {
    const updatedRotations = [...rotations];
    updatedRotations.splice(index, 1);
    setRotations(updatedRotations);
  };
  

  
  // Update a rotation
  const updateRotation = (index: number, field: 'page' | 'degrees', value: number) => {
    const updatedRotations = [...rotations];
    
    // Ensure value is an integer for page field and is at least 1
    if (field === 'page') {
      value = Math.max(1, Math.floor(value) || 1);
    }
    
    updatedRotations[index] = { ...updatedRotations[index], [field]: value };
    setRotations(updatedRotations);
    
    // Force re-render of the rotation previews by creating a new array reference
    if (pdfImages.length > 0) {
      setPdfImages([...pdfImages]);
    }
  };
  
  // Handle the rotation process
  const handleRotatePdf = async () => {
    setProcessing(true);
    
    // Reset any previous URL
    setRotatedPdfUrl(null);
    
    try {
      if (files.length !== 1) {
        toast({
          title: "Error",
          description: "Please select exactly one PDF file to rotate.",
          variant: "destructive",
          duration: 5000,
        });
        setProcessing(false);
        return;
      }
      
      // Validate rotations
      if (rotations.length === 0) {
        toast({
          title: "Error",
          description: "Please add at least one rotation instruction.",
          variant: "destructive",
          duration: 5000,
        });
        setProcessing(false);
        return;
      }
      
      // Make sure rotations are valid
      const validatedRotations = rotations.map(rotation => ({
        page: Math.max(1, Math.min(rotation.page, totalPages || 1)),
        degrees: rotation.degrees
      }));
      
      // Check if any page numbers were corrected
      const invalidPageRotations = rotations.filter(r => r.page < 1 || r.page > totalPages);
      if (invalidPageRotations.length > 0) {
        // Let the user know their values were adjusted
        toast({
          title: "Page numbers adjusted",
          description: `Some page numbers were outside the valid range and have been adjusted to fit within the document's ${totalPages} pages.`,
          duration: 5000,
        });
        
        // Update rotations with valid values
        setRotations(validatedRotations);
      }
      
      // Check for duplicate pages (keep the last rotation for each page)
      const uniquePages = new Set();
      const duplicatePages = new Set();
      
      validatedRotations.forEach(r => {
        if (uniquePages.has(r.page)) {
          duplicatePages.add(r.page);
        }
        uniquePages.add(r.page);
      });
      
      if (duplicatePages.size > 0) {
        toast({
          title: "Duplicate pages detected",
          description: `Pages ${Array.from(duplicatePages).join(', ')} have multiple rotation instructions. Only the last rotation for each page will be applied.`,
          duration: 5000,
        });
        
        // Keep only the last rotation for each page
        const uniqueRotations = [];
        const seenPages = new Set();
        
        // Process in reverse to keep the last rotation for each page
        for (let i = validatedRotations.length - 1; i >= 0; i--) {
          const r = validatedRotations[i];
          if (!seenPages.has(r.page)) {
            uniqueRotations.unshift(r); // Add to the front to maintain order
            seenPages.add(r.page);
          }
        }
        
        // Update rotations with deduplicated values
        if (uniqueRotations.length !== validatedRotations.length) {
          setRotations(uniqueRotations);
          validatedRotations.length = 0;
          validatedRotations.push(...uniqueRotations);
        }
      }
      
      // Now proceed with the API call
      await rotatePdf(files[0], validatedRotations);
    } catch (err) {
      // Show error toast
      toast({
        title: "Error",
        description: error ? getFriendlyErrorMessage(error) : "An error occurred while rotating your PDF file.",
        variant: "destructive",
        duration: 5000,
      });
      console.error("Error rotating PDF:", err);
      setProcessing(false);
    }
  };
  
  // Reset the form to start over
  const handleReset = () => {
    // Clean up the URL object to avoid memory leaks
    if (rotatedPdfUrl) {
      URL.revokeObjectURL(rotatedPdfUrl);
    }
    
    // Clean up all image URLs
    pdfImages.forEach(url => {
      URL.revokeObjectURL(url);
    });
    
    setFiles([]);
    setRotations([{ page: 1, degrees: 90 }]);
    setStep(1);
    setRotatedPdfUrl(null);
    setProcessingComplete(false);
    setProcessing(false);
    setTotalPages(0);
    setPdfImages([]);
    setIsConvertingToImages(false);
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
          <div className="max-w-6xl mx-auto w-full animate-fade-in animate-once">
            <h3 className="text-lg font-medium mb-4">Rotate PDF Pages</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Left column: PDF Preview */}
              <div className="order-2 md:order-1">
                {/* Document Preview Section */}
                <div className="mb-6">
                  <div className="flex justify-between items-center mb-3">
                    <h3 className="text-sm font-medium">Document Preview</h3>
                    <div className="flex items-center text-xs text-muted-foreground">
                      <Image className="w-3.5 h-3.5 mr-1" />
                      <span>PDF to Image Previews</span>
                    </div>
                  </div>
                  
                  {isConvertingToImages && (
                    <div className="flex flex-col items-center justify-center py-8 border border-dashed rounded-md mb-4">
                      <Loader className="w-8 h-8 text-primary animate-spin mb-2" />
                      <p className="text-sm text-muted-foreground">Converting PDF to images...</p>
                    </div>
                  )}
                  
                  {!isConvertingToImages && pdfImages.length > 0 ? (
                    <div className="mb-4">
                      {/* Only show direct image previews if rotation previews aren't shown yet */}
                      {rotations.length === 0 ? (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                          {pdfImages.map((imageUrl, index) => (
                            <div 
                              key={`image-preview-${index}`} 
                              className="border rounded-md overflow-hidden relative group"
                            >
                              <div className="aspect-[3/4] bg-white flex items-center justify-center p-2">
                                <img 
                                  src={imageUrl} 
                                  alt={`Page ${index + 1}`} 
                                  className="object-contain h-full w-full"
                                />
                              </div>
                              <div className="absolute bottom-0 left-0 right-0 bg-background/90 text-xs py-1 px-2 text-center">
                                Page {index + 1}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <PdfImageRotationPreview
                          images={pdfImages}
                          rotations={rotations}
                        />
                      )}
                    </div>
                  ) : (
                    !isConvertingToImages && (
                      <PdfFirstPagePreview
                        file={files.length > 0 ? files[0] : null}
                        className="w-full"
                      />
                    )
                  )}
                  
                  <p className="text-xs text-muted-foreground mt-2">
                    Rotations will be applied to the pages you specify without changing the original document
                  </p>
                </div>
                
                <div className="bg-background p-4 rounded-lg mt-4 text-sm">
                  <div className="flex items-start">
                    <HelpCircle className="w-5 h-5 text-primary mr-2 flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="font-medium">Rotation Tips</h4>
                      <ul className="text-muted-foreground mt-1 space-y-1">
                        <li className="flex items-center">
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1">
                            <rect x="4" y="4" width="16" height="16" rx="2"></rect>
                          </svg>
                          0° (No Rotation): Keeps the page in its original orientation
                        </li>
                        <li className="flex items-center">
                          <RotateCw className="w-4 h-4 mr-1" /> 90° Clockwise: Rotates the page to the right
                        </li>
                        <li className="flex items-center">
                          <RotateCcw className="w-4 h-4 mr-1" /> 90° Counter-Clockwise: Rotates the page to the left
                        </li>
                        <li className="flex items-center">
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1">
                            <path d="M4 8V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-2"></path>
                            <rect width="8" height="8" x="2" y="14" rx="2"></rect>
                          </svg>
                          180° Upside Down: Flips the page upside down
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Right column: Rotation Controls */}
              <div className="order-1 md:order-2">
                <div className="border rounded-lg p-6 bg-secondary/30">
                  <div className="mb-4">
                    <p className="text-sm text-muted-foreground mb-4">
                      Specify which pages to rotate and the rotation angle for each page.
                      {totalPages > 0 && (
                        <> Your document has <strong>{totalPages}</strong> {totalPages === 1 ? 'page' : 'pages'}.</>
                      )}
                    </p>
                    
                    {rotations.map((rotation, index) => (
                      <div 
                        key={index} 
                        className={cn(
                          "flex items-center gap-3 mb-3 p-3 rounded-md border border-transparent"
                        )}
                      >
                        <div className="flex-1">
                          <label className="block text-sm font-medium mb-1">Page</label>
                          <input
                            type="number"
                            min="1"
                            max={totalPages || 999}
                            className={cn(
                              "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background",
                              "file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground",
                              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                              "disabled:cursor-not-allowed disabled:opacity-50",
                              rotation.page < 1 || rotation.page > totalPages ? "border-red-500" : ""
                            )}
                            value={rotation.page}
                            onChange={(e) => updateRotation(index, 'page', parseInt(e.target.value) || 1)}
                            onBlur={(e) => {
                              const value = parseInt(e.target.value) || 1;
                              if (value < 1) {
                                updateRotation(index, 'page', 1);
                              } else if (totalPages && value > totalPages) {
                                updateRotation(index, 'page', totalPages);
                              }
                            }}

                          />
                          {totalPages > 0 && (
                            <p className="text-xs text-muted-foreground mt-1">
                              Max: {totalPages} {totalPages === 1 ? 'page' : 'pages'}
                            </p>
                          )}
                        </div>
                        
                        <div className="flex-1">
                          <label className="block text-sm font-medium mb-1">Angle</label>
                          <div className="flex">
                            <select
                              className={cn(
                                "flex h-10 w-full rounded-l-md border border-input bg-background px-3 py-2 text-sm ring-offset-background",
                                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                                "disabled:cursor-not-allowed disabled:opacity-50"
                              )}
                              value={rotation.degrees}
                              onChange={(e) => updateRotation(index, 'degrees', parseInt(e.target.value))}
                            >
                              <option value={0}>0° (No Rotation)</option>
                              <option value={90}>90° Clockwise</option>
                              <option value={180}>180° Upside Down</option>
                              <option value={270}>90° Counter-Clockwise</option>
                            </select>
                            <div className="flex items-center justify-center h-10 w-10 bg-muted border border-l-0 border-input rounded-r-md">
                              {rotation.degrees === 0 && (
                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-muted-foreground">
                                  <rect x="4" y="4" width="16" height="16" rx="2"></rect>
                                </svg>
                              )}
                              {rotation.degrees === 90 && <RotateCw className="w-5 h-5 text-primary" />}
                              {rotation.degrees === 270 && <RotateCcw className="w-5 h-5 text-primary" />}
                              {rotation.degrees === 180 && (
                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
                                  <path d="M4 8V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-2"></path>
                                  <rect width="8" height="8" x="2" y="14" rx="2"></rect>
                                </svg>
                              )}
                            </div>
                          </div>
                        </div>
                        
                        <div className="flex-none pt-6">
                          <button 
                            type="button" 
                            className="p-2 rounded-full hover:bg-background"
                            onClick={() => removeRotation(index)}
                            disabled={rotations.length <= 1}
                          >
                            <Trash className="w-4 h-4 text-destructive" />
                          </button>
                        </div>
                      </div>
                    ))}
                    
                    <button
                      type="button"
                      onClick={addRotation}
                      className="flex items-center justify-center w-full p-2 mt-2 border border-dashed border-primary/50 rounded-md text-sm text-primary hover:bg-primary/5"
                    >
                      <Plus className="w-4 h-4 mr-1" />
                      Add Another Page to Rotate
                    </button>
                  </div>
                </div>
                
                <div className="mt-6">
                  <ProcessingButton 
                    onClick={handleRotatePdf}
                    isProcessing={processing}
                    disabled={rotations.length === 0}
                    text="Rotate PDF"
                  />
                </div>
              </div>
            </div>
          </div>
        );
      case 3:
        return (
          <OperationComplete 
            fileName={`${files[0]?.name.replace('.pdf', '')}_rotated.pdf`}
            fileType="PDF Document"
            fileUrl={rotatedPdfUrl}
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

export default RotatePDF;
