import requests
import json
import logging

logger = logging.getLogger(__name__)

class PostGenerator:
    """Genera contenido para posts de empleo usando IA"""
    
    def __init__(self, model_url="http://localhost:11434/api/generate"):
        self.model_url = model_url
        self.model_name = "llama3"
    
    def generate_job_post(self, job_title, company_name, job_type, location, 
                         salary_range=None, requirements=None, benefits=None):
        """
        Genera un post atractivo para oferta de empleo
        
        Args:
            job_title (str): Título del puesto
            company_name (str): Nombre de la empresa
            job_type (str): Tipo de empleo (Tiempo completo, Medio tiempo, etc)
            location (str): Ubicación
            salary_range (str, optional): Rango salarial
            requirements (list, optional): Lista de requisitos
            benefits (list, optional): Lista de beneficios
            
        Returns:
            dict: Título y contenido generados
        """
        try:
            # Construir el prompt
            prompt = self._build_job_prompt(
                job_title, company_name, job_type, location,
                salary_range, requirements, benefits
            )
            
            # Llamar al modelo
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "max_tokens": 800
                }
            }
            
            response = requests.post(
                self.model_url,
                json=payload,
                timeout=90
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '').strip()
                
                # Separar título y contenido
                lines = generated_text.split('\n', 1)
                title = lines[0].replace('Título:', '').replace('**', '').strip()
                content = lines[1].strip() if len(lines) > 1 else generated_text
                
                return {
                    'title': title[:300],  # Límite de Reddit
                    'content': content
                }
            else:
                logger.error(f"Error en la API: {response.status_code}")
                return self._get_fallback_post(job_title, company_name)
                
        except Exception as e:
            logger.error(f"Error al generar post: {str(e)}")
            return self._get_fallback_post(job_title, company_name)
    
    def _build_job_prompt(self, job_title, company_name, job_type, location,
                         salary_range, requirements, benefits):
        """Construye el prompt para generar el post"""
        
        prompt = f"""Eres un experto en reclutamiento y marketing de empleos. Genera un post atractivo para Reddit sobre la siguiente oferta de empleo.

INFORMACIÓN DEL EMPLEO:
- Puesto: {job_title}
- Empresa: {company_name}
- Tipo: {job_type}
- Ubicación: {location}
"""
        
        if salary_range:
            prompt += f"- Salario: {salary_range}\n"
        
        if requirements:
            prompt += f"\nREQUISITOS:\n"
            for req in requirements:
                prompt += f"- {req}\n"
        
        if benefits:
            prompt += f"\nBENEFICIOS:\n"
            for benefit in benefits:
                prompt += f"- {benefit}\n"
        
        prompt += """

INSTRUCCIONES:
1. Crea un título atractivo y profesional (máximo 300 caracteres)
2. Escribe un contenido estructurado y fácil de leer
3. Usa emojis apropiados para hacer el post más atractivo
4. Incluye una llamada a la acción al final
5. Mantén un tono profesional pero amigable
6. No uses formato Markdown para el título, solo texto plano

FORMATO DE RESPUESTA:
Título: [El título aquí]

[El contenido del post aquí]
"""
        
        return prompt
    
    def generate_custom_post(self, topic, tone='professional', length='medium'):
        """
        Genera un post personalizado sobre cualquier tema
        
        Args:
            topic (str): Tema del post
            tone (str): Tono (professional, casual, enthusiastic)
            length (str): Longitud (short, medium, long)
            
        Returns:
            dict: Título y contenido generados
        """
        try:
            prompt = f"""Genera un post para Reddit sobre el siguiente tema: {topic}

Tono: {tone}
Longitud: {length}

Crea un título atractivo y contenido interesante. Usa emojis apropiados.

FORMATO:
Título: [título aquí]

[contenido aquí]
"""
            
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.8,
                    "max_tokens": 600
                }
            }
            
            response = requests.post(
                self.model_url,
                json=payload,
                timeout=90
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '').strip()
                
                lines = generated_text.split('\n', 1)
                title = lines[0].replace('Título:', '').replace('**', '').strip()
                content = lines[1].strip() if len(lines) > 1 else generated_text
                
                return {
                    'title': title[:300],
                    'content': content
                }
            else:
                return self._get_fallback_post('Post', 'ACM')
                
        except Exception as e:
            logger.error(f"Error al generar post personalizado: {str(e)}")
            return self._get_fallback_post('Post', 'ACM')
    
    def _get_fallback_post(self, job_title, company_name):
        """Post de respaldo si falla la IA"""
        return {
            'title': f"🔥 {job_title} en {company_name} - ¡Únete a nuestro equipo!",
            'content': f"""¡Estamos buscando un/a {job_title}!

🏢 **Empresa:** {company_name}

💼 **¿Qué harás?**
Serás parte de un equipo dinámico y contribuirás al crecimiento de la empresa.

✨ **¿Qué buscamos?**
Personas apasionadas, proactivas y con ganas de aprender.

📩 **¿Interesado/a?**
¡Contáctanos para más información!

#Empleo #Trabajo #Oportunidad
"""
        }