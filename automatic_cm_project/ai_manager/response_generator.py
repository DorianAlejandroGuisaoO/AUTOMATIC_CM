import requests
import json
import logging
from .prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)

class ResponseGenerator:
    """Genera respuestas usando un modelo local de IA (Llama 3)"""
    
    def __init__(self, model_url="http://localhost:11434/api/generate"):
        """
        Inicializa el generador de respuestas
        
        Args:
            model_url (str): URL del servidor Ollama local
        """
        self.model_url = model_url
        self.model_name = "llama3"  # o "llama3.1", "llama3.2" según tu instalación
    
    def generate(self, comment_text, tone='friendly', context=None):
        """
        Genera una respuesta al comentario usando IA
        
        Args:
            comment_text (str): Texto del comentario
            tone (str): Tono de la respuesta
            context (str, optional): Contexto adicional
            
        Returns:
            str: Respuesta generada
        """
        try:
            # Construir el prompt
            prompt_data = PromptBuilder.build_prompt(comment_text, tone, context)
            
            # Combinar system y user prompt para Ollama
            full_prompt = f"{prompt_data['system']}\n\n{prompt_data['user']}"
            
            # Llamar al modelo local
            payload = {
                "model": self.model_name,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            }
            
            response = requests.post(
                self.model_url,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '').strip()
                
                # Validar que la respuesta no esté vacía
                if not generated_text:
                    logger.warning("El modelo generó una respuesta vacía")
                    return self._get_fallback_response(tone)
                
                return generated_text
            else:
                logger.error(f"Error en la API: {response.status_code}")
                return self._get_fallback_response(tone)
                
        except requests.exceptions.Timeout:
            logger.error("Timeout al conectar con el modelo")
            return self._get_fallback_response(tone)
        except Exception as e:
            logger.error(f"Error al generar respuesta: {str(e)}")
            return self._get_fallback_response(tone)
    
    def _get_fallback_response(self, tone):
        """Respuesta de respaldo si falla la IA"""
        fallbacks = {
            'formal': "Gracias por su comentario. Hemos tomado nota de su mensaje y le responderemos a la brevedad.",
            'friendly': "¡Gracias por tu comentario! 😊 Lo revisaremos y te responderemos pronto.",
            'informative': "Hemos recibido tu comentario. Te proporcionaremos información detallada en breve."
        }
        return fallbacks.get(tone, fallbacks['friendly'])
    
    def test_connection(self):
        """
        Prueba la conexión con el modelo local
        
        Returns:
            bool: True si la conexión es exitosa
        """
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                logger.info(f"Modelos disponibles: {[m['name'] for m in models]}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error al conectar con Ollama: {str(e)}")
            return False