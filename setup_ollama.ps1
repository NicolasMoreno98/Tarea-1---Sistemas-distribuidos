# Script para verificar y configurar Ollama
# Ejecutar este script antes de iniciar el sistema

Write-Host "=== VERIFICACION DE OLLAMA ===" -ForegroundColor Green

# Verificar si Ollama está corriendo
try {
    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 5
    Write-Host "✅ Ollama está corriendo correctamente" -ForegroundColor Green
    
    # Mostrar modelos disponibles
    Write-Host "`nModelos disponibles:" -ForegroundColor Yellow
    foreach ($model in $response.models) {
        Write-Host "  - $($model.name)" -ForegroundColor Cyan
    }
} catch {
    Write-Host "❌ Ollama no está corriendo o no es accesible en localhost:11434" -ForegroundColor Red
    Write-Host "Por favor, ejecuta: ollama serve" -ForegroundColor Yellow
    exit 1
}

# Verificar si llama2 está instalado
$hasLlama2 = $response.models | Where-Object { $_.name -like "*llama2*" }
if (-not $hasLlama2) {
    Write-Host "`n⚠️  Modelo 'llama2' no encontrado" -ForegroundColor Yellow
    Write-Host "Instalando llama2..." -ForegroundColor Yellow
    ollama pull llama2
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ llama2 instalado correctamente" -ForegroundColor Green
    } else {
        Write-Host "❌ Error instalando llama2" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ Modelo llama2 disponible" -ForegroundColor Green
}

# Hacer una prueba simple
Write-Host "`nProbando respuesta de Ollama..." -ForegroundColor Yellow
try {
    $testPayload = @{
        model = "llama2"
        prompt = "What is 2+2?"
        stream = $false
    }
    $testResponse = Invoke-RestMethod -Uri "http://localhost:11434/api/generate" -Method Post -Body ($testPayload | ConvertTo-Json) -ContentType "application/json" -TimeoutSec 30
    Write-Host "✅ Prueba exitosa. Respuesta: $($testResponse.response.Substring(0, [Math]::Min(50, $testResponse.response.Length)))..." -ForegroundColor Green
} catch {
    Write-Host "❌ Error en prueba de Ollama: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`n🚀 Ollama está listo para el experimento!" -ForegroundColor Green
Write-Host "Ahora puedes ejecutar: docker-compose -f docker-compose-ollama.yml up --build" -ForegroundColor Cyan