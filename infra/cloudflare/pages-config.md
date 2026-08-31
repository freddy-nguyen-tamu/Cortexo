# Cortexo Cloudflare Pages deployment (blueprint section 80).
# Build settings are configured in the Cloudflare dashboard; this file is the
# canonical one-line reminder and the _headers/_redirects live here too.

# Build command
npm ci && npm run build

# On the dashboard:
#   Framework preset : Vite
#   Build command    : (above)
#   Output directory : dist
#   Root directory   : apps/web-vue
#
# Environment variables (NO secrets belong in frontend env vars):
#   VITE_API_BASE_URL=https://YOUR-API-HOST/api

# Local preview:
#   VITE_API_BASE_URL=http://localhost:8080/api npm run dev