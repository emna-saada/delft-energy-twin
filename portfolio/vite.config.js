import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// base './' so the build works on GitHub Pages, Vercel or Netlify without changes
export default defineConfig({
  base: './',
  plugins: [react()]
});
