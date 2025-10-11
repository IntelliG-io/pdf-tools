
import React from "react";
import Layout from "@/components/Layout";
import Hero from "@/components/Hero";
import ToolGrid from "@/components/ToolGrid";
import FileUpload from "@/components/FileUpload";
import { ArrowRight, BarChart, Lock, Zap, ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

const Index = () => {
  return (
    <Layout>
      <Hero />
      

      
      <section className="container mx-auto px-4 sm:px-6 py-12">
        <div className="flex justify-between items-center mb-8">
          <h2 className="text-2xl font-bold">Popular PDF Tools</h2>
          <Link 
            to="/tools" 
            className="flex items-center text-sm font-medium text-primary hover:underline"
          >
            View all tools
            <ChevronRight className="w-4 h-4 ml-1" />
          </Link>
        </div>
        
        <ToolGrid featured={true} />
      </section>
      
      <section className="container mx-auto px-4 sm:px-6 py-20">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold mb-4">Why Choose PaperFlow</h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Our platform is designed with simplicity and power in mind,
            giving you everything you need to work with PDFs efficiently.
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          <div className="bg-white rounded-xl p-8 shadow-sm border border-border/50 flex flex-col items-center text-center animate-fade-in animate-once">
            <div className="w-14 h-14 rounded-full bg-blue-100 flex items-center justify-center mb-6">
              <Zap className="w-7 h-7 text-blue-600" />
            </div>
            <h3 className="text-xl font-medium mb-3">Lightning Fast</h3>
            <p className="text-muted-foreground">
              All operations are processed within seconds, even with large files,
              ensuring you can get back to work immediately.
            </p>
          </div>
          
          <div className="bg-white rounded-xl p-8 shadow-sm border border-border/50 flex flex-col items-center text-center animate-fade-in animate-once animate-delay-100">
            <div className="w-14 h-14 rounded-full bg-amber-100 flex items-center justify-center mb-6">
              <Lock className="w-7 h-7 text-amber-600" />
            </div>
            <h3 className="text-xl font-medium mb-3">100% Secure</h3>
            <p className="text-muted-foreground">
              Your files are protected with enterprise-grade encryption and
              automatically deleted after processing.
            </p>
          </div>
          
          <div className="bg-white rounded-xl p-8 shadow-sm border border-border/50 flex flex-col items-center text-center animate-fade-in animate-once animate-delay-200">
            <div className="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center mb-6">
              <BarChart className="w-7 h-7 text-green-600" />
            </div>
            <h3 className="text-xl font-medium mb-3">High Quality</h3>
            <p className="text-muted-foreground">
              We maintain the highest possible quality in all operations,
              ensuring your documents look exactly as intended.
            </p>
          </div>
        </div>
      </section>
      
      <section className="container mx-auto px-4 sm:px-6 py-20">
        <div className="max-w-6xl mx-auto bg-gradient-to-br from-primary/5 to-primary/10 rounded-2xl overflow-hidden border border-primary/20 p-8 sm:p-12">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl font-bold mb-6">Ready to go premium?</h2>
              <p className="text-muted-foreground mb-8">
                Unlock advanced features, higher file size limits, batch processing,
                and priority support with our premium plans starting at just $7.99/month.
              </p>
              
              <ul className="space-y-4 mb-8">
                {[
                  "No file size limitations",
                  "Process up to 100 files at once",
                  "Advanced editing capabilities",
                  "OCR for scanned documents",
                  "Cloud storage integration",
                ].map((feature, index) => (
                  <li key={index} className="flex items-start">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary mr-3 mt-1">
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                      <path d="m9 11 3 3L22 4" />
                    </svg>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              
              <Link 
                to="/pricing"
                className="bg-primary hover:bg-primary/90 text-white px-6 py-3 rounded-lg font-medium shadow-lg shadow-primary/20 inline-flex items-center justify-center smooth-transition"
              >
                View Pricing Plans
                <ArrowRight className="ml-2 w-4 h-4" />
              </Link>
            </div>
            
            <div className="lg:flex justify-end hidden">
              <div className="relative">
                <div className="absolute -left-32 -top-32 w-64 h-64 bg-primary/30 rounded-full blur-3xl opacity-20" />
                <div className="absolute -right-32 -bottom-32 w-64 h-64 bg-primary/30 rounded-full blur-3xl opacity-30" />
                
                <div className="bg-white rounded-xl shadow-xl border border-border p-6 relative z-10 transform rotate-1 animate-float">
                  <div className="flex justify-between items-center mb-6">
                    <h3 className="font-bold text-lg">Pro Plan</h3>
                    <div className="px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium">
                      Most Popular
                    </div>
                  </div>
                  
                  <div className="mb-6">
                    <span className="text-3xl font-bold">$7.99</span>
                    <span className="text-muted-foreground"> / month</span>
                  </div>
                  
                  <div className="space-y-3 mb-8">
                    {[
                      "Unlimited PDF operations",
                      "Files up to 100MB",
                      "Batch processing",
                      "Advanced editing tools",
                      "Priority support",
                    ].map((feature, index) => (
                      <div key={index} className="flex items-start">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary mr-3 mt-0.5">
                          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                          <path d="m9 11 3 3L22 4" />
                        </svg>
                        <span className="text-sm">{feature}</span>
                      </div>
                    ))}
                  </div>
                  
                  <button className="w-full bg-primary hover:bg-primary/90 text-white px-4 py-2 rounded-lg font-medium shadow-md smooth-transition">
                    Get Started
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
      
      <section className="container mx-auto px-4 sm:px-6 pt-10 pb-32">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-2xl sm:text-3xl font-bold mb-6">Ready to transform your PDF workflow?</h2>
          <p className="text-muted-foreground mb-8">
            Join millions of users who trust PaperFlow for their document needs. 
            Start for free, no registration required.
          </p>
          
          <Link 
            to="/tools"
            className="bg-primary hover:bg-primary/90 text-white px-8 py-4 rounded-lg font-medium shadow-lg shadow-primary/20 inline-flex items-center justify-center smooth-transition text-lg"
          >
            Get Started Now
            <ArrowRight className="ml-2 w-5 h-5" />
          </Link>
        </div>
      </section>
    </Layout>
  );
};

export default Index;
