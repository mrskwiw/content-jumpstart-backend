import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Add cache busting with hash to filenames
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',

        manualChunks: {
          // Core React libraries
          'react-vendor': ['react', 'react-dom', 'react/jsx-runtime'],

          // React Router
          'router': ['react-router-dom'],

          // Data fetching and state management
          'query': ['@tanstack/react-query', 'axios'],

          // UI components (if you're using a library like shadcn/ui)
          // Uncomment if you have large UI dependencies
          // 'ui': ['@radix-ui/react-dialog', '@radix-ui/react-select', ...],
        },
      },
    },
    // Enable CSS code splitting
    cssCodeSplit: true,

    // Optimize chunk size warnings
    chunkSizeWarningLimit: 1000,

    // Source maps for production debugging (enable for easier debugging)
    sourcemap: true,

    // Minification
    minify: 'esbuild',

    // Target modern browsers for smaller bundles
    target: 'es2015',

    // Clear output directory before build to remove stale files
    emptyOutDir: true,
  },

  // Development server optimization
  server: {
    // Enable HTTP/2 for faster dev loading
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },

  // Preview server configuration
  preview: {
    port: 4173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
