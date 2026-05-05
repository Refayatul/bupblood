/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html', // Include all HTML files inside the templates directory
    './static/css/**/*.css', // Include your custom CSS files
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require('daisyui'), // DaisyUI for pre-built UI components
  ],
}
