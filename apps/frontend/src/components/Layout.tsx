
import React from "react";
import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";

interface LayoutProps {
  children: React.ReactNode;
  className?: string;
}

const Layout: React.FC<LayoutProps> = ({ children, className }) => {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-50 w-full glass border-b border-white/10">
        <div className="container mx-auto flex items-center justify-between h-16 px-4 md:px-6">
          <Link 
            to="/" 
            className="flex items-center gap-2 smooth-transition hover:opacity-80"
          >
            <div className="relative w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-white font-bold">
              <span>P</span>
              <span className="absolute -top-1 -right-1 w-3 h-3 bg-white rounded-full border-2 border-primary"></span>
            </div>
            <span className="font-medium text-lg">PaperFlow</span>
          </Link>

          <nav className="hidden md:flex items-center gap-6">
            <Link to="/" className="text-sm font-medium hover:text-primary smooth-transition">Home</Link>
            <Link to="/tools" className="text-sm font-medium hover:text-primary smooth-transition">All Tools</Link>
            <Link to="/pricing" className="text-sm font-medium hover:text-primary smooth-transition">Pricing</Link>
            <Link to="/about" className="text-sm font-medium hover:text-primary smooth-transition">About</Link>
          </nav>

          <div className="flex items-center gap-4">
            <button className="text-sm font-medium hover:text-primary smooth-transition hidden md:block">
              Sign In
            </button>
            <button className="bg-primary text-white px-4 py-2 rounded-md text-sm font-medium shadow-sm hover:bg-primary/90 smooth-transition">
              Sign Up Free
            </button>
          </div>
        </div>
      </header>

      <main className={cn("flex-1", className)}>
        {children}
      </main>

      <footer className="w-full border-t border-border/40 py-6 md:py-12 bg-secondary/50">
        <div className="container mx-auto px-4 md:px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <div>
              <h3 className="text-sm font-medium mb-4">Company</h3>
              <ul className="space-y-2">
                <li><Link to="/about" className="text-sm text-muted-foreground hover:text-foreground smooth-transition">About</Link></li>
                <li><Link to="/contact" className="text-sm text-muted-foreground hover:text-foreground smooth-transition">Contact</Link></li>
                <li><Link to="/careers" className="text-sm text-muted-foreground hover:text-foreground smooth-transition">Careers</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-medium mb-4">Products</h3>
              <ul className="space-y-2">
                <li><Link to="/tools" className="text-sm text-muted-foreground hover:text-foreground smooth-transition">All Tools</Link></li>
                <li><Link to="/pricing" className="text-sm text-muted-foreground hover:text-foreground smooth-transition">Pricing</Link></li>
                <li><Link to="/enterprise" className="text-sm text-muted-foreground hover:text-foreground smooth-transition">Enterprise</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-medium mb-4">Resources</h3>
              <ul className="space-y-2">
                <li><Link to="/blog" className="text-sm text-muted-foreground hover:text-foreground smooth-transition">Blog</Link></li>
                <li><Link to="/help" className="text-sm text-muted-foreground hover:text-foreground smooth-transition">Help Center</Link></li>
                <li><Link to="/developers" className="text-sm text-muted-foreground hover:text-foreground smooth-transition">Developers</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-medium mb-4">Legal</h3>
              <ul className="space-y-2">
                <li><Link to="/privacy" className="text-sm text-muted-foreground hover:text-foreground smooth-transition">Privacy</Link></li>
                <li><Link to="/terms" className="text-sm text-muted-foreground hover:text-foreground smooth-transition">Terms</Link></li>
                <li><Link to="/security" className="text-sm text-muted-foreground hover:text-foreground smooth-transition">Security</Link></li>
              </ul>
            </div>
          </div>
          <div className="mt-12 pt-8 border-t border-border/40 flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-primary rounded-lg flex items-center justify-center text-white font-bold text-xs">
                <span>P</span>
              </div>
              <span className="text-sm font-medium">PaperFlow</span>
            </div>
            <p className="text-sm text-muted-foreground">
              © {new Date().getFullYear()} PaperFlow. All rights reserved.
            </p>
            <div className="flex flex-col md:flex-row items-center gap-4">
              <div className="flex items-center gap-4">
                <a href="#" aria-label="Twitter" className="text-muted-foreground hover:text-foreground smooth-transition">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-twitter"><path d="M22 4s-.7 2.1-2 3.4c1.6 10-9.4 17.3-18 11.6 2.2.1 4.4-.6 6-2C3 15.5.5 9.6 3 5c2.2 2.6 5.6 4.1 9 4-.9-4.2 4-6.6 7-3.8 1.1 0 3-1.2 3-1.2z"/></svg>
                </a>
                <a href="#" aria-label="Facebook" className="text-muted-foreground hover:text-foreground smooth-transition">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-facebook"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg>
                </a>
                <a href="#" aria-label="Instagram" className="text-muted-foreground hover:text-foreground smooth-transition">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-instagram"><rect width="20" height="20" x="2" y="2" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" x2="17.51" y1="6.5" y2="6.5"/></svg>
                </a>
                <a href="#" aria-label="LinkedIn" className="text-muted-foreground hover:text-foreground smooth-transition">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-linkedin"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/><rect width="4" height="12" x="2" y="9"/><circle cx="4" cy="4" r="2"/></svg>
                </a>
              </div>
              
              <div className="flex items-center gap-3 mt-4 md:mt-0 md:ml-4">
                <a href="#" aria-label="App Store" className="hover:opacity-80 smooth-transition">
                  <svg width="120" height="40" viewBox="0 0 120 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect width="120" height="40" rx="6" fill="black"/>
                    <path d="M24.9956 20.0001C24.9869 17.6656 26.0478 15.8251 28.1784 14.4954C26.9994 12.7847 25.1981 11.8541 22.8462 11.6956C20.6033 11.5413 18.1846 13.0482 17.2585 13.0482C16.2956 13.0482 14.1912 11.7356 12.3724 11.7356C9.30275 11.7866 6.03869 14.1653 6.03869 19.0288C6.03869 20.5569 6.31244 22.1329 6.85994 23.7526C7.59462 25.8879 10.2171 31.6891 12.9637 31.6007C14.3143 31.5638 15.276 30.5238 17.0815 30.5238C18.8337 30.5238 19.7368 31.6007 21.2429 31.6007C23.9999 31.5569 26.3649 26.2407 27.0637 24.0976C23.3631 22.3194 24.9956 20.0976 24.9956 20.0001Z" fill="white"/>
                    <path d="M21.5806 9.36816C23.3109 7.2835 23.0632 5.39725 23.0109 4.66699C21.4521 4.75038 19.625 5.71225 18.5162 6.94599C17.3162 8.2835 16.7159 9.85474 16.8478 11.6553C18.5293 11.7866 20.1249 11.0319 21.5806 9.36816Z" fill="white"/>
                    <path d="M38.3475 27.6188H33.3331L32.0935 31.4875H29.9761L34.7375 18.2788H36.9852L41.7444 31.4875H39.5875L38.3475 27.6188ZM33.8674 26.0538H37.8109L35.8674 20.0107H35.8109L33.8674 26.0538Z" fill="white"/>
                    <path d="M53.3935 26.0538C53.3935 29.4069 51.6196 31.6307 48.8891 31.6307C47.4084 31.6744 46.0957 30.9001 45.4544 29.6126H45.4065V35.0176H43.3935V20.6307H45.3413V22.5723H45.375C46.0471 21.2691 47.3761 20.4711 48.8739 20.5138C51.6326 20.5138 53.3935 22.7513 53.3935 26.0538ZM51.3239 26.0538C51.3239 23.8451 50.1621 22.3976 48.4022 22.3976C46.6694 22.3976 45.4935 23.8726 45.4935 26.0538C45.4935 28.2488 46.6694 29.71 48.4022 29.71C50.1621 29.71 51.3239 28.2763 51.3239 26.0538Z" fill="white"/>
                    <path d="M65.5172 26.0538C65.5172 29.4069 63.7456 31.6307 61.0151 31.6307C59.5323 31.6744 58.2197 30.9001 57.5804 29.6126H57.5325V35.0176H55.5172V20.6307H57.4651V22.5723H57.4997C58.1716 21.2691 59.5001 20.4711 60.9997 20.5138C63.7585 20.5138 65.5172 22.7513 65.5172 26.0538ZM63.4498 26.0538C63.4498 23.8451 62.288 22.3976 60.5281 22.3976C58.7934 22.3976 57.6194 23.8726 57.6194 26.0538C57.6194 28.2488 58.7934 29.71 60.5281 29.71C62.288 29.71 63.4498 28.2763 63.4498 26.0538Z" fill="white"/>
                    <path d="M72.3413 27.2946C72.488 28.7669 73.8652 29.7376 75.8261 29.7376C77.688 29.7376 78.9718 28.7669 78.9718 27.4638C78.9718 26.3519 78.213 25.6821 76.2913 25.2207L74.3674 24.7731C71.7663 24.1532 70.6152 22.8501 70.6152 20.8638C70.6152 18.3696 72.8196 16.6782 75.7999 16.6782C78.7435 16.6782 80.8609 18.3696 80.9348 20.8638H78.9043C78.7935 19.3919 77.6152 18.4896 75.7674 18.4896C73.9196 18.4896 72.7413 19.4057 72.7413 20.7126C72.7413 21.7169 73.463 22.3232 75.3761 22.7846L77.0239 23.1798C79.9348 23.8669 81.0859 25.1151 81.0859 27.2121C81.0859 29.8732 78.8935 31.5507 75.7 31.5507C72.738 31.5507 70.438 29.9096 70.3185 27.2946H72.3413Z" fill="white"/>
                    <path d="M87.0675 18.5721H84.5435V20.6309H87.0675V29.5446C87.0675 30.9446 88.1716 31.5513 90.1119 31.4911C90.5586 31.4823 91.0043 31.4504 91.4489 31.3946V29.3821C91.1847 29.4134 90.9184 29.4309 90.6521 29.4328C89.838 29.4328 89.1 29.154 89.1 28.0634V20.6309H91.4489V18.5721H89.1V15.3696H87.0675V18.5721Z" fill="white"/>
                    <path d="M93.0066 26.0537C93.0066 22.6643 95.0673 20.4854 98.3047 20.4854C101.556 20.4854 103.616 22.6643 103.616 26.0537C103.616 29.4485 101.568 31.6201 98.3047 31.6201C95.0456 31.6201 93.0066 29.4485 93.0066 26.0537ZM101.559 26.0537C101.559 23.7188 100.346 22.3326 98.3047 22.3326C96.263 22.3326 95.0521 23.7325 95.0521 26.0537C95.0521 28.3942 96.263 29.7731 98.3047 29.7731C100.346 29.7731 101.559 28.3804 101.559 26.0537Z" fill="white"/>
                    <path d="M106.002 31.4875V16.8179H107.998V22.5715H108.046C108.472 21.8296 109.064 21.2146 109.77 20.7909C110.477 20.3673 111.275 20.1509 112.083 20.1631C114.648 20.1631 116.277 22.0715 116.277 25.0456V31.4875H114.258V25.3327C114.258 23.4631 113.388 22.351 111.799 22.351C111.268 22.3306 110.742 22.4444 110.271 22.6822C109.8 22.9201 109.399 23.2742 109.108 23.71C108.817 24.1458 108.645 24.6473 108.606 25.1693C108.567 25.6913 108.663 26.2143 108.884 26.6894V31.4875H106.002Z" fill="white"/>
                  </svg>
                </a>
                <a href="#" aria-label="Play Store" className="hover:opacity-80 smooth-transition">
                  <svg width="135" height="40" viewBox="0 0 135 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect width="135" height="40" rx="6" fill="black"/>
                    <path d="M47.4199 10.24H43.0195V29.5352H47.4199V10.24Z" fill="white"/>
                    <path d="M66.7871 22.3242L61.8789 10.24H57.0156V29.5352H61.4062V17.4512L66.3125 29.5352H71.1855V10.24H66.7852V22.3242H66.7871Z" fill="white"/>
                    <path d="M83.793 14.5352H88.1934V29.5352H92.5938V14.5352H96.9941V10.24H83.793V14.5352Z" fill="white"/>
                    <path d="M118.004 20.9863C118.004 14.5371 113.848 9.9004 108.777 9.9004C103.707 9.9004 99.5508 14.5371 99.5508 20.9863C99.5508 27.4356 103.707 32.0723 108.777 32.0723C113.848 32.0723 118.004 27.4356 118.004 20.9863ZM113.418 20.9863C113.418 25.12 111.215 27.8047 108.777 27.8047C106.34 27.8047 104.137 25.12 104.137 20.9863C104.137 16.8527 106.34 14.168 108.777 14.168C111.215 14.168 113.418 16.8527 113.418 20.9863Z" fill="white"/>
                    <path fill-rule="evenodd" clip-rule="evenodd" d="M21.3979 20.0121L9.68548 31.8879C9.36311 31.5394 9.18677 31.0636 9.18677 30.5151V9.47273C9.18677 8.9242 9.36311 8.44847 9.68548 8.09996L21.3979 20.0121Z" fill="#EA4335"/>
                    <path fill-rule="evenodd" clip-rule="evenodd" d="M21.3979 20.0125L34.3066 13.0004C34.6824 13.2032 34.9968 13.4908 35.2235 13.8455C35.4502 14.2003 35.582 14.6113 35.6056 15.0368V24.988C35.5813 25.4119 35.4492 25.8211 35.2226 26.1741C34.996 26.5271 34.682 26.8129 34.3066 27.0142L21.3979 20.0125Z" fill="#FBBC04"/>
                    <path fill-rule="evenodd" clip-rule="evenodd" d="M9.69099 8.1001C9.97983 7.78944 10.339 7.55325 10.7377 7.41223V7.41254L26.0022 15.3731L21.3981 20.0124L9.69099 8.1001Z" fill="#4285F4"/>
                    <path fill-rule="evenodd" clip-rule="evenodd" d="M21.3979 20.0121L26.0019 24.6515L10.7377 32.6016C10.3399 32.4617 9.98127 32.2266 9.69252 31.9172L21.3979 20.0121Z" fill="#34A853"/>
                  </svg>
                </a>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
