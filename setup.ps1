# ============================================
# Voicemod LoL - Setup Script
# Ejecutar: .\setup.ps1
# ============================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Voicemod LoL - Instalacion" -ForegroundColor Cyan
Write-Host "  Modulador de Voz Virtual con IA" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar Python
Write-Host "[1/5] Verificando Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  Python encontrado: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Python no encontrado. Instala Python 3.10+" -ForegroundColor Red
    exit 1
}

# Verificar version de Python
$versionMatch = [regex]::Match($pythonVersion, "(\d+)\.(\d+)")
$major = [int]$versionMatch.Groups[1].Value
$minor = [int]$versionMatch.Groups[2].Value

$useMinimal = $false
if ($major -eq 3 -and $minor -ge 13) {
    Write-Host ""
    Write-Host "  Python 3.$minor detectado" -ForegroundColor Yellow
    Write-Host "  Se instalara version MINIMA (GUI + audio basico)" -ForegroundColor Yellow
    Write-Host "  Para funcionalidad ML completa, usa Python 3.10-3.12" -ForegroundColor Yellow
    Write-Host ""
    $useMinimal = $true
}

# Crear virtualenv
Write-Host ""
Write-Host "[2/5] Creando entorno virtual..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "  Entorno virtual creado." -ForegroundColor Green
} else {
    Write-Host "  Entorno virtual ya existe." -ForegroundColor Green
}

# Activar entorno
Write-Host ""
Write-Host "[3/5] Activando entorno virtual..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Actualizar pip
Write-Host ""
Write-Host "[4/5] Actualizando pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Instalar dependencias
Write-Host ""
Write-Host "[5/5] Instalando dependencias..." -ForegroundColor Yellow
Write-Host "  (Esto puede tomar varios minutos)" -ForegroundColor Gray

if ($useMinimal) {
    Write-Host "  Instalando dependencias minimas..." -ForegroundColor Yellow
    pip install -r requirements-core.txt
} else {
    # Instalar PyTorch primero (con CUDA si hay GPU)
    Write-Host "  Instalando PyTorch..." -ForegroundColor Gray
    $hasGPU = nvidia-smi 2>&1 | Select-String "NVIDIA" | Select-Object -First 1
    if ($hasGPU) {
        Write-Host "  GPU NVIDIA detectada - instalando con CUDA 11.8" -ForegroundColor Green
        pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
    } else {
        Write-Host "  GPU no detectada - instalando version CPU" -ForegroundColor Yellow
        pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
    }

    # Instalar el resto
    pip install -r requirements.txt
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Instalacion completada!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Para iniciar la aplicacion:" -ForegroundColor Cyan
Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  python main.py" -ForegroundColor White
Write-Host ""
if ($useMinimal) {
    Write-Host "NOTA: Estas usando la version minima." -ForegroundColor Yellow
    Write-Host "Para ML completo, instala Python 3.11 y vuelve a ejecutar." -ForegroundColor Yellow
}
Write-Host ""
