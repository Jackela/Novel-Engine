import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import locale files
import enTranslations from './locales/en.json';
import zhTranslations from './locales/zh.json';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: {
        translation: enTranslations
      },
      zh: {
        translation: zhTranslations
      }
    },
    
    // Default language fallback
    fallbackLng: 'en',
    
    // Language detection settings
    detection: {
      order: ['navigator', 'htmlTag', 'path', 'subdomain'],
      caches: ['localStorage']
    },
    
    // Interpolation settings
    interpolation: {
      escapeValue: false, // React already does escaping
      formatSeparator: ',',
      format: function(value, format) {
        if (format === 'uppercase') return value.toUpperCase();
        if (format === 'lowercase') return value.toLowerCase();
        return value;
      }
    },
    
    // Debug mode for development
    debug: process.env.NODE_ENV === 'development',
    
    // React settings
    react: {
      useSuspense: false
    }
  });

export default i18n;