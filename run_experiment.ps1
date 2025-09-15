# Yahoo LLM Evaluation System
# Este script ejecuta el sistema completo para procesar 10,000 preguntas aleatorias

Write-Host "=== Yahoo LLM Evaluation System ===" -ForegroundColor Cyan
Write-Host "Este script ejecutará el sistema completo para procesar 10,000 preguntas aleatorias"
Write-Host "de las primeras 20,000 del dataset train.csv"
Write-Host ""

# Verificar que existe el dataset
if (-not (Test-Path "./dataset/train.csv")) {
    Write-Host "ERROR: No se encontró el archivo dataset/train.csv" -ForegroundColor Red
    Write-Host "Por favor, coloca el archivo train.csv en la carpeta dataset/"
    exit 1
}

Write-Host "✓ Dataset encontrado" -ForegroundColor Green
Write-Host ""

# Construir y levantar los servicios
Write-Host "🐳 Construyendo y levantando servicios Docker..." -ForegroundColor Yellow
docker-compose up --build -d

Write-Host ""
Write-Host "⏳ Esperando a que los servicios estén listos..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Verificar que los servicios estén funcionando
Write-Host "🔍 Verificando servicios..." -ForegroundColor Yellow
$redisStatus = docker-compose ps redis | Select-String "Up"
$postgresStatus = docker-compose ps postgres | Select-String "Up"
$llmStatus = docker-compose ps llm-service | Select-String "Up"

Write-Host "- Redis: $(if ($redisStatus) { '✓ OK' } else { '✗ Error' })"
Write-Host "- PostgreSQL: $(if ($postgresStatus) { '✓ OK' } else { '✗ Error' })"
Write-Host "- LLM Service: $(if ($llmStatus) { '✓ OK' } else { '✗ Error' })"

Write-Host ""
Write-Host "🚀 Ejecutando generador de tráfico..." -ForegroundColor Green
Write-Host "Esto tomará varios minutos dependiendo de la velocidad de la API de Gemini..."

# Ejecutar el generador de tráfico
docker-compose run --rm traffic-generator

Write-Host ""
Write-Host "📊 Resultados guardados en dataset/response.json" -ForegroundColor Green
Write-Host ""

# Mostrar estadísticas básicas si el archivo fue creado
if (Test-Path "./dataset/response.json") {
    Write-Host "=== Resumen de Ejecución ===" -ForegroundColor Cyan
    Write-Host "Archivo de resultados creado exitosamente" -ForegroundColor Green
    Write-Host "Puedes revisar las estadísticas detalladas en dataset/response.json"
} else {
    Write-Host "⚠️  No se encontró el archivo de resultados" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🐳 Para detener los servicios ejecuta: docker-compose down" -ForegroundColor Cyan
Write-Host "📁 Los resultados están en: ./dataset/response.json" -ForegroundColor Cyan
