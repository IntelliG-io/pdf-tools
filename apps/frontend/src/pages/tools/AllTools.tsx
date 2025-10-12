import React from "react";
import Layout from "@/components/Layout";
import ToolGrid from "@/components/ToolGrid";
import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

const AllTools: React.FC = () => {
  return (
    <Layout>
      <div className="container mx-auto px-4 sm:px-6 py-12">
        <div className="flex items-center mb-8">
          <Link 
            to="/" 
            className="flex items-center text-sm text-muted-foreground hover:text-primary transition-colors"
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back to Home
          </Link>
        </div>

        <div className="text-center mb-10">
          <div className="w-16 h-16 bg-amber-100 mx-auto rounded-lg flex items-center justify-center mb-6">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-8 h-8 text-amber-600">
              <path d="M21 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v3" />
              <path d="M21 16v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-3" />
              <rect x="2" y="8" width="20" height="8" rx="1" />
              <path d="M12 8v8" />
            </svg>
          </div>
          <h1 className="text-4xl font-bold mb-4">All PDF Tools</h1>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            Our comprehensive collection of PDF tools to help you edit, convert, and manage your documents.
            Select any tool to get started.
          </p>
        </div>
        
        <ToolGrid />
      </div>
    </Layout>
  );
};

export default AllTools;
