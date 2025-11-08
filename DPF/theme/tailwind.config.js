// Localizat în: theme/tailwind.config.js
module.exports = {
    content: [
        // Calea relativă la 'theme/': mergi sus (../) și intră în 'templates/'
        '../templates/**/*.html',
    ],
    theme: {
        extend: {
            colors: {
                'primary-dark': '#2B0B3F',
                'primary': '#7443A3',
                'primary-light': '#F4F1F9',
                'text-dark': '#2F1D1D',
                'accent': '#76213A',
            },
            fontFamily: {
                'sans': ['Helvetica', 'Arial', 'sans-serif'],
                'serif': ['"Source Serif Pro"', 'Georgia', 'serif'],
            },
        },
    },
    // Fără 'plugins'
}