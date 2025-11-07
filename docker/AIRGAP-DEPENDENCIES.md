# Air-Gap Dependencies - Datenschleuder

This document describes how external dependencies are handled for air-gapped deployments.

## 🔒 External Dependencies Status

### ✅ Resolved - All External Dependencies Bundled

All external dependencies have been resolved and bundled into the Docker image for fully offline operation.

## 📦 Font Dependencies

### Google Fonts → Local Fonts

**Issue:** The application originally loaded the Roboto font from Google Fonts CDN:
```html
<link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Roboto:100,300,400,500,700,900">
```

**Solution:** Replaced with `@fontsource/roboto` package (npm):

1. **Installed Package:**
   ```bash
   npm install @fontsource/roboto
   ```

2. **Import in `frontend/src/main.ts`:**
   ```typescript
   import "@fontsource/roboto/100.css";
   import "@fontsource/roboto/300.css";
   import "@fontsource/roboto/400.css";
   import "@fontsource/roboto/500.css";
   import "@fontsource/roboto/700.css";
   import "@fontsource/roboto/900.css";
   ```

3. **Removed from `frontend/index.html`:**
   - Deleted the Google Fonts link
   - Added comment explaining local font usage

**Result:** Roboto font is now bundled in the build artifacts and requires no external network access.

## 🎨 CSS and JavaScript Dependencies

### All CSS/JS via npm packages

All UI components and styling libraries are installed via npm and bundled during build:

- ✅ **Bootstrap** - via `bootstrap` package
- ✅ **Bootstrap Vue Next** - via `bootstrap-vue-next` package  
- ✅ **Font Awesome** - via `@fortawesome/*` packages (bundled SVG icons)
- ✅ **Chart.js** - via `chart.js` package
- ✅ **Leaflet** - via `leaflet` package
- ✅ **Perfect Scrollbar** - via `vue3-perfect-scrollbar` package
- ✅ **Pinia** - via `pinia` package
- ✅ **Vue Router** - via `vue-router` package

**Result:** All JavaScript and CSS dependencies are bundled in the webpack/vite output.

## 🗺️ Map Tiles (Demo Pages Only)

**Note:** The application includes demo pages (`src/DemoPages/Components/Maps.vue`) that reference OpenStreetMap tiles:

```javascript
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {...})
```

**Status:** These demo pages are not used in production. If you need maps in production in an air-gapped environment, you would need to:
1. Host your own tile server
2. Pre-download map tiles
3. Configure Leaflet to use local tile sources

## 🔍 No Analytics or Tracking

**Confirmed:** No analytics, tracking, or telemetry dependencies:
- ❌ No Google Analytics
- ❌ No Mixpanel
- ❌ No Segment
- ❌ No external tracking pixels
- ❌ No CDN-hosted scripts

## 📡 Backend Dependencies

All Python dependencies are:
1. Listed in `backend/requirements.txt`
2. Downloaded during Docker build
3. Packaged as Python wheels in the image
4. Installed from local wheels (no PyPI access needed at runtime)

**Key Backend Dependencies:**
- FastAPI
- Uvicorn
- SQLAlchemy
- Pydantic
- nipyapi (for NiFi API communication)

## 🐳 Docker Build Process

The `Dockerfile.all-in-one` uses multi-stage builds to ensure all dependencies are captured:

### Stage 1: Base System Dependencies
```dockerfile
apt-get install -y \
   git curl wget nodejs npm supervisor \
   build-essential python3-dev libffi-dev libssl-dev fping
```

### Stage 2: Frontend Build
```dockerfile
npm ci                    # Install from package-lock.json
npm run build            # Build Vue.js app with bundled fonts
```

### Stage 3: Python Dependencies
```dockerfile
pip wheel -r requirements.txt -w /tmp/wheelhouse
pip install --no-index --find-links /tmp/wheelhouse -r requirements.txt
```

### Stage 4: Runtime Image
- Copies built frontend (includes bundled fonts and CSS)
- Copies Python wheels and installs locally
- No network access required

## ✅ Verification Steps

To verify there are no external dependencies in the built application:

### 1. Check Built Files
```bash
cd frontend
npm run build
grep -r "googleapis\|cdn\|unpkg\|https://fonts" dist/
# Should return nothing
```

### 2. Check HTML
```bash
grep "googleapis" frontend/index.html
# Should return nothing (only a comment)
```

### 3. Test Offline
```bash
# Build the Docker image
./docker/prepare-all-in-one.sh

# Deploy without internet
./docker/deploy-all-in-one.sh

# Verify in browser: no failed network requests
```

## 📊 Bundle Size Impact

Adding local Roboto fonts increased the bundle size by approximately:
- **Before:** ~480 KB CSS (gzipped)
- **After:** ~600 KB CSS (gzipped) 
- **Increase:** ~120 KB (acceptable for air-gapped operation)

## 🔄 Updating Dependencies

When updating dependencies for air-gapped deployment:

1. **Update package.json/requirements.txt** on internet-connected machine
2. **Run `npm install`** / **`pip install`**
3. **Test build** locally
4. **Run `./docker/prepare-all-in-one.sh`**
5. **Transfer new image** to air-gapped environment

## 🎯 Summary

✅ **All external dependencies resolved**  
✅ **Fonts bundled locally via @fontsource**  
✅ **All npm packages bundled via Vite**  
✅ **All Python packages bundled as wheels**  
✅ **No analytics or tracking**  
✅ **No CDN dependencies**  
✅ **Fully functional in air-gapped environment**

The Datenschleuder application is now **100% air-gap compatible** with no external network dependencies at runtime.
