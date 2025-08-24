# Docker

Kreuzberg provides official Docker images for easy deployment and containerized usage.

## Image Variants

Docker images are available on [Docker Hub](https://hub.docker.com/r/goldziher/kreuzberg):

### Image Sizes Overview

| Image            | Compressed Size | Uncompressed | What's Included                 |
| ---------------- | --------------- | ------------ | ------------------------------- |
| `latest`         | 258MB           | 1.2GB        | Core + Tesseract OCR            |
| `latest-paddle`  | 837MB           | ~3GB         | Core + PaddleOCR models         |
| `latest-gmft`    | 8.0GB           | ~15GB        | Core + Table Transformer models |
| `latest-easyocr` | 8.2GB           | ~15GB        | Core + EasyOCR language models  |
| `latest-all`     | 9.0GB           | ~18GB        | Everything (testing only)       |

> **Note**: Large images (GMFT, EasyOCR) include pre-trained deep learning models which account for most of the size. These models are necessary for their advanced capabilities.

### Core Image

- **Image**: `goldziher/kreuzberg:latest`
- **Size**: 258MB compressed (1.2GB when pulled)
- **Includes**: Base library + API server + Tesseract OCR
- **Use Case**: Basic text extraction, simple OCR tasks
- **Limitations**: No chunking, language detection, entity extraction, or alternative OCR backends

### OCR Backend Variants

- **PaddleOCR**: `goldziher/kreuzberg:latest-paddle`

    - **Size**: 837MB compressed
    - Lightweight deep learning OCR
    - Good balance between size and accuracy
    - Supports multiple languages with smaller models

- **EasyOCR**: `goldziher/kreuzberg:latest-easyocr`

    - **Size**: 8.2GB compressed
    - Includes models for 80+ languages
    - Better accuracy for complex layouts and handwriting
    - Size is due to comprehensive language model collection

### Table Extraction

- **GMFT**: `goldziher/kreuzberg:latest-gmft`
    - **Size**: 8.0GB compressed
    - Advanced table detection and extraction from PDFs
    - Uses Microsoft's Table Transformer models
    - Large size due to transformer-based deep learning models

### All-in-One (Testing Only)

- **Image**: `goldziher/kreuzberg:latest-all`
- **Size**: 9.0GB compressed
- **⚠️ WARNING**: For testing only, NOT for production use
- **Includes ALL features**:
    - ✅ API server with OpenTelemetry instrumentation
    - ✅ Text chunking (semantic-text-splitter)
    - ✅ CLI with rich output
    - ✅ PDF encryption/decryption support
    - ✅ Document classification (deep-translator, pandas)
    - ✅ Language detection (fast-langdetect)
    - ✅ Entity extraction (KeyBERT, spaCy)
    - ✅ Table extraction (GMFT with Table Transformer)
    - ✅ ALL OCR backends (Tesseract, EasyOCR, PaddleOCR)
    - ✅ Email parsing support (mailparse)
- **Why not production?**:
    - Unnecessarily large for most use cases
    - Includes redundant models (both EasyOCR and PaddleOCR)
    - Slower container startup time
    - Higher memory footprint (~4GB+ RAM needed)

## Quick Start

### Basic Usage

```bash
# Pull and run the core image
docker pull goldziher/kreuzberg:latest
docker run -p 8000:8000 goldziher/kreuzberg:latest

# Extract text from a document
curl -X POST http://localhost:8000/extract \
  -F "data=@document.pdf"
```

### With Cache Volume

```bash
# Create cache directory
mkdir -p kreuzberg-cache

# Run with persistent cache
docker run -p 8000:8000 \
  -v "$(pwd)/kreuzberg-cache:/app/.kreuzberg" \
  goldziher/kreuzberg:latest
```

## Customizing Docker Images

For production, create a custom image with only the features you need:

### Example 1: Core + Chunking Support

```dockerfile
FROM goldziher/kreuzberg:latest

USER root

# Install only chunking dependency
RUN uv pip install --python /app/.venv/bin/python semantic-text-splitter

USER appuser
```

Build and run:

```bash
# Build the image
docker build -t kreuzberg-chunking .

# Run with external configuration
docker run -p 8000:8000 \
  -v "$(pwd)/kreuzberg.toml:/app/kreuzberg.toml:ro" \
  -v "$(pwd)/cache:/app/.kreuzberg" \
  kreuzberg-chunking
```

### Example 2: Core + Language Detection + Chunking

```dockerfile
FROM goldziher/kreuzberg:latest

USER root

# Install specific features
RUN uv pip install --python /app/.venv/bin/python \
    semantic-text-splitter \
    fast-langdetect

USER appuser
```

Create configuration file `kreuzberg.toml`:

```toml
chunk_content = true
auto_detect_language = true
max_chars = 2000
max_overlap = 100
```

Run with:

```bash
docker run -p 8000:8000 \
  -v "$(pwd)/kreuzberg.toml:/app/kreuzberg.toml:ro" \
  -v "$(pwd)/cache:/app/.kreuzberg" \
  kreuzberg-multilang
```

### Example 3: Core + PaddleOCR (Custom Build)

```dockerfile
FROM goldziher/kreuzberg:latest

USER root

# Install PaddleOCR dependencies
RUN uv pip install --python /app/.venv/bin/python \
    paddleocr \
    paddlepaddle

USER appuser
```

Run with PaddleOCR backend:

```bash
docker run -p 8000:8000 \
  -e KREUZBERG_OCR_BACKEND=paddleocr \
  -v "$(pwd)/cache:/app/.kreuzberg" \
  kreuzberg-paddle
```

### Example 4: Optimized Production Build

```dockerfile
FROM goldziher/kreuzberg:latest

USER root

# Install only the features you need
RUN uv pip install --python /app/.venv/bin/python \
    semantic-text-splitter \
    fast-langdetect && \
    # Clean up cache to reduce image size
    rm -rf /root/.cache/uv

USER appuser

# Set production environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
```

Deploy with Docker Compose:

```yaml
services:
  kreuzberg:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - "./config/kreuzberg.toml:/app/kreuzberg.toml:ro"
      - "kreuzberg-cache:/app/.kreuzberg"
    environment:
      - PYTHONUNBUFFERED=1
      - KREUZBERG_CACHE_DIR=/app/.kreuzberg
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  kreuzberg-cache:
```

## Docker Compose

### Production Setup

```yaml
services:
  kreuzberg:
    image: goldziher/kreuzberg:latest  # Or your custom image
    ports:
      - "8000:8000"
    volumes:
      - "./kreuzberg-cache:/app/.kreuzberg"  # Persistent cache
      - "./kreuzberg.toml:/app/kreuzberg.toml:ro"  # Configuration
    environment:
      - PYTHONUNBUFFERED=1
      - KREUZBERG_CACHE_DIR=/app/.kreuzberg
      # Cache configuration
      - KREUZBERG_OCR_CACHE_SIZE_MB=500
      - KREUZBERG_DOCUMENT_CACHE_SIZE_MB=1000
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Configuration

### Using Configuration Files

Create `kreuzberg.toml`:

```toml
force_ocr = false
chunk_content = true  # Requires semantic-text-splitter
extract_tables = false  # Requires gmft
ocr_backend = "tesseract"

[tesseract]
language = "eng"
psm = 6
```

Mount the configuration:

```bash
docker run -p 8000:8000 \
  -v "$(pwd)/kreuzberg.toml:/app/kreuzberg.toml" \
  goldziher/kreuzberg:latest
```

### Environment Variables

**Cache Configuration:**

- `KREUZBERG_CACHE_DIR`: Cache directory (default: `/app/.kreuzberg`)
- `KREUZBERG_OCR_CACHE_SIZE_MB`: OCR cache size limit (default: `500`)
- `KREUZBERG_DOCUMENT_CACHE_SIZE_MB`: Document cache size limit (default: `1000`)

**Runtime Configuration:**

- `PYTHONUNBUFFERED=1`: Ensures proper logging output
- `PYTHONDONTWRITEBYTECODE=1`: Prevents .pyc file creation

## Production Deployment

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kreuzberg-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: kreuzberg-api
  template:
    metadata:
      labels:
        app: kreuzberg-api
    spec:
      containers:
      - name: kreuzberg
        image: your-registry/kreuzberg-custom:latest
        ports:
        - containerPort: 8000
        volumeMounts:
        - name: cache
          mountPath: /app/.kreuzberg
        - name: config
          mountPath: /app/kreuzberg.toml
          subPath: kreuzberg.toml
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
      volumes:
      - name: cache
        emptyDir: {}
      - name: config
        configMap:
          name: kreuzberg-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: kreuzberg-config
data:
  kreuzberg.toml: |
    chunk_content = false
    ocr_backend = "tesseract"
    [tesseract]
    language = "eng"
```

### With nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # File upload settings
        client_max_body_size 100M;
        proxy_read_timeout 300s;
    }

    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
