import { useState } from 'react';
import { 
  mergePdfs, 
  splitPdf, 
  compressPdf, 
  convertPdfToDocx, 
  rotatePdf, 
  addPageNumbers, 
  addWatermark, 
  convertPdfToImage,
  convertPdfPageToImage,
  downloadFile 
} from '@/services/api';

interface UsePdfOperationsOptions {
  onSuccess?: (data: Blob, filename: string) => void;
  onError?: (error: Error) => void;
}

export const usePdfOperations = (options?: UsePdfOperationsOptions) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const handleMergePdfs = async (files: File[], mergeOptions?: any) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await mergePdfs(files, mergeOptions);
      
      // Create a download if onSuccess not provided
      if (options?.onSuccess) {
        options.onSuccess(result, 'merged.pdf');
      } else {
        // Default download behavior
        downloadFile(result, 'merged.pdf');
      }
      
      setIsLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to merge PDFs');
      setError(error);
      options?.onError?.(error);
      setIsLoading(false);
      throw error;
    }
  };
  
  const handleSplitPdf = async (file: File, splitOptions?: any) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await splitPdf(file, splitOptions);
      
      // Determine if result is a zip file or a single PDF
      const isZip = result.type === 'application/zip' || 
                    (result as any).filename?.toLowerCase?.().endsWith('.zip');
      
      // Prefer server-provided filename when available
      const serverFilename = (result as any).filename as string | undefined;
      const filename = serverFilename
        ? serverFilename
        : (isZip ? 'split-files.zip' : 'split.pdf');
      
      if (options?.onSuccess) {
        options.onSuccess(result, filename);
      } else {
        // Default download behavior
        downloadFile(result, filename);
      }
      
      setIsLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to split PDF');
      setError(error);
      options?.onError?.(error);
      setIsLoading(false);
      throw error;
    }
  };
  
  // Utility method to get a friendly error message from error object
  const getFriendlyErrorMessage = (error: any): string => {
    if (error?.response?.data?.message) {
      return error.response.data.message;
    } else if (error?.message) {
      return error.message;
    } else {
      return 'An unknown error occurred';
    }
  };

  // Reset error state
  const resetError = () => {
    setError(null);
  };

  const handleCompressPdf = async (file: File, compressionOptions?: any) => {
    setIsLoading(true);
    setError(null);
    
    try {
      // This now returns {file: Blob, compressionStats: {...}}
      const result = await compressPdf(file, compressionOptions);
      
      console.log('Compression result:', result);
      console.log('Compression stats:', result.compressionStats);
      
      // Generate a filename
      const originalName = file.name;
      const nameParts = originalName.split('.');
      nameParts.pop(); // Remove extension
      const filename = `${nameParts.join('.')}_compressed.pdf`;
      
      // Handle the success callback
      if (options?.onSuccess) {
        // Pass the Blob to onSuccess, not the wrapper object
        options.onSuccess(result.file, filename);
      } else {
        // Default download behavior
        downloadFile(result.file, filename);
      }
      
      setIsLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to compress PDF');
      setError(error);
      options?.onError?.(error);
      setIsLoading(false);
      throw error;
    }
  };

  const handleConvertPdfToDocx = async (file: File, conversionOptions?: any) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await convertPdfToDocx(file, conversionOptions);
      
      // Generate a filename
      const originalName = file.name;
      const nameParts = originalName.split('.');
      nameParts.pop(); // Remove extension
      const filename = `${nameParts.join('.')}.docx`;
      
      // Handle the success callback
      if (options?.onSuccess) {
        options.onSuccess(result, filename);
      } else {
        // Default download behavior
        downloadFile(result, filename);
      }
      
      setIsLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to convert PDF to DOCX');
      setError(error);
      options?.onError?.(error);
      setIsLoading(false);
      throw error;
    }
  };

  const handleRotatePdf = async (file: File, rotations: {page: number; degrees: number}[]) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await rotatePdf(file, rotations);
      
      // Generate a filename
      const originalName = file.name;
      const nameParts = originalName.split('.');
      nameParts.pop(); // Remove extension
      const filename = `${nameParts.join('.')}_rotated.pdf`;
      
      // Handle the success callback
      if (options?.onSuccess) {
        options.onSuccess(result, filename);
      } else {
        // Default download behavior
        downloadFile(result, filename);
      }
      
      setIsLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to rotate PDF pages');
      setError(error);
      options?.onError?.(error);
      setIsLoading(false);
      throw error;
    }
  };

  const handleAddPageNumbers = async (file: File, numberingOptions: any) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await addPageNumbers(file, numberingOptions);
      
      // Generate a filename
      const originalName = file.name;
      const nameParts = originalName.split('.');
      nameParts.pop(); // Remove extension
      const filename = `${nameParts.join('.')}_numbered.pdf`;
      
      // Handle the success callback
      if (options?.onSuccess) {
        options.onSuccess(result, filename);
      } else {
        // Default download behavior
        downloadFile(result, filename);
      }
      
      setIsLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to add page numbers');
      setError(error);
      options?.onError?.(error);
      setIsLoading(false);
      throw error;
    }
  };

  const handleAddWatermark = async (file: File, watermarkOptions: any) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await addWatermark(file, watermarkOptions);
      
      // Generate a filename
      const originalName = file.name;
      const nameParts = originalName.split('.');
      nameParts.pop(); // Remove extension
      const filename = `${nameParts.join('.')}_watermarked.pdf`;
      
      // Handle the success callback
      if (options?.onSuccess) {
        options.onSuccess(result, filename);
      } else {
        // Default download behavior
        downloadFile(result, filename);
      }
      
      setIsLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to add watermark');
      setError(error);
      options?.onError?.(error);
      setIsLoading(false);
      throw error;
    }
  };

  const handleConvertPdfToImage = async (file: File, conversionOptions?: any) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await convertPdfToImage(file, conversionOptions);
      
      // Generate a filename
      const originalName = file.name;
      const nameParts = originalName.split('.');
      nameParts.pop(); // Remove extension
      const format = conversionOptions?.format || 'jpg';
      const filename = `${nameParts.join('.')}_images.zip`;
      
      // Handle the success callback
      if (options?.onSuccess) {
        options.onSuccess(result.file, filename);
      } else {
        // Default download behavior
        downloadFile(result.file, filename);
      }
      
      setIsLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to convert PDF to images');
      setError(error);
      options?.onError?.(error);
      setIsLoading(false);
      throw error;
    }
  };

  const handleConvertPdfPageToImage = async (file: File, pageNumber: number, conversionOptions?: any) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await convertPdfPageToImage(file, pageNumber, conversionOptions);
      
      // Generate a filename
      const originalName = file.name;
      const nameParts = originalName.split('.');
      nameParts.pop(); // Remove extension
      const format = conversionOptions?.format || 'jpg';
      const filename = `${nameParts.join('.')}_page_${pageNumber}.${format}`;
      
      // Handle the success callback
      if (options?.onSuccess) {
        options.onSuccess(result, filename);
      } else {
        // Default download behavior
        downloadFile(result, filename);
      }
      
      setIsLoading(false);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to convert PDF page to image');
      setError(error);
      options?.onError?.(error);
      setIsLoading(false);
      throw error;
    }
  };

  return {
    mergePdfs: handleMergePdfs,
    splitPdf: handleSplitPdf,
    compressPdf: handleCompressPdf,
    convertPdfToDocx: handleConvertPdfToDocx,
    rotatePdf: handleRotatePdf,
    addPageNumbers: handleAddPageNumbers,
    addWatermark: handleAddWatermark,
    convertPdfToImage: handleConvertPdfToImage,
    convertPdfPageToImage: handleConvertPdfPageToImage,
    isLoading,
    error,
    resetError,
    getFriendlyErrorMessage,
  };
};

export default usePdfOperations;