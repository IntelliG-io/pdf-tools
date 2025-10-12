const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const API_BASE_URL = (import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '');

const buildApiUrl = (path: string) =>
  `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;

const createPdfBlob = (label: string) =>
  new Blob([`%PDF-1.4\n% Dummy PDF generated for ${label}\n`], {
    type: 'application/pdf',
  });

const createDocxBlob = (label: string) =>
  new Blob([`Dummy DOCX document for ${label}`], {
    type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  });

const createZipBlob = (label: string) =>
  new Blob([`Dummy ZIP archive for ${label}`], {
    type: 'application/zip',
  });

const createImageBlob = (label: string, format: string = 'png') =>
  new Blob([`Dummy image data for ${label}`], {
    type: `image/${format}`,
  });

const extractFilename = (header: string | null): string | undefined => {
  if (!header) {
    return undefined;
  }

  const starMatch = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (starMatch?.[1]) {
    try {
      return decodeURIComponent(starMatch[1]);
    } catch (_error) {
      return starMatch[1];
    }
  }

  const regularMatch = header.match(/filename="?([^";]+)"?/i);
  return regularMatch?.[1];
};

const parseErrorResponse = async (response: Response): Promise<Error> => {
  const contentType = response.headers.get('content-type') ?? '';
  let message = `Request failed with status ${response.status}`;

  try {
    if (contentType.includes('application/json')) {
      const payload = await response.json();
      if (typeof payload === 'string') {
        message = payload;
      } else if (payload?.detail) {
        message = typeof payload.detail === 'string'
          ? payload.detail
          : JSON.stringify(payload.detail);
      } else if (payload?.message) {
        message = String(payload.message);
      }
    } else {
      const text = await response.text();
      if (text.trim()) {
        message = text.trim();
      }
    }
  } catch (_error) {
    // Ignore parsing failures and keep the default message
  }

  return new Error(message);
};

const requestBinary = async (path: string, formData: FormData): Promise<Blob> => {
  const response = await fetch(buildApiUrl(path), {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  const blob = await response.blob();
  const filename = extractFilename(response.headers.get('content-disposition'));
  if (filename) {
    (blob as any).filename = filename;
  }

  return blob;
};

// PDF merge operations
export const mergePdfs = async (files: File[], _options?: any) => {
  if (!files || files.length < 2) {
    throw new Error('At least two PDF files are required for merging');
  }

  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));

  const result = await requestBinary('/merge', formData);
  if (!(result as any).filename) {
    (result as any).filename = 'merged.pdf';
  }

  return result;
};

const serialiseRanges = (ranges: Array<{ start: number; end: number }>): string =>
  ranges
    .map(({ start, end }) => (start === end ? `${start}` : `${start}-${end}`))
    .join(',');

const serialisePages = (pages: Array<number>): string => pages.join(',');

// PDF split operations
export const splitPdf = async (file: File, options?: any) => {
  if (!file) {
    throw new Error('A PDF file is required for splitting');
  }

  const mode = options?.mode ?? 'ranges';
  const formData = new FormData();
  formData.append('file', file);

  switch (mode) {
    case 'ranges': {
      const ranges = options?.ranges ?? [];
      if (!Array.isArray(ranges) || ranges.length === 0) {
        throw new Error('Please provide at least one page range to extract.');
      }
      formData.append('ranges', serialiseRanges(ranges));
      const result = await requestBinary('/split/ranges', formData);
      if (!(result as any).filename) {
        (result as any).filename = 'extracted_ranges.pdf';
      }
      return result;
    }
    case 'pages': {
      const pages = options?.pages ?? [];
      if (!Array.isArray(pages) || pages.length === 0) {
        throw new Error('Please provide at least one page number to split at.');
      }
      formData.append('pages', serialisePages(pages));
      const result = await requestBinary('/split/pages', formData);
      if (!(result as any).filename) {
        (result as any).filename = 'split_pages.zip';
      }
      return result;
    }
    case 'everyNPages': {
      const chunkSize = options?.everyNPages ?? options?.chunkSize;
      if (!chunkSize || Number(chunkSize) < 1) {
        throw new Error('Chunk size must be a positive integer.');
      }
      formData.append('chunk_size', String(chunkSize));
      const result = await requestBinary('/split/every-n', formData);
      if (!(result as any).filename) {
        (result as any).filename = `split_every_${chunkSize}.zip`;
      }
      return result;
    }
    case 'all': {
      const result = await requestBinary('/split/all-pages', formData);
      if (!(result as any).filename) {
        (result as any).filename = 'all_pages.zip';
      }
      return result;
    }
    default:
      throw new Error(`Unsupported split mode: ${mode}`);
  }
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
