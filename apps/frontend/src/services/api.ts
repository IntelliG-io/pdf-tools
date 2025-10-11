import axios from 'axios';

// Create axios instance with default config
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',  // Default to '/api' so Nginx proxy works in production
  timeout: 120000, // Increased timeout to 2 minutes for long-running file operations
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response || error.message);
    return Promise.reject(error);
  }
);

// PDF merge operations
export const mergePdfs = async (files: File[], options?: any) => {
  // Validate inputs
  if (!files || files.length < 2) {
    throw new Error('At least two PDF files are required for merging');
  }
  
  // Validate that all files are PDFs
  const nonPdfFiles = files.filter(file => !file.name.toLowerCase().endsWith('.pdf'));
  if (nonPdfFiles.length > 0) {
    throw new Error(`The following files are not PDFs: ${nonPdfFiles.map(f => f.name).join(', ')}`);
  }
  
  const formData = new FormData();
  
  // Add files to formData
  files.forEach((file) => {
    formData.append('files', file);
  });
  
  // Add options if provided
  if (options) {
    formData.append('options', JSON.stringify(options));
  }
  
  try {
    const response = await api.post('/pdf/merge', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'blob', // Important for file download
    });
    
    // Verify the response is a valid PDF
    if (response.headers['content-type'] !== 'application/pdf' && 
        !response.headers['content-disposition']?.includes('.pdf')) {
      // If response is not a PDF, it might be an error message in JSON format
      // Convert blob to text to see if it contains an error message
      try {
        const errorText = await response.data.text();
        try {
          const errorJson = JSON.parse(errorText);
          throw new Error(errorJson.message || 'Error merging PDFs');
        } catch (e) {
          // Not valid JSON, might be another format
          throw new Error(errorText || 'Error merging PDFs');
        }
      } catch (e) {
        // If we can't parse as text, just return the blob
        console.warn('Unexpected response type, but continuing anyway');
      }
    }
    
    return response.data;
  } catch (error) {
    console.error('Error merging PDFs:', error);
    throw error;
  }
};

