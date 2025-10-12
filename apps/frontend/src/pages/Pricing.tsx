import React from "react";
import Layout from "@/components/Layout";
import { Check, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

const Pricing: React.FC = () => {
  const plans = [
    {
      name: "Free",
      price: "$0",
      period: "forever",
      description: "Basic PDF operations for personal use",
      features: [
        "Up to 5 PDF operations per day",
        "Maximum file size of 10MB",
        "Basic PDF tools (Merge, Split, Compress)",
        "Standard conversion quality",
        "Community support"
      ],
      buttonText: "Get Started",
      buttonLink: "/tools",
      highlighted: false
    },
    {
      name: "Pro",
      price: "$7.99",
      period: "per month",
      description: "Advanced features for professionals",
      features: [
        "Unlimited PDF operations",
        "Maximum file size of 100MB",
        "All PDF tools including advanced editing",
        "Premium conversion quality",
        "Priority email support",
        "Batch processing",
        "No watermarks or ads"
      ],
      buttonText: "Go Pro",
      buttonLink: "/checkout/pro",
      highlighted: true
    },
    {
      name: "Business",
      price: "$19.99",
      period: "per month",
      description: "Enterprise-grade PDF capabilities",
      features: [
        "Everything in Pro plan",
        "Unlimited file size",
        "Team sharing capabilities",
        "API access",
        "OCR for scanned documents",
        "Dedicated account manager",
        "Custom branding"
      ],
      buttonText: "Contact Sales",
      buttonLink: "/contact",
      highlighted: false
    }
  ];

  return (
    <Layout>
      <div className="container mx-auto px-4 sm:px-6 py-16">
        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold mb-4">Simple, Transparent Pricing</h1>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            Choose the perfect plan for your PDF needs. All plans include core features with no hidden fees.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {plans.map((plan, index) => (
            <div 
              key={index}
              className={`rounded-2xl overflow-hidden border ${
                plan.highlighted 
                  ? "border-primary shadow-lg shadow-primary/10 relative z-10 scale-105 my-4 bg-white" 
                  : "border-border bg-card"
              }`}
            >
              {plan.highlighted && (
                <div className="bg-primary text-primary-foreground text-xs font-semibold text-center py-1">
                  MOST POPULAR
                </div>
              )}
              
              <div className="p-6 md:p-8">
                <h3 className="text-xl font-bold mb-2">{plan.name}</h3>
                <div className="mb-4">
                  <span className="text-3xl font-bold">{plan.price}</span>
                  <span className="text-muted-foreground ml-1">/{plan.period}</span>
                </div>
                <p className="text-muted-foreground mb-6">{plan.description}</p>
                
                <Link
                  to={plan.buttonLink}
                  className={`w-full flex justify-center items-center py-2 px-4 rounded-lg font-medium mb-8 ${
                    plan.highlighted
                      ? "bg-primary hover:bg-primary/90 text-primary-foreground"
                      : "bg-secondary hover:bg-secondary/80 text-secondary-foreground"
                  }`}
                >
                  {plan.buttonText}
                  {plan.highlighted && <ArrowRight className="ml-2 w-4 h-4" />}
                </Link>
                
                <div className="space-y-3">
                  {plan.features.map((feature, idx) => (
                    <div key={idx} className="flex items-start">
                      <Check className={`w-5 h-5 mr-3 mt-0.5 ${plan.highlighted ? "text-primary" : "text-muted-foreground"}`} />
                      <span className="text-sm">{feature}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
        
        <div className="mt-16 max-w-3xl mx-auto text-center">
          <h2 className="text-2xl font-bold mb-4">Need a custom solution?</h2>
          <p className="text-muted-foreground mb-6">
            Contact our sales team for custom pricing options tailored to your organization's specific needs.
          </p>
          <Link
            to="/contact"
            className="bg-secondary hover:bg-secondary/80 text-secondary-foreground py-2 px-6 rounded-lg font-medium inline-flex items-center"
          >
            Contact Sales
          </Link>
        </div>
        
        <div className="mt-20 pt-8 border-t">
          <h2 className="text-2xl font-bold mb-6 text-center">Frequently Asked Questions</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            {[
              {
                q: "Can I cancel my subscription at any time?",
                a: "Yes, you can cancel your subscription at any time. Your access will continue until the end of your billing period."
              },
              {
                q: "How are the file size limits applied?",
                a: "The file size limit applies to each individual file uploaded. For example, on the Pro plan, each PDF can be up to 100MB."
              },
              {
                q: "Do you offer discounts for annual subscriptions?",
                a: "Yes, we offer a 20% discount when you choose annual billing on any of our paid plans."
              },
              {
                q: "Is my data secure when using PaperFlow?",
                a: "All files are encrypted during transit and processing. We automatically delete all files after processing is complete to ensure your data stays protected."
              }
            ].map((faq, index) => (
              <div key={index} className="mb-6">
                <h3 className="text-lg font-semibold mb-2">{faq.q}</h3>
                <p className="text-muted-foreground">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Pricing;
