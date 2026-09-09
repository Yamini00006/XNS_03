/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#dbe7ff",
          500: "#3b5bdb",
          600: "#2f4bc7",
          700: "#263ea3",
        },
      },
    },
  },
  plugins: [],
};
