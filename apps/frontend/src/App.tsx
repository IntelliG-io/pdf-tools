
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import NotFound from "./pages/NotFound";
import AllTools from "./pages/tools/AllTools";
import Pricing from "./pages/Pricing";
import About from "./pages/About";

// Import new PDF tool pages
import MergePDF from "./pages/tools/MergePDF";
import SplitPDF from "./pages/tools/SplitPDF";
import ConvertPDF from "./pages/tools/ConvertPDF";
import CompressPDF from "./pages/tools/CompressPDF";
import PdfToDocx from "./pages/tools/PdfToDocx";
import ProtectPDF from "./pages/tools/ProtectPDFWithLayout";
import RotatePDF from "./pages/tools/RotatePDF";
import NumberPages from "./pages/tools/NumberPages";
import WatermarkPDF from "./pages/tools/WatermarkPDF";
import PdfToImage from "./pages/tools/PdfToImage";

// Legacy route handler for backward compatibility
import Tool from "./pages/Tool";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/tools" element={<AllTools />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/about" element={<About />} />
          
          {/* New dedicated tool routes */}
          <Route path="/tools/merge-pdf" element={<MergePDF />} />
          <Route path="/tools/split-pdf" element={<SplitPDF />} />
          <Route path="/tools/convert-pdf" element={<ConvertPDF />} />
          <Route path="/tools/compress-pdf" element={<CompressPDF />} />
          <Route path="/tools/pdf-to-docx" element={<PdfToDocx />} />
          <Route path="/tools/protect-pdf" element={<ProtectPDF />} />
          <Route path="/tools/rotate-pdf" element={<RotatePDF />} />
          <Route path="/tools/number-pages" element={<NumberPages />} />
          <Route path="/tools/watermark-pdf" element={<WatermarkPDF />} />
          <Route path="/tools/pdf-to-image" element={<PdfToImage />} />
          
          {/* Legacy route for backward compatibility */}
          <Route path="/tool/:toolId" element={<Tool />} />
          
          {/* Catch-all route */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
