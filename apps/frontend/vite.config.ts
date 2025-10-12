import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on mode
  const env = loadEnv(mode, process.cwd(), '');
  const apiUrl = env.VITE_API_URL || 'http://165.227.96.78:3000';
  
  // Extract host from API URL
  const apiHost = apiUrl.replace(/https?:\/\//, '').split('/')[0];
  const apiProtocol = apiUrl.startsWith('https') ? 'https' : 'http';
  const target = `${apiProtocol}://${apiHost}`;
  
  return {
    server: {
      host: "::",
      port: 8080,
      proxy: {
        '/pdf': {
          target,
          changeOrigin: true,
          secure: false,
        },
        '/api/pdf': {
          target,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    plugins: [
      react(),
      mode === 'development' &&
      componentTagger(),
    ].filter(Boolean),
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  };
});
