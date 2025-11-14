import praw
from django.conf import settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class RedditBot:
    def __init__(self):
        """Inicializa la conexión con Reddit"""
        self.reddit = praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT,
            username=settings.REDDIT_USERNAME,
            password=settings.REDDIT_PASSWORD
        )
        
    def get_subreddit_posts(self, subreddit_name, limit=25):
        """
        Obtiene los posts más recientes de un subreddit
        
        Args:
            subreddit_name (str): Nombre del subreddit
            limit (int): Número de posts a obtener
            
        Returns:
            list: Lista de posts con su información
        """
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = []
            
            for submission in subreddit.new(limit=limit):
                posts.append({
                    'post_id': submission.id,
                    'title': submission.title,
                    'url': submission.url,
                    'permalink': f"https://reddit.com{submission.permalink}",
                    'author': str(submission.author),
                    'created_at': datetime.fromtimestamp(submission.created_utc),
                    'subreddit': subreddit_name,
                    'num_comments': submission.num_comments
                })
            
            return posts
        except Exception as e:
            logger.error(f"Error al obtener posts: {str(e)}")
            return []
    
    def get_post_comments(self, post_id):
        """
        Obtiene todos los comentarios de un post
        
        Args:
            post_id (str): ID del post en Reddit
            
        Returns:
            list: Lista de comentarios con su información
        """
        try:
            submission = self.reddit.submission(id=post_id)
            submission.comments.replace_more(limit=0)  # Expandir todos los comentarios
            
            comments = []
            for comment in submission.comments.list():
                # Ignorar comentarios del bot mismo
                if str(comment.author) == settings.REDDIT_USERNAME:
                    continue
                    
                comments.append({
                    'comment_id': comment.id,
                    'author': str(comment.author),
                    'content': comment.body,
                    'created_at': datetime.fromtimestamp(comment.created_utc),
                    'parent_id': comment.parent_id if hasattr(comment, 'parent_id') else None,
                    'permalink': f"https://reddit.com{comment.permalink}"
                })
            
            return comments
        except Exception as e:
            logger.error(f"Error al obtener comentarios del post {post_id}: {str(e)}")
            return []
    
    def reply_to_comment(self, comment_id, text):
        """
        Responde a un comentario en Reddit
        
        Args:
            comment_id (str): ID del comentario
            text (str): Texto de la respuesta
            
        Returns:
            str: ID de la respuesta o None si falla
        """
        try:
            comment = self.reddit.comment(id=comment_id)
            reply = comment.reply(text)
            logger.info(f"Respuesta publicada exitosamente: {reply.id}")
            return reply.id
        except Exception as e:
            logger.error(f"Error al publicar respuesta: {str(e)}")
            return None
    
    def test_connection(self):
        """
        Prueba la conexión con Reddit
        
        Returns:
            bool: True si la conexión es exitosa
        """
        try:
            user = self.reddit.user.me()
            logger.info(f"Conexión exitosa. Usuario: {user.name}")
            return True
        except Exception as e:
            logger.error(f"Error de conexión: {str(e)}")
            return False
        

    def create_post(self, subreddit_name, title, content, post_type='text', image_path=None):
        """
        Crea un nuevo post en Reddit
        
        Args:
            subreddit_name (str): Nombre del subreddit
            title (str): Título del post
            content (str): Contenido del post (texto o URL)
            post_type (str): Tipo de post ('text', 'link', 'image')
            image_path (str): Ruta de la imagen (para post_type='image')
            
        Returns:
            dict: Información del post creado o None si falla
        """
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            if post_type == 'text':
                submission = subreddit.submit(
                    title=title,
                    selftext=content
                )
            elif post_type == 'link':
                submission = subreddit.submit(
                    title=title,
                    url=content
                )
            elif post_type == 'image':
                if not image_path:
                    logger.error("Se requiere una imagen para post tipo 'image'")
                    return None
                submission = subreddit.submit_image(
                    title=title,
                    image_path=image_path
                )
            else:
                logger.error(f"Tipo de post no soportado: {post_type}")
                return None
            
            logger.info(f"Post creado exitosamente: {submission.id}")
            
            return {
                'post_id': submission.id,
                'title': submission.title,
                'url': submission.url,
                'permalink': f"https://reddit.com{submission.permalink}",
                'created_at': datetime.fromtimestamp(submission.created_utc)
            }
            
        except Exception as e:
            logger.error(f"Error al crear post: {str(e)}")
            return None

    def edit_post(self, post_id, new_content):
        """
        Edita un post existente (solo posts de texto)
        
        Args:
            post_id (str): ID del post
            new_content (str): Nuevo contenido
            
        Returns:
            bool: True si se editó exitosamente
        """
        try:
            submission = self.reddit.submission(id=post_id)
            
            # Verificar que sea el autor
            if str(submission.author) != settings.REDDIT_USERNAME:
                logger.error("No tienes permiso para editar este post")
                return False
            
            # Solo se pueden editar posts de texto
            if not submission.is_self:
                logger.error("Solo se pueden editar posts de texto")
                return False
            
            submission.edit(new_content)
            logger.info(f"Post {post_id} editado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al editar post: {str(e)}")
            return False

    def delete_post(self, post_id):
        """
        Elimina un post
        
        Args:
            post_id (str): ID del post
            
        Returns:
            bool: True si se eliminó exitosamente
        """
        try:
            submission = self.reddit.submission(id=post_id)
            
            # Verificar que sea el autor
            if str(submission.author) != settings.REDDIT_USERNAME:
                logger.error("No tienes permiso para eliminar este post")
                return False
            
            submission.delete()
            logger.info(f"Post {post_id} eliminado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al eliminar post: {str(e)}")
            return False

    def delete_comment(self, comment_id):
        """
        Elimina/Remueve un comentario de Reddit
        - Si eres el autor: lo ELIMINA permanentemente
        - Si eres moderador: lo REMUEVE (oculta pero no elimina)
        
        Args:
            comment_id (str): ID del comentario
            
        Returns:
            bool: True si se eliminó/removió exitosamente
        """
        try:
            comment = self.reddit.comment(id=comment_id)
            
            # Intentar eliminar si eres el autor
            if str(comment.author) == settings.REDDIT_USERNAME:
                comment.delete()
                logger.info(f"Comentario {comment_id} eliminado exitosamente de Reddit (como autor)")
                return True
            else:
                # Si no eres el autor, intentar remover como moderador
                comment.mod.remove(spam=False)
                logger.info(f"Comentario {comment_id} removido exitosamente de Reddit (como moderador)")
                return True
            
        except Exception as e:
            logger.error(f"No se pudo eliminar/remover comentario {comment_id} de Reddit: {str(e)}")
            return False