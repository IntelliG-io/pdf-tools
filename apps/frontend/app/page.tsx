'use client';

import { useState } from 'react';

type MergeResponse = {
  ok: boolean;
  message?: string;
  blob?: Blob;
};

async function mergePdfs(files: FileList): Promise<MergeResponse> {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000';
  const formData = new FormData();

  Array.from(files).forEach((file) => formData.append('files', file));

  const response = await fetch(`${backendUrl}/merge`, {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    const message = await response.text();
    return { ok: false, message };
  }

  const blob = await response.blob();
  return { ok: true, blob };
}

export default function HomePage() {
  const [status, setStatus] = useState<string | null>(null);

  return (
    <main style={{ margin: '2rem auto', maxWidth: '720px', fontFamily: 'system-ui' }}>
      <h1>IntelliPDF Dashboard</h1>
      <p>Upload multiple PDFs and merge them using the shared API backend.</p>

      <form
        onSubmit={async (event) => {
          event.preventDefault();
          const input = event.currentTarget.elements.namedItem('documents') as HTMLInputElement;
          if (!input.files || input.files.length === 0) {
            setStatus('Please select at least one PDF file.');
            return;
          }

          setStatus('Merging…');
          const result = await mergePdfs(input.files);
          if (result.ok && result.blob) {
            const url = window.URL.createObjectURL(result.blob);
            const anchor = document.createElement('a');
            anchor.href = url;
            anchor.download = 'merged.pdf';
            anchor.click();
            window.URL.revokeObjectURL(url);
            setStatus('Merged PDF downloaded.');
          } else {
            setStatus(result.message ?? 'Unable to merge PDFs.');
          }
        }}
      >
        <label style={{ display: 'block', marginBottom: '1rem' }}>
          <span style={{ display: 'block', marginBottom: '.5rem' }}>Select PDF files</span>
          <input type="file" name="documents" accept="application/pdf" multiple />
        </label>
        <button type="submit">Merge PDFs</button>
      </form>

      {status && <p style={{ marginTop: '1rem' }}>{status}</p>}
    </main>
  );
}
