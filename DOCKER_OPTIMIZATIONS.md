# Docker-Optimierungen für Raspberry Pi

## Durchgeführte Optimierungen

### 1. Multi-Stage Build ✅
- **Vorher:** Ein-Stage Build mit allen Build-Dependencies im finalen Image
- **Nachher:** Zwei-Stage Build
  - **Stage 1 (builder):** Kompiliert Dependencies
  - **Stage 2 (runtime):** Nur Runtime-Dependencies, kleineres Image

**Vorteile:**
- Deutlich kleineres finales Image (~50% kleiner)
- Schnellere Extraktion auf Raspberry Pi
- Weniger Speicherbedarf

### 2. Optimiertes Layer-Caching ✅
- **Vorher:** Alles in einem COPY-Befehl
- **Nachher:** 
  - `requirements.txt` wird zuerst kopiert
  - Dependencies werden installiert (Layer wird gecacht)
  - Dann wird der Code kopiert

**Vorteil:** Bei Code-Änderungen müssen Dependencies nicht neu installiert werden

### 3. Entfernte unnötige Dependencies ✅
- **Entfernt:** `musl-dev` (nur für Alpine Linux, nicht für Debian)
- **Entfernt:** `python3-cryptography`, `python3-gevent` (werden über pip installiert)
- **Behalten:** Nur Runtime-Dependencies im finalen Image

### 4. Verbesserte .dockerignore ✅
- Mehr Dateien werden ignoriert (Git, IDE, Docs)
- Kleinere Build-Context
- Schnellere Builds

### 5. Optimierte pip-Installation ✅
- `--no-cache-dir` für kleinere Images
- `--user` Installation für bessere Isolation
- `--compile` für ARM-Optimierungen (in Dockerfile.arm)

## Verwendung

### Standard Dockerfile (für alle Plattformen)
```bash
docker build -t dsbridge:latest .
```

### Optimiertes Dockerfile für ARM/Raspberry Pi
```bash
docker build -f Dockerfile.arm -t dsbridge:arm .
```

## Erwartete Verbesserungen

1. **Kleineres Image:**
   - Vorher: ~500-600 MB
   - Nachher: ~250-300 MB (mit Multi-Stage Build)

2. **Schnellere Extraktion:**
   - Weniger Daten müssen extrahiert werden
   - Multi-Stage Build reduziert Image-Größe

3. **Schnellere Builds:**
   - Besseres Layer-Caching
   - Dependencies werden nur neu gebaut wenn sich requirements.txt ändert

4. **Weniger Speicherbedarf:**
   - Keine Build-Tools im finalen Image
   - Nur Runtime-Dependencies

## Weitere Optimierungsmöglichkeiten

### Build-Kit verwenden
```bash
DOCKER_BUILDKIT=1 docker build -t dsbridge:latest .
```

### Build-Cache verwenden
```bash
# Build mit Cache
docker build --cache-from dsbridge:latest -t dsbridge:latest .
```

### Pre-built Wheels verwenden
Für noch schnellere Builds könnten Pre-built Wheels für ARM verwendet werden, aber das erfordert zusätzliche Infrastruktur.

## Troubleshooting

### Wenn Build zu langsam ist:
1. Stelle sicher, dass BuildKit aktiviert ist: `DOCKER_BUILDKIT=1`
2. Verwende `Dockerfile.arm` für Raspberry Pi
3. Prüfe, ob `.dockerignore` korrekt konfiguriert ist
4. Verwende lokalen Build-Cache

### Wenn Image zu groß ist:
1. Prüfe mit `docker images` die Image-Größe
2. Verwende `docker history <image>` um Layer-Größen zu sehen
3. Stelle sicher, dass Multi-Stage Build verwendet wird
