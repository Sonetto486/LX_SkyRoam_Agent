/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        // 主色调 - Notion 紫色系
        primary: {
          DEFAULT: '#5645d4',
          pressed: '#4534b3',
          deep: '#3a2a99',
          on: '#ffffff',
        },
        // 品牌深色
        'brand-navy': {
          DEFAULT: '#0a1530',
          deep: '#070f24',
          mid: '#1a2a52',
        },
        // 链接蓝
        'link-blue': {
          DEFAULT: '#0075de',
          pressed: '#005bab',
        },
        // 品牌彩色
        brand: {
          pink: '#ff64c8',
          'pink-deep': '#a02e6d',
          orange: '#dd5b00',
          'orange-deep': '#793400',
          purple: '#7b3ff2',
          'purple-300': '#d6b6f6',
          'purple-800': '#391c57',
          teal: '#2a9d99',
          green: '#1aae39',
          yellow: '#f5d75e',
          brown: '#523410',
        },
        // 卡片彩色背景
        'card-tint': {
          peach: '#ffe8d4',        // 美食/餐厅
          rose: '#fde0ec',         // 酒店/住宿
          mint: '#d9f3e1',         // 景点/自然
          lavender: '#e6e0f5',     // 文化/艺术
          sky: '#dcecfa',          // 航班/交通
          yellow: '#fef7d6',       // 攻略/笔记
          'yellow-bold': '#f9e79f', // AI助手/高亮
          cream: '#f8f5e8',
          gray: '#f0eeec',
        },
        // 基础表面色
        canvas: '#ffffff',
        surface: '#f6f5f4',
        'surface-soft': '#fafaf9',
        // 边框色
        hairline: {
          DEFAULT: '#e5e3df',
          soft: '#ede9e4',
          strong: '#c8c4be',
        },
        // 文字色
        ink: {
          deep: '#000000',
          DEFAULT: '#1a1a1a',
        },
        charcoal: '#37352f',
        slate: '#5d5b54',
        steel: '#787671',
        stone: '#a4a097',
        muted: '#bbb8b1',
        // 深色背景文字
        'on-dark': '#ffffff',
        'on-dark-muted': '#a4a097',
        // 语义色
        semantic: {
          success: '#1aae39',
          warning: '#dd5b00',
          error: '#e03131',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', 'Helvetica', 'Arial', 'sans-serif'],
      },
      fontSize: {
        'hero': ['80px', { lineHeight: '1.05', letterSpacing: '-2px', fontWeight: '600' }],
        'display-lg': ['56px', { lineHeight: '1.10', letterSpacing: '-1px', fontWeight: '600' }],
        'heading-1': ['48px', { lineHeight: '1.15', letterSpacing: '-0.5px', fontWeight: '600' }],
        'heading-2': ['36px', { lineHeight: '1.20', letterSpacing: '-0.5px', fontWeight: '600' }],
        'heading-3': ['28px', { lineHeight: '1.25', fontWeight: '600' }],
        'heading-4': ['22px', { lineHeight: '1.30', fontWeight: '600' }],
        'heading-5': ['18px', { lineHeight: '1.40', fontWeight: '600' }],
        'subtitle': ['18px', { lineHeight: '1.50', fontWeight: '400' }],
        'body-md': ['16px', { lineHeight: '1.55', fontWeight: '400' }],
        'body-sm': ['14px', { lineHeight: '1.50', fontWeight: '400' }],
        'caption': ['13px', { lineHeight: '1.40', fontWeight: '400' }],
        'micro': ['12px', { lineHeight: '1.40', fontWeight: '500' }],
      },
      borderRadius: {
        'xs': '4px',
        'sm': '6px',
        'md': '8px',
        'lg': '12px',
        'xl': '16px',
        'xxl': '20px',
        'xxxl': '24px',
      },
      spacing: {
        'xxs': '4px',
        'xs': '8px',
        'sm': '12px',
        'md': '16px',
        'lg': '20px',
        'xl': '24px',
        'xxl': '32px',
        'xxxl': '40px',
        'section-sm': '48px',
        'section': '64px',
        'section-lg': '96px',
        'hero': '120px',
      },
      boxShadow: {
        '1': 'rgba(15, 15, 15, 0.04) 0px 1px 2px 0px',
        '2': 'rgba(15, 15, 15, 0.08) 0px 4px 12px 0px',
        '3': 'rgba(15, 15, 15, 0.20) 0px 24px 48px -8px',
        '4': 'rgba(15, 15, 15, 0.16) 0px 16px 48px -8px',
        'card': 'rgba(15, 15, 15, 0.08) 0px 4px 12px 0px',
        'mockup': 'rgba(15, 15, 15, 0.20) 0px 24px 48px -8px',
      },
      maxWidth: {
        'container': '1280px',
      },
      transitionDuration: {
        'fast': '150ms',
        'normal': '200ms',
        'slow': '300ms',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-soft': 'pulseSoft 1.5s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
      },
    },
  },
  plugins: [],
}
