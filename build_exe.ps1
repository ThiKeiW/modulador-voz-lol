# ============================================
# Voicemod LoL - Build del .exe (Fase 7)
# Uso: .\build_exe.ps1
# Requiere: .venv311 (Python 3.11 + torch CUDA + pyinstaller)
# Salida: dist\VoicemodLoL\VoicemodLoL.exe (onedir, console visible)
# ============================================

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Voicemod LoL - Build .exe" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (-not (Test-Path ".venv311\Scripts\pyinstaller.exe")) {
    Write-Host "  ERROR: .venv311 sin pyinstaller. Corre antes:" -ForegroundColor Red
    Write-Host "    py -3.11 -m venv .venv311" -ForegroundColor White
    Write-Host "    .\.venv311\Scripts\pip.exe install torch torchaudio --index-url https://download.pytorch.org/whl/cu118" -ForegroundColor White
    Write-Host "    .\.venv311\Scripts\pip.exe install -r requirements.txt pyinstaller" -ForegroundColor White
    exit 1
}

if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

Write-Host "  Compilando (tarda varios minutos, log en build.log)..." -ForegroundColor Yellow
$proc = Start-Process -FilePath ".\.venv311\Scripts\pyinstaller.exe" `
    -ArgumentList "--clean --noconfirm voicemod-lol.spec" `
    -RedirectStandardOutput "build.log" -RedirectStandardError "build.err.log" `
    -NoNewWindow -PassThru -Wait

if ($proc.ExitCode -ne 0) {
    Write-Host "  BUILD FALLO (exit $($proc.ExitCode)). Revisa build.log y build.err.log" -ForegroundColor Red
    exit 1
}

Write-Host "  OK: dist\VoicemodLoL\VoicemodLoL.exe" -ForegroundColor Green
Write-Host ""
Write-Host "  Para distribuir: comprime la carpeta dist\VoicemodLoL en .zip" -ForegroundColor Cyan
Write-Host "  El usuario final descarga modelos con:" -ForegroundColor Cyan
Write-Host "    VoicemodLoL.exe (no incluye .pth/.index/hubert/rmvpe por peso)" -ForegroundColor White
Write-Host "    + scripts de descarga incluidos en el repo" -ForegroundColor White