```

## Resource Requirements

| Variant     | CPU      | Memory | Storage |
| ----------- | -------- | ------ | ------- |
| Core        | 1+ cores | 512MB+ | 1GB     |
| + Chunking  | 1+ cores | 1GB+   | 1GB     |
| + PaddleOCR | 2+ cores | 2GB+   | 2GB     |
| + EasyOCR   | 2+ cores | 4GB+   | 10GB    |
| + GMFT      | 2+ cores | 4GB+   | 10GB    |

## Troubleshooting

### Common Issues

#### Permission Denied on Cache Directory

```bash
# Fix: Ensure proper ownership
docker run --rm -v "$(pwd)/cache:/app/.kreuzberg" --user root \
  goldziher/kreuzberg:latest \
  chown -R 999:999 /app/.kreuzberg
```

#### Missing Dependencies Error

```bash
# Solution: Use appropriate image variant or build custom image
# For chunking: Install semantic-text-splitter
# For language detection: Install fast-langdetect
```

#### Out of Memory

- Increase Docker memory allocation
- Use a smaller OCR engine (Tesseract instead of EasyOCR)
- Disable unnecessary features

### Debugging

```bash
# Check logs
docker logs <container-id>

# Shell access
docker exec -it <container-id> /bin/bash

# Test extraction
docker exec <container-id> python3 -c "
from kreuzberg import extract_file_sync
result = extract_file_sync('/path/to/file.pdf')
print(result.content[:100])
"
```

## Security Considerations

- Runs as non-root user (`appuser`) by default
- No external API calls or cloud dependencies
- Process files locally within the container
- Use read-only mounts where possible (`:ro`)
- Consider adding authentication for production use
