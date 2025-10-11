import React from "react";
import Layout from "@/components/Layout";
import { Users, Zap, Shield, Globe, Mail, Twitter, Github } from "lucide-react";
import { Link } from "react-router-dom";

const About: React.FC = () => {
  return (
    <Layout>
      <div className="container mx-auto px-4 sm:px-6 py-16">
        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold mb-4">About PaperFlow</h1>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            We're on a mission to make working with PDFs simple, efficient, and accessible for everyone.
          </p>
        </div>

        {/* Our Story */}
        <div className="max-w-3xl mx-auto mb-24">
          <h2 className="text-2xl font-bold mb-6 text-center">Our Story</h2>
          <div className="prose prose-lg max-w-none">
            <p>
              PaperFlow was founded in 2023 by a team of developers who were frustrated with the 
              existing PDF solutions on the market. We found most tools to be either too complex, 
              too expensive, or lacking the features we needed.
            </p>
            <p>
              We set out to build a solution that would be intuitive enough for casual users but powerful 
              enough for professional workflows. After months of development and testing, we launched 
              PaperFlow with a simple goal: to create the best PDF tools on the web.
            </p>
            <p>
              Today, PaperFlow is used by thousands of professionals, students, and businesses around 
              the world. We're constantly improving our platform based on user feedback and industry 
              trends to ensure we're always providing the most useful PDF tools possible.
            </p>
          </div>
        </div>

        {/* Our Values */}
        <div className="mb-24">
          <h2 className="text-2xl font-bold mb-10 text-center">Our Values</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {[
              {
                icon: <Zap className="w-8 h-8 text-blue-600" />,
                title: "Simplicity",
                description: "We believe powerful tools don't need to be complicated. Everything we build focuses on intuitive design and ease of use."
              },
              {
                icon: <Shield className="w-8 h-8 text-green-600" />,
                title: "Privacy",
                description: "Your documents contain sensitive information. We prioritize security and privacy in everything we do."
              },
              {
                icon: <Users className="w-8 h-8 text-purple-600" />,
                title: "Accessibility",
                description: "We're committed to making our tools available to everyone, regardless of technical expertise or budget."
              }
            ].map((value, index) => (
              <div key={index} className="text-center">
                <div className="w-16 h-16 rounded-full bg-secondary flex items-center justify-center mx-auto mb-4">
                  {value.icon}
                </div>
                <h3 className="text-xl font-semibold mb-2">{value.title}</h3>
                <p className="text-muted-foreground">{value.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Team Section */}
        <div className="mb-24">
          <h2 className="text-2xl font-bold mb-10 text-center">Our Team</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 max-w-5xl mx-auto">
            {[
              {
                name: "Alex Johnson",
                role: "Founder & CEO",
                bio: "Former software engineer with 10+ years of experience in document processing technologies.",
                image: "https://randomuser.me/api/portraits/men/32.jpg"
              },
              {
                name: "Sarah Chen",
                role: "CTO",
                bio: "PhD in Computer Science with expertise in machine learning and document analysis.",
                image: "https://randomuser.me/api/portraits/women/44.jpg"
              },
              {
                name: "Michael Rodriguez",
                role: "Head of Design",
                bio: "Award-winning UX designer passionate about creating intuitive user experiences.",
                image: "https://randomuser.me/api/portraits/men/22.jpg"
              },
              {
                name: "Emma Williams",
                role: "Customer Success",
                bio: "Dedicated to ensuring customers get the most value from our platform.",
                image: "https://randomuser.me/api/portraits/women/29.jpg"
              }
            ].map((member, index) => (
              <div key={index} className="text-center">
                <div className="mb-4">
                  <img 
                    src={member.image} 
                    alt={member.name} 
                    className="w-24 h-24 rounded-full mx-auto object-cover"
                  />
                </div>
                <h3 className="text-lg font-semibold mb-1">{member.name}</h3>
                <p className="text-sm text-primary mb-2">{member.role}</p>
                <p className="text-sm text-muted-foreground">{member.bio}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Contact Section */}
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-2xl font-bold mb-4">Get In Touch</h2>
          <p className="text-muted-foreground mb-8">
            Have questions or feedback? We'd love to hear from you.
          </p>
          
          <div className="flex flex-wrap justify-center gap-4 mb-8">
            <a 
              href="mailto:hello@paperflow.com" 
              className="flex items-center px-4 py-2 rounded-lg bg-secondary hover:bg-secondary/80 text-secondary-foreground"
            >
              <Mail className="w-4 h-4 mr-2" />
              hello@paperflow.com
            </a>
            <a 
              href="https://twitter.com/paperflow" 
              className="flex items-center px-4 py-2 rounded-lg bg-secondary hover:bg-secondary/80 text-secondary-foreground"
            >
              <Twitter className="w-4 h-4 mr-2" />
              @paperflow
            </a>
            <a 
              href="https://github.com/paperflow" 
              className="flex items-center px-4 py-2 rounded-lg bg-secondary hover:bg-secondary/80 text-secondary-foreground"
            >
              <Github className="w-4 h-4 mr-2" />
              github.com/paperflow
            </a>
          </div>
          
          <div>
            <Link
              to="/contact"
              className="bg-primary hover:bg-primary/90 text-primary-foreground px-6 py-3 rounded-lg font-medium inline-flex items-center"
            >
              Contact Us
            </Link>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default About;
