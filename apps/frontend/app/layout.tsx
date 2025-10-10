import './globals.css';
import type { ReactNode } from 'react';

export const metadata = {
  title: 'IntelliPDF Dashboard',
  description: 'Interface for PDF tooling backed by IntelliPDF services.'
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
