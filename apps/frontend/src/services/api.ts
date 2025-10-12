const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const createPdfBlob = (label: string) =>
  new Blob([`%PDF-1.4\n% Dummy PDF generated for ${label}\n`], {
    type: 'application/pdf',
  });

const createZipBlob = (label: string) =>
  new Blob([`Dummy ZIP archive for ${label}`], {
    type: 'application/zip',
  });

const createDocxBlob = (label: string) =>
  new Blob([`Dummy DOCX document for ${label}`], {
    type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  });

const createImageBlob = (label: string, format: string = 'png') =>
  new Blob([`Dummy image data for ${label}`], {
    type: `image/${format}`,
  });

// PDF merge operations
export const mergePdfs = async (files: File[], options?: any) => {
  if (!files || files.length < 2) {
    throw new Error('At least two PDF files are required for merging');
  }

  await delay(800);
  return createPdfBlob('merged.pdf');
};

// PDF split operations
export const splitPdf = async (file: File, options?: any) => {
  if (!file) {
    throw new Error('A PDF file is required for splitting');
  }

  await delay(600);
  const result = options?.outputFormat === 'zip' ? createZipBlob('split files') : createPdfBlob('split.pdf');
  (result as any).filename = options?.outputFormat === 'zip' ? 'split-files.zip' : 'split.pdf';
  return result;
};

// Get PDF info (metadata, page count, etc.)
export const getPdfInfo = async (file: File) => {
  if (!file) {
    throw new Error('A PDF file is required');
  }

  await delay(300);
  return {
    filename: file.name,
    pageCount: 5,
    fileSize: file.size,
    title: 'Sample PDF',
    author: 'Frontend Preview',
  };
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

// PDF compression operations - mocked
export const compressPdf = async (file: File, options?: any) => {
  if (!file) {
    throw new Error('A PDF file is required for compression');
  }

  await delay(900);
  const compressedSize = Math.max(1, Math.floor(file.size * 0.6));
  return {
    file: createPdfBlob('compressed.pdf'),
    compressionStats: {
      compressionRatio: file.size ? Math.round((1 - compressedSize / file.size) * 100) : 40,
      originalSize: file.size,
      compressedSize,
    },
  };
};

// PDF rotation operations
export const rotatePdf = async (file: File, rotations: { page: number; degrees: number }[]) => {
  if (!file) {
    throw new Error('A PDF file is required for rotation');
  }

  if (!rotations || rotations.length === 0) {
    throw new Error('At least one rotation instruction is required');
  }

  await delay(500);
  return createPdfBlob('rotated.pdf');
};

// PDF protection operations
export const protectPdf = async (file: File, options: any) => {
  if (!file) {
    throw new Error('A PDF file is required for protection');
  }

  if (!options?.userPassword) {
    throw new Error('A user password is required to protect the PDF');
  }

  await delay(700);
  return createPdfBlob('protected.pdf');
};

export const removeProtection = async (file: File, password: string) => {
  if (!file) {
    throw new Error('A PDF file is required');
  }

  if (!password) {
    throw new Error('A password is required to remove protection');
  }

  await delay(700);
  return createPdfBlob('unprotected.pdf');
};

export const checkPdfProtection = async (file: File) => {
  if (!file) {
    throw new Error('A PDF file is required');
  }

  await delay(400);
  return {
    isEncrypted: false,
    encryptionLevel: 'None',
  };
};

// PDF to DOCX conversion operations
export const convertPdfToDocx = async (file: File, options?: any) => {
  if (!file) {
    throw new Error('A PDF file is required for conversion');
  }

  await delay(800);
  return createDocxBlob('converted.docx');
};

// PDF page numbering operations
export const addPageNumbers = async (file: File, options: any) => {
  if (!file) {
    throw new Error('A PDF file is required for adding page numbers');
  }

  await delay(650);
  return createPdfBlob('numbered.pdf');
};

// PDF watermark operations
export const addWatermark = async (file: File, options: any) => {
  if (!file) {
    throw new Error('A PDF file is required for adding a watermark');
  }

  if (!options?.type) {
    throw new Error('Watermark type is required');
  }

  await delay(650);
  return createPdfBlob('watermarked.pdf');
};

// PDF to image conversion operations
export const convertPdfToImage = async (file: File, options?: any) => {
  if (!file) {
    throw new Error('A PDF file is required for conversion');
  }

  await delay(900);
  return {
    file: createZipBlob('pdf-images.zip'),
    pageCount: 3,
  };
};

// Convert a single PDF page to an image
export const convertPdfPageToImage = async (file: File, pageNumber: number, options?: any) => {
  if (!file) {
    throw new Error('A PDF file is required for conversion');
  }

  if (!pageNumber || pageNumber < 1) {
    throw new Error('A valid page number is required');
  }

  await delay(500);
  const format = options?.format?.toLowerCase?.() || 'png';
  return createImageBlob('single-page-image', format);
};
