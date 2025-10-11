
import React from "react";
import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";
import { ArrowRight, FileText, CheckCircle2 } from "lucide-react";

const features = [
  "No file size limits or watermarks",
  "Advanced security and encryption",
  "Available on all devices",
  "No registration required",
];

interface HeroProps {
  className?: string;
}

const Hero: React.FC<HeroProps> = ({ className }) => {
  return (
    <section 
      className={cn(
        "relative overflow-hidden py-20 sm:py-32 lg:py-40", 
        className
      )}
    >
      {/* Background elements */}
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(45%_50%_at_50%_50%,hsl(var(--primary)/0.08)_0%,hsl(var(--background)/0)_100%)]" />
      <div className="absolute top-0 right-0 -z-10 overflow-hidden">
        <svg
          width="800"
          height="800"
          viewBox="0 0 800 800"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="opacity-20"
        >
          <circle cx="400" cy="400" r="400" fill="url(#paint0_radial)" />
          <defs>
            <radialGradient
              id="paint0_radial"
              cx="0"
              cy="0"
              r="1"
              gradientUnits="userSpaceOnUse"
              gradientTransform="translate(400 400) rotate(90) scale(400)"
            >
              <stop stopColor="hsl(var(--primary))" />
              <stop offset="1" stopColor="hsl(var(--primary))" stopOpacity="0" />
            </radialGradient>
          </defs>
        </svg>
      </div>

      {/* Content */}
      <div className="container mx-auto px-4 sm:px-6 relative">
        <div className="flex flex-col justify-center items-center text-center max-w-3xl mx-auto">
          <div className="mb-6 animate-fade-in animate-once">
            <span className="px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium inline-flex items-center">
              <span className="flex w-2 h-2 rounded-full bg-primary mr-2"></span>
              Most powerful PDF suite
            </span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight mb-6 animate-fade-in animate-once animate-delay-100">
            Every PDF Tool <br />
            <span className="relative">
              You
              <span className="absolute -bottom-2 left-0 w-full h-1 bg-primary rounded opacity-50"></span>
            </span> Will Ever Need
          </h1>

          <p className="text-lg text-muted-foreground mb-10 max-w-2xl animate-fade-in animate-once animate-delay-200">
            Edit, convert, merge, split, compress, sign, and protect your PDFs with our all-in-one PDF solution. Simple, powerful, and beautifully designed for the perfect workflow.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 mb-16 animate-fade-in animate-once animate-delay-300">
            <Link 
              to="/tools"
              className="bg-primary hover:bg-primary/90 text-white px-6 py-3 rounded-lg font-medium shadow-lg shadow-primary/20 flex items-center justify-center smooth-transition group"
            >
              Explore All Tools
              <ArrowRight className="ml-2 w-4 h-4 group-hover:translate-x-1 smooth-transition" />
            </Link>
            <Link 
              to="/upload"
              className="bg-white hover:bg-white/90 text-foreground border border-border px-6 py-3 rounded-lg font-medium shadow-sm flex items-center justify-center smooth-transition"
            >
              <FileText className="mr-2 w-4 h-4" />
              Upload a PDF
            </Link>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-8 max-w-3xl mx-auto animate-fade-in animate-once animate-delay-400">
            {features.map((feature, index) => (
              <div key={index} className="flex items-start">
                <CheckCircle2 className="w-4 h-4 text-primary shrink-0 mt-0.5 mr-2" />
                <span className="text-sm text-muted-foreground text-left">{feature}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;
