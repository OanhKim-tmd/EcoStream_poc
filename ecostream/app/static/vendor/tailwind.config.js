// Build config for the offline stylesheet (ecostream/app/static/vendor/app.css).
// Mirrors the inline config previously passed to the Tailwind Play CDN in index.html.
// Rebuild after changing classes in the HTML/JS files:
//   npx tailwindcss@3.4.17 -c ecostream/app/static/vendor/tailwind.config.js \
//       -i ecostream/app/static/vendor/input.css -o ecostream/app/static/vendor/app.css --minify
module.exports = {
  content: [
    "./ecostream/app/static/index.html",
    "./ecostream/app/static/monitor.html",
    "./ecostream/app/static/monitor.js",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
      colors: {
        brand: {
          50: "#edf5e9",
          100: "#dff4cc",
          200: "#cce5c0",
          500: "#2a5c47",
          600: "#184e42",
          700: "#003c33",
          800: "#002820",
          900: "#091710",
        },
      },
    },
  },
  plugins: [],
};
