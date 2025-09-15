import pandas as pd
import requests
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuración
API_URL = "http://llm-service:5000/process"
CSV_FILE = "/data/train.csv"
OUTPUT_FILE = "/data/response.json"
NUM_TOTAL_QUESTIONS = 20000  # Primeras 20k preguntas del dataset
# Configuration
NUM_REQUESTS = 10000  # Number of random requests to make
QUESTIONS_FILE = "/data/train.csv"

def load_questions():
    """Carga las primeras 20,000 preguntas del CSV"""
    try:
        print("Cargando dataset...")
        # Leer solo las primeras 20,000 filas
        df = pd.read_csv(CSV_FILE, nrows=NUM_TOTAL_QUESTIONS)
        
        # Formato CSV: class_index, question_title, question_content, best_answer
        # Usaremos el índice de fila + 1 como ID único para tener 20k IDs diferentes
        questions = []
        for idx, row in df.iterrows():
            questions.append({
                'id': str(idx + 1),  # Usar índice de fila + 1 como ID único (1-20000)
                'question': str(row.iloc[1]),  # Segunda columna es el título de la pregunta
                'best_answer': str(row.iloc[3]) if pd.notna(row.iloc[3]) else ""  # Cuarta columna es la mejor respuesta
            })
        
        print(f"Cargadas {len(questions)} preguntas")
        print(f"IDs van desde 1 hasta {len(questions)}")
        return questions
        
    except Exception as e:
        print(f"Error cargando questions: {e}")
        return []

def send_request(question_data, max_retries=2):
    """Envía una request al servicio LLM con reintentos hasta obtener respuesta"""
    for attempt in range(max_retries):
        try:
            print(f"    Intento {attempt + 1}/{max_retries}")
            # Timeout ajustado para Gemini 2.5 Flash
            response = requests.post(API_URL, json=question_data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'question_id': question_data['id'],
                    'question': question_data['question'],
                    'human_answer': question_data['best_answer'],
                    'llm_answer': result.get('answer', ''),
                    'source': result.get('source', 'unknown'),  # 'cache' o 'llm'
                    'score': result.get('score', 0.0),
                    'timestamp': time.time()
                }
            elif response.status_code == 429:  # TooManyRequests
                print(f"    Rate limit alcanzado (429), esperando...")
                wait_time = 60  # Esperar 1 minuto por rate limit
                print(f"    Esperando {wait_time} segundos por rate limit...")
                time.sleep(wait_time)
                continue
            else:
                print(f"    Error {response.status_code}: {response.text[:200]}")
                
        except requests.exceptions.Timeout:
            print(f"    Timeout después de 60 segundos")
        except Exception as e:
            print(f"    Excepción: {e}")
        
        # Backoff más moderado
        if attempt < max_retries - 1:
            wait_time = 10 + (attempt * 5)  # 10, 15 segundos
            print(f"    Esperando {wait_time} segundos antes del siguiente intento...")
            time.sleep(wait_time)
    
    print(f"    Falló después de {max_retries} intentos")
    return None

def main():
    """Función principal"""
    print("=== Yahoo LLM Traffic Generator ===")
    
    # Cargar preguntas
    questions = load_questions()
    if not questions:
        print("No se pudieron cargar las preguntas")
        return
    
    # Seleccionar 10,000 preguntas de manera aleatoria con repetición
    print(f"Seleccionando {NUM_REQUESTS} preguntas aleatorias con repetición...")
    selected_questions = random.choices(questions, k=NUM_REQUESTS)
    
    # Mostrar estadísticas de repetición
    unique_ids = set(q['id'] for q in selected_questions)
    print(f"Preguntas únicas seleccionadas: {len(unique_ids)}")
    print(f"Repeticiones: {NUM_REQUESTS - len(unique_ids)}")
    print(f"Cache hit rate esperado: ~{(NUM_REQUESTS - len(unique_ids)) / NUM_REQUESTS * 100:.1f}%")
    
    # Procesar requests
    results = []
    cache_hits = 0
    llm_calls = 0
    
    print("\nEnviando requests secuencialmente para evitar rate limiting...")
    
    # Procesar requests una por una con delay para evitar TooManyRequests
    for i, question in enumerate(selected_questions, 1):
        print(f"\nProcesando request {i}/{NUM_REQUESTS} - ID: {question['id']}")
        
        # Delay mínimo entre requests - respetar 1000 RPM del Tier 1
        if i > 1:
            # 1000 requests per minute = 0.06 segundos entre requests mínimo
            # Usamos 0.1 segundos para ser conservador
            base_delay = 0.1  # 0.1 segundos para respetar rate limit
            print(f"Esperando {base_delay} segundos para respetar rate limit (1000 RPM)...")
            time.sleep(base_delay)
        
        # Enviar request con reintentos hasta obtener respuesta
        start_time = time.time()
        result = send_request(question)
        end_time = time.time()
        
        if result:
            response_time = end_time - start_time
            results.append(result)
            
            # Contar cache hits vs LLM calls
            if result['source'] == 'cache':
                cache_hits += 1
                print(f"  ✓ Cache hit obtenido ({response_time:.1f}s)")
            elif result['source'] == 'llm':
                llm_calls += 1
                print(f"  ✓ LLM call completado ({response_time:.1f}s)")
                # Delay muy pequeño después de LLM calls en Tier 1
                additional_delay = 0.2  # 0.2 segundos después de cada LLM call
                print(f"  LLM call realizada, esperando {additional_delay} segundos adicionales...")
                time.sleep(additional_delay)
            
            # Mostrar progreso cada 500 requests
            if i % 500 == 0:
                rate = cache_hits / len(results) * 100 if results else 0
                avg_time = sum(end_time - start_time for _ in range(len(results))) / len(results) if results else 0
                print(f"\n--- Progreso: {i}/{NUM_REQUESTS} ---")
                print(f"Exitosas: {len(results)}, Cache hits: {cache_hits}, LLM calls: {llm_calls}")
                print(f"Cache hit rate actual: {rate:.1f}%")
                print(f"Tiempo promedio de respuesta: {avg_time:.1f}s")
        else:
            print(f"  ✗ Request falló definitivamente después de todos los reintentos")
            # Aún así, esperamos antes de continuar - más tiempo por el fallo
            print(f"  Esperando 30 segundos antes de continuar...")
            time.sleep(30)
    
    # Guardar resultados
    print(f"\nGuardando {len(results)} resultados en {OUTPUT_FILE}...")
    
    summary = {
        'total_requests': NUM_REQUESTS,
        'successful_requests': len(results),
        'cache_hits': cache_hits,
        'llm_calls': llm_calls,
        'cache_hit_rate': cache_hits / len(results) if results else 0,
        'unique_questions': len(unique_ids),
        'timestamp': time.time()
    }
    
    output_data = {
        'summary': summary,
        'responses': results
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    # Mostrar estadísticas finales
    print("\n=== Estadísticas Finales ===")
    print(f"Total requests: {NUM_REQUESTS}")
    print(f"Requests exitosas: {len(results)}")
    print(f"Cache hits: {cache_hits}")
    print(f"LLM calls: {llm_calls}")
    print(f"Cache hit rate: {cache_hits / len(results) * 100:.2f}%" if results else "0%")
    print(f"Preguntas únicas: {len(unique_ids)}")
    print(f"Promedio de repeticiones por pregunta: {NUM_REQUESTS / len(unique_ids):.2f}")
    print(f"Resultados guardados en: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()