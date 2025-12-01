// @ts-check
import { defineConfig } from "astro/config";

import react from "@astrojs/react";
import tailwindcss from "@tailwindcss/vite";

const config = {
  local: {
    SITE_URL: "http://localhost:4321",
    BASE_PATH: "",
  },
  production: {
    SITE_URL: "https://esa-apex.github.io/",
    BASE_PATH: "/apex_document_repo/",
  },
};

const buildTarget = (process.env.BUILD_TARGET ??
  "local") as keyof typeof config;

const { SITE_URL, BASE_PATH } = config[buildTarget];

// https://astro.build/config
export default defineConfig({
  site: SITE_URL,
  base: BASE_PATH,
  integrations: [react()],

  vite: {
    plugins: [tailwindcss()],
  },
});
