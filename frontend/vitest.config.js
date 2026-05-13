import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    include: ["tests-dom/**/*.test.{js,jsx,ts,tsx}"],
    setupFiles: ["tests-dom/setup.js"],
  },
});
