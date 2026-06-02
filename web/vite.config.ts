import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // proxy API calls to the FastAPI backend during dev
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