// PDF split operations
export const splitPdf = async (file: File, options?: any) => {
  // Validate input
  if (!file) {
    throw new Error('A PDF file is required for splitting');
  }
  
  // Validate file is a PDF
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    throw new Error(`The file "${file.name}" is not a PDF`);
  }
  
  const formData = new FormData();
  formData.append('file', file);
  
  if (options) {
    formData.append('options', JSON.stringify(options));
  }
  
  // Check if we need to use the advanced endpoint
  const useAdvanced = options && (
    options.mode === 'pages' ||
    options.mode === 'everyNPages' ||
    options.mode === 'bookmarks' ||
    options.mode === 'all' ||
    options.mode === 'ranges' ||
    options.filenamePrefix ||
    options.preserveBookmarks
  );
  
  // Decide when to request ZIP download
  const wantZip = Boolean(
    (options && options.outputFormat === 'zip') ||
    (options && (
      options.mode === 'all' ||
      options.mode === 'pages' ||
      options.mode === 'everyNPages' ||
      options.mode === 'bookmarks' ||
      (options.mode === 'ranges' && Array.isArray(options.ranges) && options.ranges.length > 1)
    ))
  );
  
  try {
    // Construct URL with any query parameters
    const endpoint = useAdvanced ? '/pdf/split/advanced' : '/pdf/split';
    const queryParams = wantZip ? '?download=zip' : '';
    
    const response = await api.post(`${endpoint}${queryParams}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'blob',
    });
    
    // Check response content type to determine if it's PDF, ZIP, or an error
    const contentType = response.headers['content-type']?.toLowerCase();
    const isZip = contentType === 'application/zip' || 
                  response.headers['content-disposition']?.includes('.zip');
    const isPdf = contentType === 'application/pdf' ||
                  response.headers['content-disposition']?.includes('.pdf');
                  
    if (!isPdf && !isZip) {
      try {
        const errorText = await response.data.text();
        try {
          const errorJson = JSON.parse(errorText);
          throw new Error(errorJson.message || 'Error splitting PDF');
        } catch (e) {
          throw new Error(errorText || 'Error splitting PDF');
        }
      } catch (e) {
        // If the blob isn't text/JSON, still surface an error to avoid corrupt downloads
        throw new Error('Unexpected response type from server while splitting PDF');
      }
    }
    
    // Try to extract filename from Content-Disposition
    const contentDisposition = response.headers['content-disposition'] as string | undefined;
    let serverFilename: string | undefined;
    if (contentDisposition) {
      const match = /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i.exec(contentDisposition);
      serverFilename = decodeURIComponent((match?.[1] || match?.[2] || '').trim());
    }

    // Return the blob data with an appropriate filename
    if (isZip) {
      // For ZIP files, set the correct filename
      const result = response.data;
      result.filename = serverFilename && serverFilename.toLowerCase().endsWith('.zip')
        ? serverFilename
        : (serverFilename || 'split-files.zip');
      return result;
    }
    
    // For single PDF response
    const pdfResult = response.data;
    if (serverFilename && serverFilename.toLowerCase().endsWith('.pdf')) {
      (pdfResult as any).filename = serverFilename;
    } else {
      (pdfResult as any).filename = serverFilename || 'split.pdf';
    }
    return pdfResult;
  } catch (error) {
    // Try to extract a useful error message from Blob responses
    if (axios.isAxiosError(error) && error.response && error.response.data instanceof Blob) {
      try {
        const text = await (error.response.data as Blob).text();
        try {
          const json = JSON.parse(text);
          const message = json.message || 'Error splitting PDF';
          console.error('Error splitting PDF:', message);
          throw new Error(message);
        } catch {
          console.error('Error splitting PDF:', text);
          throw new Error(text || 'Error splitting PDF');
        }
      } catch (e) {
        console.error('Error splitting PDF (unreadable response):', e);
        throw new Error('Error splitting PDF');
      }
    }
    console.error('Error splitting PDF:', error);
    throw error as any;
  }
};

// Get PDF info (metadata, page count, etc.)
export const getPdfInfo = async (file: File) => {
  // Validate input
  if (!file) {
    throw new Error('A PDF file is required');
  }
  
  // Validate file is a PDF
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    throw new Error(`The file "${file.name}" is not a PDF`);
  }
  
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    const response = await api.post('/pdf/info', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  } catch (error) {
    console.error('Error getting PDF info:', error);
    throw error;
  }
};

// Helper function to handle file downloads
export const downloadFile = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  
  // Clean up
  link.remove();
  window.URL.revokeObjectURL(url);
};

// PDF compression operations - completely rewritten
export const compressPdf = async (file: File, options?: any) => {
  // Validate input
  if (!file) {
    throw new Error('A PDF file is required for compression');
  }
  
  // Validate file is a PDF
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    throw new Error(`The file "${file.name}" is not a PDF`);
  }
  
  // Validate file size (15MB limit)
  const MAX_FILE_SIZE = 15 * 1024 * 1024; // 15MB in bytes
  if (file.size > MAX_FILE_SIZE) {
    throw new Error(`File size exceeds the maximum limit of 15MB. Current size: ${(file.size / (1024 * 1024)).toFixed(2)}MB`);
  }
  
  // Create form data and add the file
  const formData = new FormData();
  formData.append('file', file);
  
  // Add compression options if provided
  if (options) {
    console.log('Sending options to backend:', options);
    
    // Make sure we're using imageCompression parameter not compressionLevel
    const correctedOptions = { ...options };
    if (options.compressionLevel && !options.imageCompression) {
      correctedOptions.imageCompression = options.compressionLevel;
      delete correctedOptions.compressionLevel;
    }
    
    // Add each option as a separate field
    Object.entries(correctedOptions).forEach(([key, value]) => {
      formData.append(key, String(value));
    });
  }
  
  try {
    // Get the PDF file and compression stats in one response
    const response = await api.post('/pdf/compress', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      responseType: 'blob'
    });
    
    // Verify we got a PDF back
    if (response.headers['content-type'] !== 'application/pdf') {
      throw new Error('Invalid response type from server');
    }
    
    // Get compression ratio from header
    const compressionRatio = parseFloat(response.headers['x-compression-ratio'] || '0');
    console.log(`Compression ratio from header: ${compressionRatio}%`);
    
    // Create a wrapper object that includes both the PDF and the stats
    return {
      // The actual PDF file
      file: response.data,
      
      // Stats about the compression
      compressionStats: {
        compressionRatio: compressionRatio,
        originalSize: file.size,
        compressedSize: response.data.size
      }
    };
  } catch (error) {
    console.error('PDF compression error:', error);
    throw error;
  }
};

// PDF rotation operations
export const rotatePdf = async (file: File, rotations: {page: number; degrees: number}[]) => {
  // Validate input
  if (!file) {
    throw new Error('A PDF file is required for rotation');
  }
  
  // Validate file is a PDF
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    throw new Error(`The file "${file.name}" is not a PDF`);
  }
  
  // Validate rotations array
  if (!rotations || rotations.length === 0) {
    throw new Error('At least one rotation instruction is required');
  }
  
  const formData = new FormData();
  formData.append('file', file);
  
  // Convert rotations to the format expected by the backend
  // The backend expects a JSON string in the 'rotations' field
  formData.append('rotations', JSON.stringify(rotations));
  
  // For debugging
  console.log('Sending rotations to backend:', JSON.stringify(rotations));
  
  try {
    const response = await api.post('/pdf/rotate', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'blob',
    });
    
    // Verify the response is a valid PDF
    if (response.headers['content-type'] !== 'application/pdf') {
      try {
        const errorText = await response.data.text();
        try {
          const errorJson = JSON.parse(errorText);
          throw new Error(errorJson.message || 'Error rotating PDF pages');
        } catch (e) {
          throw new Error(errorText || 'Error rotating PDF pages');
        }
      } catch (e) {
        console.warn('Unexpected response type, but continuing anyway');
      }
    }
    
    return response.data;
  } catch (error) {
    console.error('Error rotating PDF:', error);
    throw error;
  }
};

// PDF protection operations
export const protectPdf = async (file: File, options: any) => {
  // Validate input
  if (!file) {
    throw new Error('A PDF file is required for protection');
  }
  
  // Validate file is a PDF
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    throw new Error(`The file "${file.name}" is not a PDF`);
  }
  
  // Validate password exists
  if (!options.userPassword) {
    throw new Error('A user password is required to protect the PDF');
  }
  
  const formData = new FormData();
  formData.append('file', file);
  
  // Add protection options
  Object.entries(options).forEach(([key, value]) => {
    // Convert boolean values properly
    if (typeof value === 'boolean') {
      formData.append(key, value ? 'true' : 'false');
    } else {
      formData.append(key, String(value));
    }
  });
  
  try {
    const response = await api.post('/pdf/protect', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'blob',
    });
    
    // Verify the response is a valid PDF
    if (response.headers['content-type'] !== 'application/pdf') {
      try {
        const errorText = await response.data.text();
        try {
          const errorJson = JSON.parse(errorText);
          throw new Error(errorJson.message || 'Error protecting PDF');
        } catch (e) {
          throw new Error(errorText || 'Error protecting PDF');
        }
      } catch (e) {
        console.warn('Unexpected response type, but continuing anyway');
      }
    }
    
    return response.data;
  } catch (error) {
    console.error('Error protecting PDF:', error);
    throw error;
  }
};

export const removeProtection = async (file: File, password: string) => {
  // Validate input
  if (!file) {
    throw new Error('A PDF file is required');
  }
  
  // Validate file is a PDF
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    throw new Error(`The file "${file.name}" is not a PDF`);
  }
  
  // Validate password exists
  if (!password) {
    throw new Error('A password is required to remove protection');
  }
  
  const formData = new FormData();
  formData.append('file', file);
  formData.append('password', password);
  
  try {
    const response = await api.post('/pdf/protect/remove', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'blob',
    });
    
    // Verify the response is a valid PDF
    if (response.headers['content-type'] !== 'application/pdf') {
      try {
        const errorText = await response.data.text();
        try {
          const errorJson = JSON.parse(errorText);
          throw new Error(errorJson.message || 'Error removing PDF protection');
        } catch (e) {
          throw new Error(errorText || 'Error removing PDF protection');
        }
      } catch (e) {
        console.warn('Unexpected response type, but continuing anyway');
      }
    }
    
    return response.data;
  } catch (error) {
    console.error('Error removing PDF protection:', error);
    throw error;
  }
};

export const checkPdfProtection = async (file: File) => {
  // Validate input
  if (!file) {
    throw new Error('A PDF file is required');
  }
  
  // Validate file is a PDF
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    throw new Error(`The file "${file.name}" is not a PDF`);
  }
  
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    const response = await api.post('/pdf/protect/check', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  } catch (error) {
    console.error('Error checking PDF protection:', error);
    throw error;
  }
};

// PDF to DOCX conversion operations
export const convertPdfToDocx = async (file: File, options?: any) => {
  // Validate input
  if (!file) {
    throw new Error('A PDF file is required for conversion');
  }
  
  // Validate file is a PDF
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    throw new Error(`The file "${file.name}" is not a PDF`);
  }
  
  const formData = new FormData();
  formData.append('file', file);
  
  // Add options if provided
  if (options) {
    formData.append('options', JSON.stringify(options));
  }
  
  try {
    // Use the basic or advanced endpoint based on options
    const isAdvanced = options && Object.keys(options).length > 0;
    const endpoint = isAdvanced ? '/pdf/convert/to-word/advanced' : '/pdf/convert/to-word/basic';
    
    const response = await api.post(endpoint, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'blob',
    });
    
    // Log information about the response
    console.log('PDF to DOCX conversion response:', {
      status: response.status,
      contentType: response.headers['content-type'],
      contentDisposition: response.headers['content-disposition'],
      dataSize: response.data.size
    });
    
    // Verify the response content type
    if (response.headers['content-type'] !== 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' &&
        !response.headers['content-disposition']?.includes('.docx')) {
      // Try to parse error message if response is not a DOCX
      try {
        const errorText = await response.data.text();
        try {
          const errorJson = JSON.parse(errorText);
          throw new Error(errorJson.message || 'Error converting PDF to DOCX');
        } catch (e) {
          throw new Error(errorText || 'Error converting PDF to DOCX');
        }
      } catch (e) {
        console.warn('Unexpected response type, but continuing anyway');
      }
    }
    
    return response.data;
  } catch (error) {
    console.error('Error converting PDF to DOCX:', error);
    throw error;
  }
};

// PDF page numbering operations
export const addPageNumbers = async (file: File, options: any) => {
  // Validate input
  if (!file) {
    throw new Error('A PDF file is required for adding page numbers');
  }
  
  // Validate file is a PDF
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    throw new Error(`The file "${file.name}" is not a PDF`);
  }
  
  const formData = new FormData();
  formData.append('file', file);
  
  // Add numbering options
  Object.entries(options).forEach(([key, value]) => {
    if (typeof value === 'object' && value !== null) {
      formData.append(key, JSON.stringify(value));
    } else if (typeof value === 'boolean') {
      formData.append(key, value ? 'true' : 'false');
    } else if (value !== undefined && value !== null) {
      formData.append(key, String(value));
    }
  });
  
  try {
    const response = await api.post('/pdf/number-pages', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'blob',
    });
    
    // Verify the response is a valid PDF
    if (response.headers['content-type'] !== 'application/pdf') {
      try {
        const errorText = await response.data.text();
        try {
          const errorJson = JSON.parse(errorText);
          throw new Error(errorJson.message || 'Error adding page numbers');
        } catch (e) {
          throw new Error(errorText || 'Error adding page numbers');
        }
      } catch (e) {
        console.warn('Unexpected response type, but continuing anyway');
      }
    }
    
    return response.data;
  } catch (error) {
    console.error('Error adding page numbers:', error);
    throw error;
  }
};

// PDF watermark operations
export const addWatermark = async (file: File, options: any) => {
  // Validate input
  if (!file) {
    throw new Error('A PDF file is required for adding a watermark');
  }
  
  // Validate file is a PDF
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    throw new Error(`The file "${file.name}" is not a PDF`);
  }
  
  // Validate required options
  if (!options.type) {
    throw new Error('Watermark type is required');
  }
  
  if (!options.position) {
    throw new Error('Watermark position is required');
  }
  
  if (options.type === 'text' && !options.text) {
    throw new Error('Text content is required for text watermarks');
  }
  
  const formData = new FormData();
  formData.append('file', file);
  
  // Add watermark options
  Object.entries(options).forEach(([key, value]) => {
    if (typeof value === 'object' && value !== null) {
      formData.append(key, JSON.stringify(value));
    } else if (typeof value === 'boolean') {
      formData.append(key, value ? 'true' : 'false');
    } else if (value !== undefined && value !== null) {
      formData.append(key, String(value));
    }
  });
  
  try {
    const response = await api.post('/pdf/watermark', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'blob',
    });
    
    // Verify the response is a valid PDF
    if (response.headers['content-type'] !== 'application/pdf') {
      try {
        const errorText = await response.data.text();
        try {
          const errorJson = JSON.parse(errorText);
          throw new Error(errorJson.message || 'Error adding watermark');
        } catch (e) {
          throw new Error(errorText || 'Error adding watermark');
        }
      } catch (e) {
        console.warn('Unexpected response type, but continuing anyway');
      }
    }
    
    return response.data;
  } catch (error) {
    console.error('Error adding watermark:', error);
    throw error;
  }
};

// PDF to image conversion operations
export const convertPdfToImage = async (file: File, options?: any) => {
  // Validate input
  if (!file) {
    throw new Error('A PDF file is required for conversion');
  }
  
  // Validate file is a PDF
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    throw new Error(`The file "${file.name}" is not a PDF`);
  }
  
  const formData = new FormData();
  formData.append('file', file);
  
  // Add conversion options
  if (options) {
    // Handle object parameters separately
    Object.entries(options).forEach(([key, value]) => {
      if (typeof value === 'object' && value !== null) {
        formData.append(key, JSON.stringify(value));
      } else if (typeof value === 'boolean') {
        formData.append(key, value ? 'true' : 'false');
      } else if (value !== undefined && value !== null) {
        formData.append(key, String(value));
      }
    });
  }
  
  try {
    const response = await api.post('/pdf/convert/to-image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'blob',
    });
    
    // Check response content type to determine if it's a ZIP or an error
    const contentType = response.headers['content-type']?.toLowerCase();
    const isZip = contentType === 'application/zip' || 
                  response.headers['content-disposition']?.includes('.zip');
                  
    if (!isZip) {
      try {
        const errorText = await response.data.text();
        try {
          const errorJson = JSON.parse(errorText);
          throw new Error(errorJson.message || 'Error converting PDF to images');
        } catch (e) {
          throw new Error(errorText || 'Error converting PDF to images');
        }
      } catch (e) {
        console.warn('Unexpected response type, but continuing anyway');
      }
    }
    
    // Get the page count from the header
    const pageCount = parseInt(response.headers['x-page-count'] || '0', 10);
    
    // Return both the ZIP file and metadata
    return {
      file: response.data,
      pageCount,
    };
  } catch (error) {
    console.error('Error converting PDF to images:', error);
    throw error;
  }
};

// Convert a single PDF page to an image
export const convertPdfPageToImage = async (file: File, pageNumber: number, options?: any) => {
  // Validate input
  if (!file) {
    throw new Error('A PDF file is required for conversion');
  }
  
  // Validate file is a PDF
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    throw new Error(`The file "${file.name}" is not a PDF`);
  }
  
  // Validate page number
  if (!pageNumber || pageNumber < 1) {
    throw new Error('A valid page number is required');
  }
  
  const formData = new FormData();
  formData.append('file', file);
  formData.append('pageNumber', String(pageNumber));
  
  // Add conversion options
  if (options) {
    // Handle object parameters separately
    Object.entries(options).forEach(([key, value]) => {
      if (typeof value === 'object' && value !== null) {
        formData.append(key, JSON.stringify(value));
      } else if (typeof value === 'boolean') {
        formData.append(key, value ? 'true' : 'false');
      } else if (value !== undefined && value !== null) {
        formData.append(key, String(value));
      }
    });
  }
  
  try {
    const response = await api.post('/pdf/convert/to-image/single-page', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'blob',
    });
    
    // Check response content type to determine if it's an image or an error
    const contentType = response.headers['content-type']?.toLowerCase();
    const isImage = contentType?.startsWith('image/');
                  
    if (!isImage) {
      try {
        const errorText = await response.data.text();
        try {
          const errorJson = JSON.parse(errorText);
          throw new Error(errorJson.message || 'Error converting PDF page to image');
        } catch (e) {
          throw new Error(errorText || 'Error converting PDF page to image');
        }
      } catch (e) {
        console.warn('Unexpected response type, but continuing anyway');
      }
    }
    
    return response.data;
  } catch (error) {
    console.error('Error converting PDF page to image:', error);
    throw error;
  }
};

export default api;
