#!/usr/bin/env python3
"""
Análisis matemático de la proporción de cache hits esperada vs observada
"""
import math

def analyze_cache_hits():
    print('🔍 ANÁLISIS MATEMÁTICO DE CACHE HITS')
    print('='*60)
    
    # Parámetros del experimento
    N = 20000  # Pool total de preguntas
    n = 10000  # Requests realizados
    k_observed = 260  # Cache hits observados
    
    print(f'📊 PARÁMETROS DEL EXPERIMENTO:')
    print(f'  • Pool de preguntas disponibles: {N:,}')
    print(f'  • Requests totales realizados: {n:,}')
    print(f'  • Cache hits observados: {k_observed}')
    print(f'  • Rate observado: {k_observed/n*100:.2f}%')
    
    print(f'\n🎯 ANÁLISIS TEÓRICO (Distribución de Poisson):')
    
    # Para selección aleatoria con reemplazo de n elementos de N posibles
    # La probabilidad de seleccionar una pregunta específica es 1/N
    p_single = 1/N
    lambda_param = n * p_single  # Parámetro λ para distribución de Poisson
    
    print(f'  • Probabilidad por pregunta: {p_single:.6f}')
    print(f'  • Parámetro λ (Poisson): {lambda_param:.2f}')
    print(f'  • Veces esperadas por pregunta: {lambda_param:.2f}')
    
    # Calcular probabilidades y cache hits esperados
    total_cache_hits_expected = 0
    
    print(f'\n📈 CÁLCULO DE CACHE HITS POR REPETICIÓN:')
    for k in range(2, 8):  # k = número de veces que aparece una pregunta
        prob_k = (lambda_param**k * math.exp(-lambda_param)) / math.factorial(k)
        questions_with_k_appearances = N * prob_k
        cache_hits_from_k = (k-1) * questions_with_k_appearances  # k-1 cache hits por pregunta
        total_cache_hits_expected += cache_hits_from_k
        
        if prob_k > 0.0001:  # Solo mostrar si es significativo
            print(f'  • k={k} apariciones: {questions_with_k_appearances:.1f} preguntas → {cache_hits_from_k:.0f} cache hits')
    
    print(f'\n📊 RESULTADOS COMPARATIVOS:')
    print(f'  • Cache hits esperados (teórico): {total_cache_hits_expected:.0f}')
    print(f'  • Cache hits observados (real): {k_observed}')
    print(f'  • Diferencia absoluta: {abs(k_observed - total_cache_hits_expected):.0f}')
    print(f'  • Ratio observado/esperado: {k_observed/total_cache_hits_expected:.2f}x')
    
    # Análisis alternativo: Problema del cumpleaños generalizado
    print(f'\n🎲 ANÁLISIS ALTERNATIVO (Problema del Cumpleaños):')
    
    # Aproximación para preguntas únicas esperadas
    expected_unique = N * (1 - math.exp(-n/N))
    expected_duplicates = n - expected_unique
    
    print(f'  • Preguntas únicas esperadas: {expected_unique:.0f}')
    print(f'  • Total de duplicados esperados: {expected_duplicates:.0f}')
    print(f'  • Cache hits ≈ duplicados: {expected_duplicates:.0f}')
    
    # Rango de confianza (±2 desviaciones estándar)
    variance = total_cache_hits_expected  # Para Poisson, varianza = media
    std_dev = math.sqrt(variance)
    lower_bound = total_cache_hits_expected - 2*std_dev
    upper_bound = total_cache_hits_expected + 2*std_dev
    
    print(f'\n📏 RANGO DE CONFIANZA (95%):')
    print(f'  • Media esperada: {total_cache_hits_expected:.0f}')
    print(f'  • Desviación estándar: {std_dev:.1f}')
    print(f'  • Rango [μ-2σ, μ+2σ]: [{lower_bound:.0f}, {upper_bound:.0f}]')
    
    # Verificar si está dentro del rango
    is_within_range = lower_bound <= k_observed <= upper_bound
    
    print(f'\n✅ CONCLUSIÓN FINAL:')
    if is_within_range:
        print(f'  ✓ Los {k_observed} cache hits están DENTRO del rango esperado')
        print(f'  ✓ El resultado es estadísticamente NORMAL')
        print(f'  ✓ La proporción {k_observed/n*100:.1f}% es matemáticamente correcta')
    else:
        if k_observed < lower_bound:
            print(f'  ⚠ Los {k_observed} cache hits están por DEBAJO del rango esperado')
            print(f'  ⚠ Podría indicar un problema en la aleatoriedad')
        else:
            print(f'  ⚠ Los {k_observed} cache hits están por ENCIMA del rango esperado')
            print(f'  ⚠ Podría indicar sesgo en la selección')
    
    # Información adicional
    print(f'\n💡 CONTEXTO ADICIONAL:')
    print(f'  • Con selección aleatoria pura, ~{total_cache_hits_expected/n*100:.1f}% de cache hits es normal')
    print(f'  • Pool de 20k preguntas para 10k requests es suficientemente grande')
    print(f'  • La baja tasa de cache hits confirma buena diversidad del dataset')
    
    return {
        'observed': k_observed,
        'expected': total_cache_hits_expected,
        'is_normal': is_within_range,
        'confidence_range': (lower_bound, upper_bound)
    }

if __name__ == "__main__":
    analyze_cache_hits()