// vite.config.ts
import { defineConfig } from "file:///D:/Code/Novel-Engine/frontend/node_modules/vitest/dist/config.js";
import react from "file:///D:/Code/Novel-Engine/frontend/node_modules/@vitejs/plugin-react/dist/index.js";
import { resolve } from "path";
var __vite_injected_original_dirname = "D:\\Code\\Novel-Engine\\frontend";
var devPort = Number(process.env.VITE_DEV_PORT || process.env.PORT || 3e3);
var vite_config_default = defineConfig({
  plugins: [
    react()
    // nodePolyfills removed for debugging
  ],
  // Manual process polyfill via define
  // MIGRATION NOTE: Transitioning from REACT_APP_* to VITE_* (VITE_* takes precedence)
  /* define: {
    global: 'globalThis',
    'process': JSON.stringify({
      env: {
        NODE_ENV: process.env.NODE_ENV || 'development',
        // Backward compatibility: Keep REACT_APP_* for existing code
        REACT_APP_API_BASE_URL: process.env.VITE_API_BASE_URL || process.env.REACT_APP_API_BASE_URL || 'http://localhost:3000/v1',
        REACT_APP_API_TIMEOUT: process.env.VITE_API_TIMEOUT || process.env.REACT_APP_API_TIMEOUT || '10000',
        REACT_APP_API_URL: process.env.VITE_API_URL || process.env.REACT_APP_API_URL || 'http://localhost:8000',
        REACT_APP_DOCKER: process.env.VITE_DOCKER || process.env.REACT_APP_DOCKER || 'false',
      },
      platform: 'browser',
      version: '18.0.0',
      versions: { node: '18.0.0' },
      nextTick: (callback, ...args) => setTimeout(() => callback(...args), 0),
      cwd: () => '/',
      argv: [],
      stdout: { write: () => {} },
      stderr: { write: () => {} },
    }),
    'process.env': JSON.stringify({
      NODE_ENV: process.env.NODE_ENV || 'development',
      // Backward compatibility: Keep REACT_APP_* for existing code
      REACT_APP_API_BASE_URL: process.env.VITE_API_BASE_URL || process.env.REACT_APP_API_BASE_URL || 'http://localhost:3000/v1',
      REACT_APP_API_TIMEOUT: process.env.VITE_API_TIMEOUT || process.env.REACT_APP_API_TIMEOUT || '10000',
      REACT_APP_API_URL: process.env.VITE_API_URL || process.env.REACT_APP_API_URL || 'http://localhost:8000',
      REACT_APP_DOCKER: process.env.VITE_DOCKER || process.env.REACT_APP_DOCKER || 'false',
    }),
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'development'),
    'process.env.REACT_APP_API_BASE_URL': JSON.stringify(process.env.VITE_API_BASE_URL || process.env.REACT_APP_API_BASE_URL || 'http://localhost:3000/v1'),
    'process.env.REACT_APP_API_TIMEOUT': JSON.stringify(process.env.VITE_API_TIMEOUT || process.env.REACT_APP_API_TIMEOUT || '10000'),
    'process.env.REACT_APP_API_URL': JSON.stringify(process.env.VITE_API_URL || process.env.REACT_APP_API_URL || 'http://localhost:8000'),
    'process.env.REACT_APP_DOCKER': JSON.stringify(process.env.VITE_DOCKER || process.env.REACT_APP_DOCKER || 'false'),
  }, */
  // Performance optimizations
  build: {
    // Code splitting and chunk optimization
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor chunks for better caching
          vendor: ["react", "react-dom"],
          // Heavy libraries split for mobile optimization
          animation: ["framer-motion"],
          utils: ["axios", "socket.io-client", "lodash-es"],
          query: ["react-query", "@reduxjs/toolkit", "react-redux"],
          xyflow: ["@xyflow/react"]
        }
      }
    },
    outDir: "dist",
    emptyOutDir: true
    // terserOptions: {
    //   compress: {
    //     drop_console: true, // Remove console.log in production
    //     drop_debugger: true,
    //     dead_code: true,
    //     unused: true,
    //   },
    //   mangle: {
    //     safari10: true, // Fix Safari 10+ issues
    //   },
    // },
  },
  // Development server optimizations
  server: {
    port: devPort,
    host: "0.0.0.0",
    // Enable network access for WSL2/Docker
    strictPort: true,
    // Fail if port is already in use
    cors: true,
    // HMR optimization for WSL2 - use WebSocket protocol
    hmr: {
      protocol: "ws",
      host: "localhost",
      port: devPort,
      clientPort: devPort
      // Prevent port mapping confusion
    },
    // WSL2 file watching fix - use polling with faster interval
    watch: {
      usePolling: true,
      interval: 100
      // Faster polling for better responsiveness
    },
    proxy: {
      // Proxy /api/* to backend without versioning
      // Use 127.0.0.1 explicitly for WSL2 compatibility (avoid IPv6 resolution issues)
      "/api": {
        target: process.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
        changeOrigin: true,
        // SSE-specific configuration for event streaming
        configure: (proxy, _options) => {
          proxy.on("proxyReq", (proxyReq, req, _res) => {
            var _a;
            if ((_a = req.url) == null ? void 0 : _a.includes("/events/stream")) {
              proxyReq.setHeader("Accept", "text/event-stream");
              proxyReq.setHeader("Cache-Control", "no-cache");
              proxyReq.setHeader("Connection", "keep-alive");
            }
          });
        }
      },
      // Proxy /meta/* to backend
      "/meta": {
        target: process.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
        changeOrigin: true
      },
      // Proxy /health to backend
      "/health": {
        target: process.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
        changeOrigin: true
      }
    }
  },
  // Dependency optimization
  optimizeDeps: {
    include: [
      "react",
      "react-dom",
      "axios",
      "framer-motion"
    ]
  },
  // Path resolution
  resolve: {
    alias: {
      "@": resolve(__vite_injected_original_dirname, "src"),
      "@components": resolve(__vite_injected_original_dirname, "src/components"),
      "@hooks": resolve(__vite_injected_original_dirname, "src/hooks"),
      "@services": resolve(__vite_injected_original_dirname, "src/services"),
      "@types": resolve(__vite_injected_original_dirname, "src/types"),
      "@/styles": resolve(__vite_injected_original_dirname, "src/styles"),
      "@/lib": resolve(__vite_injected_original_dirname, "src/lib"),
      // MUI shims for gradual migration to Tailwind
      "@mui/material": resolve(__vite_injected_original_dirname, "src/shim/mui-material.tsx"),
      "@mui/material/styles": resolve(__vite_injected_original_dirname, "src/shim/mui-material.tsx"),
      "@mui/material/Box": resolve(__vite_injected_original_dirname, "src/shim/mui-material.tsx"),
      "@mui/material/Typography": resolve(__vite_injected_original_dirname, "src/shim/mui-material.tsx"),
      "@mui/material/Chip": resolve(__vite_injected_original_dirname, "src/shim/mui-material.tsx"),
      "@mui/material/Stack": resolve(__vite_injected_original_dirname, "src/shim/mui-material.tsx"),
      "@mui/material/List": resolve(__vite_injected_original_dirname, "src/shim/mui-material.tsx"),
      "@mui/material/ListItem": resolve(__vite_injected_original_dirname, "src/shim/mui-material.tsx"),
      "@mui/material/ListItemAvatar": resolve(__vite_injected_original_dirname, "src/shim/mui-material.tsx"),
      "@mui/material/ListItemText": resolve(__vite_injected_original_dirname, "src/shim/mui-material.tsx"),
      "@mui/material/Avatar": resolve(__vite_injected_original_dirname, "src/shim/mui-material.tsx"),
      "@mui/material/LinearProgress": resolve(__vite_injected_original_dirname, "src/shim/mui-material.tsx"),
      "@mui/material/Fade": resolve(__vite_injected_original_dirname, "src/shim/mui-material.tsx"),
      "@mui/material/useMediaQuery": resolve(__vite_injected_original_dirname, "src/shim/mui-material.tsx"),
      "@mui/icons-material": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/Menu": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/Add": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/RocketLaunch": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/LiveTv": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/Insights": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/Security": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/LockPerson": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/Visibility": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/VisibilityOff": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/AutoStories": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/Description": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/PlayArrow": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/MoreVert": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/CheckCircle": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/Refresh": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/RadioButtonUnchecked": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/Person": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/PlayCircle": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/Groups": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/MenuBook": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/Link": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/Diversity3": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/TrendingFlat": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/LocationOn": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/Timeline": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/OpenInFull": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@mui/icons-material/InfoOutlined": resolve(__vite_injected_original_dirname, "src/shim/mui-icons.tsx"),
      "@/styles/tokens": resolve(__vite_injected_original_dirname, "src/shim/tokens.ts")
    }
  },
  // CSS optimization
  css: {
    devSourcemap: true,
    preprocessorOptions: {
      scss: {
        additionalData: `@import "@/styles/variables.scss";`
      }
    }
  },
  // Preview configuration with SPA fallback
  preview: {
    port: 4173,
    host: true,
    proxy: {
      // Proxy /api/* to backend in preview mode
      // Use 127.0.0.1 explicitly for WSL2 compatibility
      "/api": {
        target: process.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
        changeOrigin: true
      },
      "/meta": {
        target: process.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
        changeOrigin: true
      },
      "/health": {
        target: process.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
        changeOrigin: true
      }
    }
  },
  // App type for SPA history fallback support
  appType: "spa",
  // Vitest Configuration
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    isolate: true,
    css: false,
    // Disable CSS processing for faster tests
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80
      },
      exclude: [
        "node_modules/",
        "src/test/setup.ts",
        "**/*.test.tsx",
        "**/*.test.ts",
        "**/*.spec.ts",
        "dist/"
      ]
    },
    fileParallelism: false,
    // Disable parallelism to prevent hangs on limited resources
    pool: "forks",
    // Use forks instead of threads for better isolation
    // Vitest 4: poolOptions moved to top-level
    singleFork: true,
    // Run tests sequentially in a single fork
    testTimeout: 1e4,
    hookTimeout: 1e4,
    reporters: ["verbose"],
    // Exclude e2e tests and integration tests from unit test runs
    exclude: ["node_modules", "dist", "**/*.spec.ts", "**/*.spec.tsx", "**/tests/integration/**", "tests/integration"]
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJEOlxcXFxDb2RlXFxcXE5vdmVsLUVuZ2luZVxcXFxmcm9udGVuZFwiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9maWxlbmFtZSA9IFwiRDpcXFxcQ29kZVxcXFxOb3ZlbC1FbmdpbmVcXFxcZnJvbnRlbmRcXFxcdml0ZS5jb25maWcudHNcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfaW1wb3J0X21ldGFfdXJsID0gXCJmaWxlOi8vL0Q6L0NvZGUvTm92ZWwtRW5naW5lL2Zyb250ZW5kL3ZpdGUuY29uZmlnLnRzXCI7Ly8vIDxyZWZlcmVuY2UgdHlwZXM9XCJ2aXRlc3RcIiAvPlxyXG5pbXBvcnQgeyBkZWZpbmVDb25maWcgfSBmcm9tICd2aXRlc3QvY29uZmlnJztcclxuaW1wb3J0IHJlYWN0IGZyb20gJ0B2aXRlanMvcGx1Z2luLXJlYWN0JztcclxuaW1wb3J0IHsgcmVzb2x2ZSB9IGZyb20gJ3BhdGgnO1xyXG5cclxuY29uc3QgZGV2UG9ydCA9IE51bWJlcihwcm9jZXNzLmVudi5WSVRFX0RFVl9QT1JUIHx8IHByb2Nlc3MuZW52LlBPUlQgfHwgMzAwMCk7XHJcblxyXG5leHBvcnQgZGVmYXVsdCBkZWZpbmVDb25maWcoe1xyXG4gIHBsdWdpbnM6IFtcclxuICAgIHJlYWN0KCksXHJcbiAgICAvLyBub2RlUG9seWZpbGxzIHJlbW92ZWQgZm9yIGRlYnVnZ2luZ1xyXG4gIF0sXHJcblxyXG4gIC8vIE1hbnVhbCBwcm9jZXNzIHBvbHlmaWxsIHZpYSBkZWZpbmVcclxuICAvLyBNSUdSQVRJT04gTk9URTogVHJhbnNpdGlvbmluZyBmcm9tIFJFQUNUX0FQUF8qIHRvIFZJVEVfKiAoVklURV8qIHRha2VzIHByZWNlZGVuY2UpXHJcbiAgLyogZGVmaW5lOiB7XHJcbiAgICBnbG9iYWw6ICdnbG9iYWxUaGlzJyxcclxuICAgICdwcm9jZXNzJzogSlNPTi5zdHJpbmdpZnkoe1xyXG4gICAgICBlbnY6IHtcclxuICAgICAgICBOT0RFX0VOVjogcHJvY2Vzcy5lbnYuTk9ERV9FTlYgfHwgJ2RldmVsb3BtZW50JyxcclxuICAgICAgICAvLyBCYWNrd2FyZCBjb21wYXRpYmlsaXR5OiBLZWVwIFJFQUNUX0FQUF8qIGZvciBleGlzdGluZyBjb2RlXHJcbiAgICAgICAgUkVBQ1RfQVBQX0FQSV9CQVNFX1VSTDogcHJvY2Vzcy5lbnYuVklURV9BUElfQkFTRV9VUkwgfHwgcHJvY2Vzcy5lbnYuUkVBQ1RfQVBQX0FQSV9CQVNFX1VSTCB8fCAnaHR0cDovL2xvY2FsaG9zdDozMDAwL3YxJyxcclxuICAgICAgICBSRUFDVF9BUFBfQVBJX1RJTUVPVVQ6IHByb2Nlc3MuZW52LlZJVEVfQVBJX1RJTUVPVVQgfHwgcHJvY2Vzcy5lbnYuUkVBQ1RfQVBQX0FQSV9USU1FT1VUIHx8ICcxMDAwMCcsXHJcbiAgICAgICAgUkVBQ1RfQVBQX0FQSV9VUkw6IHByb2Nlc3MuZW52LlZJVEVfQVBJX1VSTCB8fCBwcm9jZXNzLmVudi5SRUFDVF9BUFBfQVBJX1VSTCB8fCAnaHR0cDovL2xvY2FsaG9zdDo4MDAwJyxcclxuICAgICAgICBSRUFDVF9BUFBfRE9DS0VSOiBwcm9jZXNzLmVudi5WSVRFX0RPQ0tFUiB8fCBwcm9jZXNzLmVudi5SRUFDVF9BUFBfRE9DS0VSIHx8ICdmYWxzZScsXHJcbiAgICAgIH0sXHJcbiAgICAgIHBsYXRmb3JtOiAnYnJvd3NlcicsXHJcbiAgICAgIHZlcnNpb246ICcxOC4wLjAnLFxyXG4gICAgICB2ZXJzaW9uczogeyBub2RlOiAnMTguMC4wJyB9LFxyXG4gICAgICBuZXh0VGljazogKGNhbGxiYWNrLCAuLi5hcmdzKSA9PiBzZXRUaW1lb3V0KCgpID0+IGNhbGxiYWNrKC4uLmFyZ3MpLCAwKSxcclxuICAgICAgY3dkOiAoKSA9PiAnLycsXHJcbiAgICAgIGFyZ3Y6IFtdLFxyXG4gICAgICBzdGRvdXQ6IHsgd3JpdGU6ICgpID0+IHt9IH0sXHJcbiAgICAgIHN0ZGVycjogeyB3cml0ZTogKCkgPT4ge30gfSxcclxuICAgIH0pLFxyXG4gICAgJ3Byb2Nlc3MuZW52JzogSlNPTi5zdHJpbmdpZnkoe1xyXG4gICAgICBOT0RFX0VOVjogcHJvY2Vzcy5lbnYuTk9ERV9FTlYgfHwgJ2RldmVsb3BtZW50JyxcclxuICAgICAgLy8gQmFja3dhcmQgY29tcGF0aWJpbGl0eTogS2VlcCBSRUFDVF9BUFBfKiBmb3IgZXhpc3RpbmcgY29kZVxyXG4gICAgICBSRUFDVF9BUFBfQVBJX0JBU0VfVVJMOiBwcm9jZXNzLmVudi5WSVRFX0FQSV9CQVNFX1VSTCB8fCBwcm9jZXNzLmVudi5SRUFDVF9BUFBfQVBJX0JBU0VfVVJMIHx8ICdodHRwOi8vbG9jYWxob3N0OjMwMDAvdjEnLFxyXG4gICAgICBSRUFDVF9BUFBfQVBJX1RJTUVPVVQ6IHByb2Nlc3MuZW52LlZJVEVfQVBJX1RJTUVPVVQgfHwgcHJvY2Vzcy5lbnYuUkVBQ1RfQVBQX0FQSV9USU1FT1VUIHx8ICcxMDAwMCcsXHJcbiAgICAgIFJFQUNUX0FQUF9BUElfVVJMOiBwcm9jZXNzLmVudi5WSVRFX0FQSV9VUkwgfHwgcHJvY2Vzcy5lbnYuUkVBQ1RfQVBQX0FQSV9VUkwgfHwgJ2h0dHA6Ly9sb2NhbGhvc3Q6ODAwMCcsXHJcbiAgICAgIFJFQUNUX0FQUF9ET0NLRVI6IHByb2Nlc3MuZW52LlZJVEVfRE9DS0VSIHx8IHByb2Nlc3MuZW52LlJFQUNUX0FQUF9ET0NLRVIgfHwgJ2ZhbHNlJyxcclxuICAgIH0pLFxyXG4gICAgJ3Byb2Nlc3MuZW52Lk5PREVfRU5WJzogSlNPTi5zdHJpbmdpZnkocHJvY2Vzcy5lbnYuTk9ERV9FTlYgfHwgJ2RldmVsb3BtZW50JyksXHJcbiAgICAncHJvY2Vzcy5lbnYuUkVBQ1RfQVBQX0FQSV9CQVNFX1VSTCc6IEpTT04uc3RyaW5naWZ5KHByb2Nlc3MuZW52LlZJVEVfQVBJX0JBU0VfVVJMIHx8IHByb2Nlc3MuZW52LlJFQUNUX0FQUF9BUElfQkFTRV9VUkwgfHwgJ2h0dHA6Ly9sb2NhbGhvc3Q6MzAwMC92MScpLFxyXG4gICAgJ3Byb2Nlc3MuZW52LlJFQUNUX0FQUF9BUElfVElNRU9VVCc6IEpTT04uc3RyaW5naWZ5KHByb2Nlc3MuZW52LlZJVEVfQVBJX1RJTUVPVVQgfHwgcHJvY2Vzcy5lbnYuUkVBQ1RfQVBQX0FQSV9USU1FT1VUIHx8ICcxMDAwMCcpLFxyXG4gICAgJ3Byb2Nlc3MuZW52LlJFQUNUX0FQUF9BUElfVVJMJzogSlNPTi5zdHJpbmdpZnkocHJvY2Vzcy5lbnYuVklURV9BUElfVVJMIHx8IHByb2Nlc3MuZW52LlJFQUNUX0FQUF9BUElfVVJMIHx8ICdodHRwOi8vbG9jYWxob3N0OjgwMDAnKSxcclxuICAgICdwcm9jZXNzLmVudi5SRUFDVF9BUFBfRE9DS0VSJzogSlNPTi5zdHJpbmdpZnkocHJvY2Vzcy5lbnYuVklURV9ET0NLRVIgfHwgcHJvY2Vzcy5lbnYuUkVBQ1RfQVBQX0RPQ0tFUiB8fCAnZmFsc2UnKSxcclxuICB9LCAqL1xyXG5cclxuICAvLyBQZXJmb3JtYW5jZSBvcHRpbWl6YXRpb25zXHJcbiAgYnVpbGQ6IHtcclxuICAgIC8vIENvZGUgc3BsaXR0aW5nIGFuZCBjaHVuayBvcHRpbWl6YXRpb25cclxuICAgIHJvbGx1cE9wdGlvbnM6IHtcclxuICAgICAgb3V0cHV0OiB7XHJcbiAgICAgICAgbWFudWFsQ2h1bmtzOiB7XHJcbiAgICAgICAgICAvLyBWZW5kb3IgY2h1bmtzIGZvciBiZXR0ZXIgY2FjaGluZ1xyXG4gICAgICAgICAgdmVuZG9yOiBbJ3JlYWN0JywgJ3JlYWN0LWRvbSddLFxyXG4gICAgICAgICAgLy8gSGVhdnkgbGlicmFyaWVzIHNwbGl0IGZvciBtb2JpbGUgb3B0aW1pemF0aW9uXHJcbiAgICAgICAgICBhbmltYXRpb246IFsnZnJhbWVyLW1vdGlvbiddLFxyXG4gICAgICAgICAgdXRpbHM6IFsnYXhpb3MnLCAnc29ja2V0LmlvLWNsaWVudCcsICdsb2Rhc2gtZXMnXSxcclxuICAgICAgICAgIHF1ZXJ5OiBbJ3JlYWN0LXF1ZXJ5JywgJ0ByZWR1eGpzL3Rvb2xraXQnLCAncmVhY3QtcmVkdXgnXSxcclxuICAgICAgICAgIHh5ZmxvdzogWydAeHlmbG93L3JlYWN0J10sXHJcbiAgICAgICAgfSxcclxuICAgICAgfSxcclxuICAgIH0sXHJcbiAgICBvdXREaXI6ICdkaXN0JyxcclxuICAgIGVtcHR5T3V0RGlyOiB0cnVlLFxyXG4gICAgLy8gdGVyc2VyT3B0aW9uczoge1xyXG4gICAgLy8gICBjb21wcmVzczoge1xyXG4gICAgLy8gICAgIGRyb3BfY29uc29sZTogdHJ1ZSwgLy8gUmVtb3ZlIGNvbnNvbGUubG9nIGluIHByb2R1Y3Rpb25cclxuICAgIC8vICAgICBkcm9wX2RlYnVnZ2VyOiB0cnVlLFxyXG4gICAgLy8gICAgIGRlYWRfY29kZTogdHJ1ZSxcclxuICAgIC8vICAgICB1bnVzZWQ6IHRydWUsXHJcbiAgICAvLyAgIH0sXHJcbiAgICAvLyAgIG1hbmdsZToge1xyXG4gICAgLy8gICAgIHNhZmFyaTEwOiB0cnVlLCAvLyBGaXggU2FmYXJpIDEwKyBpc3N1ZXNcclxuICAgIC8vICAgfSxcclxuICAgIC8vIH0sXHJcbiAgfSxcclxuXHJcbiAgLy8gRGV2ZWxvcG1lbnQgc2VydmVyIG9wdGltaXphdGlvbnNcclxuICBzZXJ2ZXI6IHtcclxuICAgIHBvcnQ6IGRldlBvcnQsXHJcbiAgICBob3N0OiAnMC4wLjAuMCcsIC8vIEVuYWJsZSBuZXR3b3JrIGFjY2VzcyBmb3IgV1NMMi9Eb2NrZXJcclxuICAgIHN0cmljdFBvcnQ6IHRydWUsIC8vIEZhaWwgaWYgcG9ydCBpcyBhbHJlYWR5IGluIHVzZVxyXG4gICAgY29yczogdHJ1ZSxcclxuICAgIC8vIEhNUiBvcHRpbWl6YXRpb24gZm9yIFdTTDIgLSB1c2UgV2ViU29ja2V0IHByb3RvY29sXHJcbiAgICBobXI6IHtcclxuICAgICAgcHJvdG9jb2w6ICd3cycsXHJcbiAgICAgIGhvc3Q6ICdsb2NhbGhvc3QnLFxyXG4gICAgICBwb3J0OiBkZXZQb3J0LFxyXG4gICAgICBjbGllbnRQb3J0OiBkZXZQb3J0LCAvLyBQcmV2ZW50IHBvcnQgbWFwcGluZyBjb25mdXNpb25cclxuICAgIH0sXHJcbiAgICAvLyBXU0wyIGZpbGUgd2F0Y2hpbmcgZml4IC0gdXNlIHBvbGxpbmcgd2l0aCBmYXN0ZXIgaW50ZXJ2YWxcclxuICAgIHdhdGNoOiB7XHJcbiAgICAgIHVzZVBvbGxpbmc6IHRydWUsXHJcbiAgICAgIGludGVydmFsOiAxMDAsIC8vIEZhc3RlciBwb2xsaW5nIGZvciBiZXR0ZXIgcmVzcG9uc2l2ZW5lc3NcclxuICAgIH0sXHJcbiAgICBwcm94eToge1xyXG4gICAgICAvLyBQcm94eSAvYXBpLyogdG8gYmFja2VuZCB3aXRob3V0IHZlcnNpb25pbmdcclxuICAgICAgLy8gVXNlIDEyNy4wLjAuMSBleHBsaWNpdGx5IGZvciBXU0wyIGNvbXBhdGliaWxpdHkgKGF2b2lkIElQdjYgcmVzb2x1dGlvbiBpc3N1ZXMpXHJcbiAgICAgICcvYXBpJzoge1xyXG4gICAgICAgIHRhcmdldDogcHJvY2Vzcy5lbnYuVklURV9BUElfQkFTRV9VUkwgfHwgJ2h0dHA6Ly8xMjcuMC4wLjE6ODAwMCcsXHJcbiAgICAgICAgY2hhbmdlT3JpZ2luOiB0cnVlLFxyXG5cclxuICAgICAgICAvLyBTU0Utc3BlY2lmaWMgY29uZmlndXJhdGlvbiBmb3IgZXZlbnQgc3RyZWFtaW5nXHJcbiAgICAgICAgY29uZmlndXJlOiAocHJveHksIF9vcHRpb25zKSA9PiB7XHJcbiAgICAgICAgICBwcm94eS5vbigncHJveHlSZXEnLCAocHJveHlSZXEsIHJlcSwgX3JlcykgPT4ge1xyXG4gICAgICAgICAgICAvLyBQcmVzZXJ2ZSBTU0UgaGVhZGVycyBmb3IgZXZlbnQgc3RyZWFtIGVuZHBvaW50XHJcbiAgICAgICAgICAgIGlmIChyZXEudXJsPy5pbmNsdWRlcygnL2V2ZW50cy9zdHJlYW0nKSkge1xyXG4gICAgICAgICAgICAgIHByb3h5UmVxLnNldEhlYWRlcignQWNjZXB0JywgJ3RleHQvZXZlbnQtc3RyZWFtJyk7XHJcbiAgICAgICAgICAgICAgcHJveHlSZXEuc2V0SGVhZGVyKCdDYWNoZS1Db250cm9sJywgJ25vLWNhY2hlJyk7XHJcbiAgICAgICAgICAgICAgcHJveHlSZXEuc2V0SGVhZGVyKCdDb25uZWN0aW9uJywgJ2tlZXAtYWxpdmUnKTtcclxuICAgICAgICAgICAgfVxyXG4gICAgICAgICAgfSk7XHJcbiAgICAgICAgfSxcclxuICAgICAgfSxcclxuICAgICAgLy8gUHJveHkgL21ldGEvKiB0byBiYWNrZW5kXHJcbiAgICAgICcvbWV0YSc6IHtcclxuICAgICAgICB0YXJnZXQ6IHByb2Nlc3MuZW52LlZJVEVfQVBJX0JBU0VfVVJMIHx8ICdodHRwOi8vMTI3LjAuMC4xOjgwMDAnLFxyXG4gICAgICAgIGNoYW5nZU9yaWdpbjogdHJ1ZSxcclxuICAgICAgfSxcclxuICAgICAgLy8gUHJveHkgL2hlYWx0aCB0byBiYWNrZW5kXHJcbiAgICAgICcvaGVhbHRoJzoge1xyXG4gICAgICAgIHRhcmdldDogcHJvY2Vzcy5lbnYuVklURV9BUElfQkFTRV9VUkwgfHwgJ2h0dHA6Ly8xMjcuMC4wLjE6ODAwMCcsXHJcbiAgICAgICAgY2hhbmdlT3JpZ2luOiB0cnVlLFxyXG4gICAgICB9LFxyXG4gICAgfSxcclxuICB9LFxyXG5cclxuICAvLyBEZXBlbmRlbmN5IG9wdGltaXphdGlvblxyXG4gIG9wdGltaXplRGVwczoge1xyXG4gICAgaW5jbHVkZTogW1xyXG4gICAgICAncmVhY3QnLFxyXG4gICAgICAncmVhY3QtZG9tJyxcclxuICAgICAgJ2F4aW9zJyxcclxuICAgICAgJ2ZyYW1lci1tb3Rpb24nXHJcbiAgICBdLFxyXG4gIH0sXHJcblxyXG4gIC8vIFBhdGggcmVzb2x1dGlvblxyXG4gIHJlc29sdmU6IHtcclxuICAgIGFsaWFzOiB7XHJcbiAgICAgICdAJzogcmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMnKSxcclxuICAgICAgJ0Bjb21wb25lbnRzJzogcmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMvY29tcG9uZW50cycpLFxyXG4gICAgICAnQGhvb2tzJzogcmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMvaG9va3MnKSxcclxuICAgICAgJ0BzZXJ2aWNlcyc6IHJlc29sdmUoX19kaXJuYW1lLCAnc3JjL3NlcnZpY2VzJyksXHJcbiAgICAgICdAdHlwZXMnOiByZXNvbHZlKF9fZGlybmFtZSwgJ3NyYy90eXBlcycpLFxyXG4gICAgICAnQC9zdHlsZXMnOiByZXNvbHZlKF9fZGlybmFtZSwgJ3NyYy9zdHlsZXMnKSxcclxuICAgICAgJ0AvbGliJzogcmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMvbGliJyksXHJcbiAgICAgIC8vIE1VSSBzaGltcyBmb3IgZ3JhZHVhbCBtaWdyYXRpb24gdG8gVGFpbHdpbmRcclxuICAgICAgJ0BtdWkvbWF0ZXJpYWwnOiByZXNvbHZlKF9fZGlybmFtZSwgJ3NyYy9zaGltL211aS1tYXRlcmlhbC50c3gnKSxcclxuICAgICAgJ0BtdWkvbWF0ZXJpYWwvc3R5bGVzJzogcmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMvc2hpbS9tdWktbWF0ZXJpYWwudHN4JyksXHJcbiAgICAgICdAbXVpL21hdGVyaWFsL0JveCc6IHJlc29sdmUoX19kaXJuYW1lLCAnc3JjL3NoaW0vbXVpLW1hdGVyaWFsLnRzeCcpLFxyXG4gICAgICAnQG11aS9tYXRlcmlhbC9UeXBvZ3JhcGh5JzogcmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMvc2hpbS9tdWktbWF0ZXJpYWwudHN4JyksXHJcbiAgICAgICdAbXVpL21hdGVyaWFsL0NoaXAnOiByZXNvbHZlKF9fZGlybmFtZSwgJ3NyYy9zaGltL211aS1tYXRlcmlhbC50c3gnKSxcclxuICAgICAgJ0BtdWkvbWF0ZXJpYWwvU3RhY2snOiByZXNvbHZlKF9fZGlybmFtZSwgJ3NyYy9zaGltL211aS1tYXRlcmlhbC50c3gnKSxcclxuICAgICAgJ0BtdWkvbWF0ZXJpYWwvTGlzdCc6IHJlc29sdmUoX19kaXJuYW1lLCAnc3JjL3NoaW0vbXVpLW1hdGVyaWFsLnRzeCcpLFxyXG4gICAgICAnQG11aS9tYXRlcmlhbC9MaXN0SXRlbSc6IHJlc29sdmUoX19kaXJuYW1lLCAnc3JjL3NoaW0vbXVpLW1hdGVyaWFsLnRzeCcpLFxyXG4gICAgICAnQG11aS9tYXRlcmlhbC9MaXN0SXRlbUF2YXRhcic6IHJlc29sdmUoX19kaXJuYW1lLCAnc3JjL3NoaW0vbXVpLW1hdGVyaWFsLnRzeCcpLFxyXG4gICAgICAnQG11aS9tYXRlcmlhbC9MaXN0SXRlbVRleHQnOiByZXNvbHZlKF9fZGlybmFtZSwgJ3NyYy9zaGltL211aS1tYXRlcmlhbC50c3gnKSxcclxuICAgICAgJ0BtdWkvbWF0ZXJpYWwvQXZhdGFyJzogcmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMvc2hpbS9tdWktbWF0ZXJpYWwudHN4JyksXHJcbiAgICAgICdAbXVpL21hdGVyaWFsL0xpbmVhclByb2dyZXNzJzogcmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMvc2hpbS9tdWktbWF0ZXJpYWwudHN4JyksXHJcbiAgICAgICdAbXVpL21hdGVyaWFsL0ZhZGUnOiByZXNvbHZlKF9fZGlybmFtZSwgJ3NyYy9zaGltL211aS1tYXRlcmlhbC50c3gnKSxcclxuICAgICAgJ0BtdWkvbWF0ZXJpYWwvdXNlTWVkaWFRdWVyeSc6IHJlc29sdmUoX19kaXJuYW1lLCAnc3JjL3NoaW0vbXVpLW1hdGVyaWFsLnRzeCcpLFxyXG4gICAgICAnQG11aS9pY29ucy1tYXRlcmlhbCc6IHJlc29sdmUoX19kaXJuYW1lLCAnc3JjL3NoaW0vbXVpLWljb25zLnRzeCcpLFxyXG4gICAgICAnQG11aS9pY29ucy1tYXRlcmlhbC9NZW51JzogcmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMvc2hpbS9tdWktaWNvbnMudHN4JyksXHJcbiAgICAgICdAbXVpL2ljb25zLW1hdGVyaWFsL0FkZCc6IHJlc29sdmUoX19kaXJuYW1lLCAnc3JjL3NoaW0vbXVpLWljb25zLnRzeCcpLFxyXG4gICAgICAnQG11aS9pY29ucy1tYXRlcmlhbC9Sb2NrZXRMYXVuY2gnOiByZXNvbHZlKF9fZGlybmFtZSwgJ3NyYy9zaGltL211aS1pY29ucy50c3gnKSxcclxuICAgICAgJ0BtdWkvaWNvbnMtbWF0ZXJpYWwvTGl2ZVR2JzogcmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMvc2hpbS9tdWktaWNvbnMudHN4JyksXHJcbiAgICAgICdAbXVpL2ljb25zLW1hdGVyaWFsL0luc2lnaHRzJzogcmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMvc2hpbS9tdWktaWNvbnMudHN4JyksXHJcbiAgICAgICdAbXVpL2ljb25zLW1hdGVyaWFsL1NlY3VyaXR5JzogcmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMvc2hpbS9tdWktaWNvbnMudHN4JyksXHJcbiAgICAgICdAbXVpL2ljb25zLW1hdGVyaWFsL0xvY2tQZXJzb24nOiByZXNvbHZlKF9fZGlybmFtZSwgJ3NyYy9zaGltL211aS1pY29ucy50c3gnKSxcclxuICAgICAgJ0BtdWkvaWNvbnMtbWF0ZXJpYWwvVmlzaWJpbGl0eSc6IHJlc29sdmUoX19kaXJuYW1lLCAnc3JjL3NoaW0vbXVpLWljb25zLnRzeCcpLFxyXG4gICAgICAnQG11aS9pY29ucy1tYXRlcmlhbC9WaXNpYmlsaXR5T2ZmJzogcmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMvc2hpbS9tdWktaWNvbnMudHN4JyksXHJcbiAgICAgICdAbXVpL2ljb25zLW1hdGVyaWFsL0F1dG9TdG9yaWVzJzogcmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMvc2hpbS9tdWktaWNvbnMudHN4JyksXHJcbiAgICAgICdAbXVpL2ljb25zLW1hdGVyaWFsL0Rlc2NyaXB0aW9uJzogcmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMvc2hpbS9tdWktaWNvbnMudHN4JyksXHJcbiAgICAgICdAbXVpL2ljb25zLW1hdGVyaWFsL1BsYXlBcnJvdyc6IHJlc29sdmUoX19kaXJuYW1lLCAnc3JjL3NoaW0vbXVpLWljb25zLnRzeCcpLFxyXG4gICAgICAnQG11aS9pY29ucy1tYXRlcmlhbC9Nb3JlVmVydCc6IHJlc29sdmUoX19kaXJuYW1lLCAnc3JjL3NoaW0vbXVpLWljb25zLnRzeCcpLFxyXG4gICAgICAnQG11aS9pY29ucy1tYXRlcmlhbC9DaGVja0NpcmNsZSc6IHJlc29sdmUoX19kaXJuYW1lLCAnc3JjL3NoaW0vbXVpLWljb25zLnRzeCcpLFxyXG4gICAgICAnQG11aS9pY29ucy1tYXRlcmlhbC9SZWZyZXNoJzogcmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMvc2hpbS9tdWktaWNvbnMudHN4JyksXHJcbiAgICAgICdAbXVpL2ljb25zLW1hdGVyaWFsL1JhZGlvQnV0dG9uVW5jaGVja2VkJzogcmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMvc2hpbS9tdWktaWNvbnMudHN4JyksXHJcbiAgICAgICdAbXVpL2ljb25zLW1hdGVyaWFsL1BlcnNvbic6IHJlc29sdmUoX19kaXJuYW1lLCAnc3JjL3NoaW0vbXVpLWljb25zLnRzeCcpLFxyXG4gICAgICAnQG11aS9pY29ucy1tYXRlcmlhbC9QbGF5Q2lyY2xlJzogcmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMvc2hpbS9tdWktaWNvbnMudHN4JyksXHJcbiAgICAgICdAbXVpL2ljb25zLW1hdGVyaWFsL0dyb3Vwcyc6IHJlc29sdmUoX19kaXJuYW1lLCAnc3JjL3NoaW0vbXVpLWljb25zLnRzeCcpLFxyXG4gICAgICAnQG11aS9pY29ucy1tYXRlcmlhbC9NZW51Qm9vayc6IHJlc29sdmUoX19kaXJuYW1lLCAnc3JjL3NoaW0vbXVpLWljb25zLnRzeCcpLFxyXG4gICAgICAnQG11aS9pY29ucy1tYXRlcmlhbC9MaW5rJzogcmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMvc2hpbS9tdWktaWNvbnMudHN4JyksXHJcbiAgICAgICdAbXVpL2ljb25zLW1hdGVyaWFsL0RpdmVyc2l0eTMnOiByZXNvbHZlKF9fZGlybmFtZSwgJ3NyYy9zaGltL211aS1pY29ucy50c3gnKSxcclxuICAgICAgJ0BtdWkvaWNvbnMtbWF0ZXJpYWwvVHJlbmRpbmdGbGF0JzogcmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMvc2hpbS9tdWktaWNvbnMudHN4JyksXHJcbiAgICAgICdAbXVpL2ljb25zLW1hdGVyaWFsL0xvY2F0aW9uT24nOiByZXNvbHZlKF9fZGlybmFtZSwgJ3NyYy9zaGltL211aS1pY29ucy50c3gnKSxcclxuICAgICAgJ0BtdWkvaWNvbnMtbWF0ZXJpYWwvVGltZWxpbmUnOiByZXNvbHZlKF9fZGlybmFtZSwgJ3NyYy9zaGltL211aS1pY29ucy50c3gnKSxcclxuICAgICAgJ0BtdWkvaWNvbnMtbWF0ZXJpYWwvT3BlbkluRnVsbCc6IHJlc29sdmUoX19kaXJuYW1lLCAnc3JjL3NoaW0vbXVpLWljb25zLnRzeCcpLFxyXG4gICAgICAnQG11aS9pY29ucy1tYXRlcmlhbC9JbmZvT3V0bGluZWQnOiByZXNvbHZlKF9fZGlybmFtZSwgJ3NyYy9zaGltL211aS1pY29ucy50c3gnKSxcclxuICAgICAgJ0Avc3R5bGVzL3Rva2Vucyc6IHJlc29sdmUoX19kaXJuYW1lLCAnc3JjL3NoaW0vdG9rZW5zLnRzJyksXHJcbiAgICB9LFxyXG4gIH0sXHJcblxyXG4gIC8vIENTUyBvcHRpbWl6YXRpb25cclxuICBjc3M6IHtcclxuICAgIGRldlNvdXJjZW1hcDogdHJ1ZSxcclxuICAgIHByZXByb2Nlc3Nvck9wdGlvbnM6IHtcclxuICAgICAgc2Nzczoge1xyXG4gICAgICAgIGFkZGl0aW9uYWxEYXRhOiBgQGltcG9ydCBcIkAvc3R5bGVzL3ZhcmlhYmxlcy5zY3NzXCI7YCxcclxuICAgICAgfSxcclxuICAgIH0sXHJcbiAgfSxcclxuXHJcbiAgLy8gUHJldmlldyBjb25maWd1cmF0aW9uIHdpdGggU1BBIGZhbGxiYWNrXHJcbiAgcHJldmlldzoge1xyXG4gICAgcG9ydDogNDE3MyxcclxuICAgIGhvc3Q6IHRydWUsXHJcbiAgICBwcm94eToge1xyXG4gICAgICAvLyBQcm94eSAvYXBpLyogdG8gYmFja2VuZCBpbiBwcmV2aWV3IG1vZGVcclxuICAgICAgLy8gVXNlIDEyNy4wLjAuMSBleHBsaWNpdGx5IGZvciBXU0wyIGNvbXBhdGliaWxpdHlcclxuICAgICAgJy9hcGknOiB7XHJcbiAgICAgICAgdGFyZ2V0OiBwcm9jZXNzLmVudi5WSVRFX0FQSV9CQVNFX1VSTCB8fCAnaHR0cDovLzEyNy4wLjAuMTo4MDAwJyxcclxuICAgICAgICBjaGFuZ2VPcmlnaW46IHRydWUsXHJcbiAgICAgIH0sXHJcbiAgICAgICcvbWV0YSc6IHtcclxuICAgICAgICB0YXJnZXQ6IHByb2Nlc3MuZW52LlZJVEVfQVBJX0JBU0VfVVJMIHx8ICdodHRwOi8vMTI3LjAuMC4xOjgwMDAnLFxyXG4gICAgICAgIGNoYW5nZU9yaWdpbjogdHJ1ZSxcclxuICAgICAgfSxcclxuICAgICAgJy9oZWFsdGgnOiB7XHJcbiAgICAgICAgdGFyZ2V0OiBwcm9jZXNzLmVudi5WSVRFX0FQSV9CQVNFX1VSTCB8fCAnaHR0cDovLzEyNy4wLjAuMTo4MDAwJyxcclxuICAgICAgICBjaGFuZ2VPcmlnaW46IHRydWUsXHJcbiAgICAgIH0sXHJcbiAgICB9LFxyXG4gIH0sXHJcbiAgLy8gQXBwIHR5cGUgZm9yIFNQQSBoaXN0b3J5IGZhbGxiYWNrIHN1cHBvcnRcclxuICBhcHBUeXBlOiAnc3BhJyxcclxuXHJcbiAgLy8gVml0ZXN0IENvbmZpZ3VyYXRpb25cclxuICAgICAgdGVzdDoge1xyXG4gICAgICAgIGdsb2JhbHM6IHRydWUsXHJcbiAgICAgICAgZW52aXJvbm1lbnQ6ICdqc2RvbScsXHJcbiAgICAgICAgc2V0dXBGaWxlczogJy4vc3JjL3Rlc3Qvc2V0dXAudHMnLFxyXG4gICAgICAgIGlzb2xhdGU6IHRydWUsXHJcbiAgICAgICAgY3NzOiBmYWxzZSwgLy8gRGlzYWJsZSBDU1MgcHJvY2Vzc2luZyBmb3IgZmFzdGVyIHRlc3RzXHJcbiAgICAgICAgY292ZXJhZ2U6IHtcclxuICAgICAgICAgIHByb3ZpZGVyOiAndjgnLFxyXG4gICAgICAgICAgcmVwb3J0ZXI6IFsndGV4dCcsICdqc29uJywgJ2h0bWwnXSxcclxuICAgICAgICAgIHRocmVzaG9sZHM6IHtcclxuICAgICAgICAgICAgbGluZXM6IDgwLFxyXG4gICAgICAgICAgICBmdW5jdGlvbnM6IDgwLFxyXG4gICAgICAgICAgICBicmFuY2hlczogODAsXHJcbiAgICAgICAgICAgIHN0YXRlbWVudHM6IDgwLFxyXG4gICAgICAgICAgfSxcclxuICAgICAgICAgIGV4Y2x1ZGU6IFtcclxuICAgICAgICAgICAgJ25vZGVfbW9kdWxlcy8nLFxyXG4gICAgICAgICAgICAnc3JjL3Rlc3Qvc2V0dXAudHMnLFxyXG4gICAgICAgICAgICAnKiovKi50ZXN0LnRzeCcsXHJcbiAgICAgICAgICAgICcqKi8qLnRlc3QudHMnLFxyXG4gICAgICAgICAgICAnKiovKi5zcGVjLnRzJyxcclxuICAgICAgICAgICAgJ2Rpc3QvJyxcclxuICAgICAgICAgIF0sXHJcbiAgICAgICAgfSxcclxuICAgICAgICBmaWxlUGFyYWxsZWxpc206IGZhbHNlLCAvLyBEaXNhYmxlIHBhcmFsbGVsaXNtIHRvIHByZXZlbnQgaGFuZ3Mgb24gbGltaXRlZCByZXNvdXJjZXNcclxuXHJcbiAgICAgICAgcG9vbDogJ2ZvcmtzJywgLy8gVXNlIGZvcmtzIGluc3RlYWQgb2YgdGhyZWFkcyBmb3IgYmV0dGVyIGlzb2xhdGlvblxyXG4gICAgICAgIC8vIFZpdGVzdCA0OiBwb29sT3B0aW9ucyBtb3ZlZCB0byB0b3AtbGV2ZWxcclxuICAgICAgICBzaW5nbGVGb3JrOiB0cnVlLCAvLyBSdW4gdGVzdHMgc2VxdWVudGlhbGx5IGluIGEgc2luZ2xlIGZvcmtcclxuICAgIHRlc3RUaW1lb3V0OiAxMDAwMCxcclxuICAgIGhvb2tUaW1lb3V0OiAxMDAwMCxcclxuICAgIHJlcG9ydGVyczogWyd2ZXJib3NlJ10sXHJcbiAgICAvLyBFeGNsdWRlIGUyZSB0ZXN0cyBhbmQgaW50ZWdyYXRpb24gdGVzdHMgZnJvbSB1bml0IHRlc3QgcnVuc1xyXG4gICAgZXhjbHVkZTogWydub2RlX21vZHVsZXMnLCAnZGlzdCcsICcqKi8qLnNwZWMudHMnLCAnKiovKi5zcGVjLnRzeCcsICcqKi90ZXN0cy9pbnRlZ3JhdGlvbi8qKicsICd0ZXN0cy9pbnRlZ3JhdGlvbiddLFxyXG4gIH0sXHJcblxyXG59KTtcclxuIl0sCiAgIm1hcHBpbmdzIjogIjtBQUNBLFNBQVMsb0JBQW9CO0FBQzdCLE9BQU8sV0FBVztBQUNsQixTQUFTLGVBQWU7QUFIeEIsSUFBTSxtQ0FBbUM7QUFLekMsSUFBTSxVQUFVLE9BQU8sUUFBUSxJQUFJLGlCQUFpQixRQUFRLElBQUksUUFBUSxHQUFJO0FBRTVFLElBQU8sc0JBQVEsYUFBYTtBQUFBLEVBQzFCLFNBQVM7QUFBQSxJQUNQLE1BQU07QUFBQTtBQUFBLEVBRVI7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBLEVBd0NBLE9BQU87QUFBQTtBQUFBLElBRUwsZUFBZTtBQUFBLE1BQ2IsUUFBUTtBQUFBLFFBQ04sY0FBYztBQUFBO0FBQUEsVUFFWixRQUFRLENBQUMsU0FBUyxXQUFXO0FBQUE7QUFBQSxVQUU3QixXQUFXLENBQUMsZUFBZTtBQUFBLFVBQzNCLE9BQU8sQ0FBQyxTQUFTLG9CQUFvQixXQUFXO0FBQUEsVUFDaEQsT0FBTyxDQUFDLGVBQWUsb0JBQW9CLGFBQWE7QUFBQSxVQUN4RCxRQUFRLENBQUMsZUFBZTtBQUFBLFFBQzFCO0FBQUEsTUFDRjtBQUFBLElBQ0Y7QUFBQSxJQUNBLFFBQVE7QUFBQSxJQUNSLGFBQWE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUEsRUFZZjtBQUFBO0FBQUEsRUFHQSxRQUFRO0FBQUEsSUFDTixNQUFNO0FBQUEsSUFDTixNQUFNO0FB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
