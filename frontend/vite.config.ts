import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [vue()],
    base: '/',

    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
        vue: 'vue/dist/vue.esm-bundler.js'
      }
    },

    server: {
      port: parseInt(env.VITE_DEV_PORT || '3000'),
      open: false,
      host: env.VITE_DEV_HOST || 'localhost',
      proxy: {
        '/api': {
          target: env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
        '/auth': {
          target: env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        }
      }
    },

    build: {
      outDir: 'dist',
      sourcemap: false,
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ['vue', 'vue-router', 'pinia'],
            bootstrap: ['bootstrap', 'bootstrap-vue-next'],
            charts: ['chart.js', 'vue-chartjs'],
            icons: [
              '@fortawesome/fontawesome-svg-core',
              '@fortawesome/free-solid-svg-icons',
              '@fortawesome/vue-fontawesome'
            ]
          }
        }
      }
    },

    css: {
      preprocessorOptions: {
        scss: {
          silenceDeprecations: [
            'legacy-js-api',
            'import',
            'global-builtin',
            'mixed-decls',
            'color-functions',
            'slash-div'
          ]
        }
      }
    },

    optimizeDeps: {
      include: [
        'vue',
        'vue-router',
        'pinia',
        'bootstrap',
        'bootstrap-vue-next',
        'chart.js',
        'vue-chartjs',
        '@fortawesome/fontawesome-svg-core',
        '@fortawesome/free-solid-svg-icons',
        '@fortawesome/vue-fontawesome'
      ]
    },

    define: {
      __VUE_OPTIONS_API__: true,
      __VUE_PROD_DEVTOOLS__: false,
      __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false
    }
  }
})
