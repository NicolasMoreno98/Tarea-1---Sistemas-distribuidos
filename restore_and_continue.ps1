# Script para restaurar progreso y continuar con Ollama

Write-Host "=== RESTAURACION DE PROGRESO ANTERIOR ===" -ForegroundColor Green

# Verificar que tenemos el backup
$backupFile = "dataset/backup_responses.sql"
if (-not (Test-Path $backupFile)) {
    Write-Host "❌ No se encontró el archivo de backup: $backupFile" -ForegroundColor Red
    Write-Host "Generando backup desde la base de datos actual..." -ForegroundColor Yellow
    
    # Intentar hacer backup desde la BD actual
    docker-compose -f docker-compose-ollama.yml up -d postgres
    Start-Sleep 10
    docker-compose -f docker-compose-ollama.yml exec postgres pg_dump -U user -d yahoo_db -t responses --data-only --column-inserts > $backupFile
    
    if (Test-Path $backupFile) {
        Write-Host "✅ Backup creado exitosamente" -ForegroundColor Green
    } else {
        Write-Host "❌ Error creando backup" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ Backup encontrado: $backupFile" -ForegroundColor Green
}

Write-Host "`nIniciando servicios con Ollama..." -ForegroundColor Yellow
docker-compose -f docker-compose-ollama.yml up -d postgres redis

Write-Host "Esperando que los servicios estén listos..." -ForegroundColor Yellow
Start-Sleep 15

Write-Host "Restaurando datos anteriores..." -ForegroundColor Yellow
Get-Content $backupFile | docker-compose -f docker-compose-ollama.yml exec -T postgres psql -U user -d yahoo_db

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Datos restaurados exitosamente" -ForegroundColor Green
    
    # Verificar cuántos registros tenemos
    $count = docker-compose -f docker-compose-ollama.yml exec postgres psql -U user -d yahoo_db -t -c "SELECT COUNT(*) FROM responses;"
    Write-Host "📊 Registros restaurados: $($count.Trim())" -ForegroundColor Cyan
    
    # Verificar progreso
    $progress = docker-compose -f docker-compose-ollama.yml exec postgres psql -U user -d yahoo_db -t -c "SELECT COUNT(*) * 100.0 / 10000 as progress FROM responses;"
    Write-Host "📈 Progreso: $($progress.Trim())% completado" -ForegroundColor Cyan
    
} else {
    Write-Host "❌ Error restaurando datos" -ForegroundColor Red
    exit 1
}

Write-Host "`n🎯 Sistema listo para continuar con Ollama!" -ForegroundColor Green
Write-Host "Para continuar el experimento:" -ForegroundColor Yellow
Write-Host "1. Ejecuta: docker-compose -f docker-compose-ollama.yml up --build llm-service" -ForegroundColor Cyan
Write-Host "2. En otra terminal: docker-compose -f docker-compose-ollama.yml run --rm traffic-generator" -ForegroundColor Cyan