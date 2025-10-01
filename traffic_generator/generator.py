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
NUM_REQUESTS = 10  # Number of random requests to make (TEST MODE)
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
    
    # Procesar requests una por una con delay para evitar sobrecarga
    print(f"\n{'='*60}")
    print(f"INICIANDO EXPERIMENTO OLLAMA - {NUM_REQUESTS:,} REQUESTS")
    print(f"{'='*60}")
    
    for i, question in enumerate(selected_questions, 1):
        if i % 10 != 1:  # Solo mostrar detalles cada 10 o la primera
            print(f"[{i:4d}/{NUM_REQUESTS}] Procesando ID: {question['id']}", end=" ")
        else:
            print(f"\nRequest {i}/{NUM_REQUESTS} - ID: {question['id']}")
            print(f"Pregunta: {question['question'][:80]}...")
        
        # Delay mínimo entre requests para no sobrecargar
        if i > 1:
            base_delay = 0.1  # 0.1 segundos entre requests
            if i % 10 == 1:
                print(f"Delay: {base_delay}s para evitar sobrecarga...")
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
                if i % 10 != 1:
                    print(f"CACHE ({response_time:.1f}s, score: {result['score']:.3f})")
                else:
                    print(f"  Cache hit obtenido ({response_time:.1f}s) - Score: {result['score']:.3f}")
            elif result['source'] == 'llm':
                llm_calls += 1
                if i % 10 != 1:
                    print(f"LLM ({response_time:.1f}s, score: {result['score']:.3f})")
                else:
                    print(f"  Ollama respondió ({response_time:.1f}s) - Score: {result['score']:.3f}")
                    # Verificar qué clave contiene la respuesta
                    answer_text = result.get('answer') or result.get('response') or result.get('llm_response', 'N/A')
                    if isinstance(answer_text, str) and len(answer_text) > 100:
                        print(f"  Respuesta: {answer_text[:100]}...")
                    else:
                        print(f"  Respuesta: {answer_text}")
                # Delay después de LLM calls
                additional_delay = 0.2
                time.sleep(additional_delay)
            
            # Mostrar progreso cada 10 requests (más frecuente)
            if i % 10 == 0:
                rate = cache_hits / len(results) * 100 if results else 0
                avg_score = sum(r['score'] for r in results) / len(results) if results else 0
                progress_percent = (i / NUM_REQUESTS) * 100
                estimated_remaining = ((end_time - start_time) * (NUM_REQUESTS - i)) / 60  # en minutos
                
                print(f"\nPROGRESO: {i}/{NUM_REQUESTS} ({progress_percent:.1f}%)")
                print(f"Exitosas: {len(results)} | Cache hits: {cache_hits} | LLM calls: {llm_calls}")
                print(f"Cache hit rate: {rate:.1f}% | Score promedio: {avg_score:.3f}")
                print(f"Tiempo estimado restante: {estimated_remaining:.1f} minutos")
                print("─" * 60)
        else:
            print(f"  ERROR: Request falló definitivamente después de todos los reintentos")
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
    print(f"\n{'='*60}")
    print("EXPERIMENTO OLLAMA COMPLETADO")
    print(f"{'='*60}")
    
    if results:
        avg_score = sum(r['score'] for r in results) / len(results)
        max_score = max(r['score'] for r in results)
        min_score = min(r['score'] for r in results)
        
        print(f"ESTADÍSTICAS FINALES:")
        print(f"  • Total requests: {NUM_REQUESTS:,}")
        print(f"  • Requests exitosas: {len(results):,} ({len(results)/NUM_REQUESTS*100:.1f}%)")
        print(f"  • Cache hits: {cache_hits:,} ({cache_hits/len(results)*100:.1f}%)")
        print(f"  • LLM calls: {llm_calls:,} ({llm_calls/len(results)*100:.1f}%)")
        print(f"\nSCORES:")
        print(f"  • Score promedio: {avg_score:.4f}")
        print(f"  • Score máximo: {max_score:.4f}")
        print(f"  • Score mínimo: {min_score:.4f}")
        print(f"\nResultados guardados en: {OUTPUT_FILE}")
    else:
        print("ERROR: No se procesaron requests exitosas")
    
    print(f"{'='*60}")

if __name__ == "__main__":
    main()