/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{astro,html,js,ts,jsx,tsx}",
    "./public/docs/**/*.yml",
    "./public/docs/**/*.yaml",
  ],
  theme: {
    extend: {
      colors: {
        dochub: {
          DEFAULT: "#13b8a6",
          accent: "#1ea99f",
        },
      },
    },
  },
  plugins: [],
};
