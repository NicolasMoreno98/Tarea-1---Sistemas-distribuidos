import requests
import json
import time
import os
import redis
import psycopg2
from flask import Flask, request, jsonify
from bert_score import score
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuración de Ollama (local)
OLLAMA_URL = "http://host.docker.internal:11434"  # URL para acceder a Ollama desde Docker
OLLAMA_MODEL = "tinyllama:latest"  # Modelo ultrarrápido disponible localmente

# Configuración de Redis
redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

# Configuración de PostgreSQL
def get_db_connection():
    return psycopg2.connect(
        host='postgres',
        database='yahoo_db',
        user='user',
        password='password'
    )

def call_ollama_llm(question):
    """Llama a Ollama local para generar respuesta - OPTIMIZADO ANTI-TIMEOUT"""
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": f"Answer briefly: {question}",  # Prompt más corto
            "stream": False,
            "options": {
                "num_ctx": 512,      # Contexto MUY reducido para velocidad
                "num_gpu": 1.0,      # Usar toda la GPU para máxima velocidad
                "temperature": 0.3,   # Balance velocidad/calidad
                "top_p": 0.9,        # Limitar opciones para velocidad
                "repeat_penalty": 1.0,  # Sin penalización por repetición
                "num_predict": 100,   # Limitar tokens de respuesta
                "stop": [".", "?", "!"]  # Parar en puntuación para respuestas cortas
            }
        }
        
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=15  # Timeout ultra-agresivo para TinyLlama (debe responder en <5s)
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('response', '').strip()
        else:
            logger.error(f"Error en Ollama: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error llamando a Ollama: {e}")
        return None

def calculate_bertscore(candidate, reference):
    """Calcula BERTScore entre respuesta del LLM y respuesta humana"""
    try:
        if not candidate or not reference:
            return 0.0
        
        P, R, F1 = score([candidate], [reference], lang='en', verbose=False)
        return float(F1[0])
    except Exception as e:
        logger.error(f"Error calculando BERTScore: {e}")
        return 0.0

@app.route('/process', methods=['POST'])
def process_question():
    try:
        data = request.json
        question_id = data['id']
        question = data['question']
        best_answer = data['best_answer']
        
        # Buscar en cache primero
        cache_key = f"question:{question_id}"
        cached_result = redis_client.get(cache_key)
        
        if cached_result:
            logger.info(f"Cache hit para pregunta {question_id}")
            result = json.loads(cached_result)
            result['source'] = 'cache'
            
            # Incrementar contador en BD
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE responses SET count = count + 1 WHERE id = %s",
                        (question_id,)
                    )
                    conn.commit()
            
            return jsonify(result)
        
        # Si no está en cache, llamar a Ollama
        logger.info(f"Cache miss para pregunta {question_id} - llamando a Ollama")
        llm_answer = call_ollama_llm(question)
        
        if llm_answer is None:
            return jsonify({'error': 'Error generando respuesta con Ollama'}), 500
        
        # Calcular BERTScore
        bert_score = calculate_bertscore(llm_answer, best_answer)
        
        result = {
            'answer': llm_answer,
            'score': bert_score,
            'source': 'llm'
        }
        
        # Guardar en cache (TTL de 1 hora)
        redis_client.setex(cache_key, 3600, json.dumps(result))
        
        # Guardar en base de datos
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO responses (id, question, human_answer, llm_answer, score, count)
                    VALUES (%s, %s, %s, %s, %s, 1)
                    ON CONFLICT (id) DO UPDATE SET
                        count = responses.count + 1
                """, (question_id, question, best_answer, llm_answer, bert_score))
                conn.commit()
        
        logger.info(f"Respuesta generada para pregunta {question_id} - Score: {bert_score:.3f}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error procesando pregunta: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    try:
        # Verificar conectividad con Ollama
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        ollama_status = response.status_code == 200
        
        return jsonify({
            'status': 'healthy',
            'ollama_connected': ollama_status,
            'redis_connected': redis_client.ping(),
            'model': OLLAMA_MODEL
        })
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

if __name__ == '__main__':
    logger.info(f"Iniciando servicio LLM con Ollama - Modelo: {OLLAMA_MODEL}")
    logger.info(f"Ollama URL: {OLLAMA_URL}")
    app.run(host='0.0.0.0', port=5000, debug=True)