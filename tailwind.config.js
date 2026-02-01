/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app_connaissance/templates/**/*.html",
    "./app_connaissance/**/*.py",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "pop-in": {
          "0%": { opacity: "0", transform: "scale(0.98)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        "floaty": {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" },
        },
        "glow": {
          "0%, 100%": { filter: "drop-shadow(0 0 0 rgba(0,0,0,0))" },
          "50%": { filter: "drop-shadow(0 10px 30px rgba(99,102,241,0.25))" },
        },
      },
      animation: {
        "fade-in": "fade-in 420ms ease-out both",
        "pop-in": "pop-in 280ms ease-out both",
        "floaty": "floaty 6s ease-in-out infinite",
        "glow": "glow 4.5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
}

