class PromptBuilder:
    """Construye prompts para generar respuestas con diferentes tonos"""
    
    TONE_PROMPTS = {
        'formal': {
            'system': "Eres un asistente profesional que responde comentarios de manera formal y educada.",
            'instructions': """
Genera una respuesta formal y profesional al siguiente comentario.
- Usa un tono respetuoso y educado
- Sé conciso pero completo
- Evita emojis y jerga
- Mantén un lenguaje profesional
"""
        },
        'friendly': {
            'system': "Eres un asistente amigable que responde comentarios de manera cercana y cálida.",
            'instructions': """
Genera una respuesta amigable y cercana al siguiente comentario.
- Usa un tono conversacional y amigable
- Puedes usar emojis con moderación
- Sé empático y positivo
- Mantén la respuesta natural y humana
"""
        },
        'informative': {
            'system': "Eres un asistente experto que proporciona información clara y precisa.",
            'instructions': """
Genera una respuesta informativa y útil al siguiente comentario.
- Proporciona información clara y precisa
- Usa ejemplos si es necesario
- Sé educativo pero accesible
- Estructura la información de manera ordenada
"""
        }
    }
    
    @classmethod
    def build_prompt(cls, comment_text, tone='friendly', context=None):
        """
        Construye el prompt completo para generar una respuesta
        
        Args:
            comment_text (str): Texto del comentario
            tone (str): Tono de la respuesta (formal, friendly, informative)
            context (str, optional): Contexto adicional sobre el post
            
        Returns:
            dict: Diccionario con system prompt y user prompt
        """
        tone_config = cls.TONE_PROMPTS.get(tone, cls.TONE_PROMPTS['friendly'])
        
        user_prompt = f"{tone_config['instructions']}\n\n"
        
        if context:
            user_prompt += f"CONTEXTO DEL POST: {context}\n\n"
        
        user_prompt += f"COMENTARIO A RESPONDER:\n{comment_text}\n\n"
        user_prompt += "RESPUESTA (máximo 500 caracteres):"
        
        return {
            'system': tone_config['system'],
            'user': user_prompt
        }
    
    @classmethod
    def get_available_tones(cls):
        """Retorna los tonos disponibles"""
        return list(cls.TONE_PROMPTS.keys())