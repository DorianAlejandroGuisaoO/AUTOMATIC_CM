import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Scopes necesarios para leer y responder comentarios
SCOPES = [
    'https://www.googleapis.com/auth/youtube.force-ssl',
    'https://www.googleapis.com/auth/youtube.readonly'
]

class YouTubeBot:
    def __init__(self, credentials_file='client_secret.json', token_file='youtube_token.pickle'):
        """
        Inicializa la conexión con YouTube
        
        Args:
            credentials_file (str): Ruta al archivo client_secret.json
            token_file (str): Ruta donde se guardará el token de acceso
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.youtube = None
        self._authenticate()
    
    def _authenticate(self):
        """Autentica con OAuth 2.0 y crea el cliente de YouTube"""
        creds = None
        
        # Verificar si ya existe un token guardado
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # Si no hay credenciales válidas, solicitar login
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error al refrescar token: {str(e)}")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"No se encontró {self.credentials_file}. "
                        "Descarga el archivo desde Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, 
                    SCOPES
                )
                creds = flow.run_local_server(port=8080)
            
            # Guardar el token para futuros usos
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        # Crear el cliente de YouTube
        self.youtube = build('youtube', 'v3', credentials=creds)
        logger.info("Autenticación exitosa con YouTube API")
    
    def get_channel_videos(self, channel_id=None, max_results=25):
        """
        Obtiene los videos más recientes del canal autenticado o de un canal específico
        
        Args:
            channel_id (str, optional): ID del canal. Si no se proporciona, usa el canal autenticado
            max_results (int): Número máximo de videos a obtener
            
        Returns:
            list: Lista de videos con su información
        """
        try:
            if not channel_id:
                # Obtener el canal del usuario autenticado
                channels_response = self.youtube.channels().list(
                    part='contentDetails',
                    mine=True
                ).execute()
                
                if not channels_response.get('items'):
                    logger.error("No se encontró ningún canal para el usuario autenticado")
                    return []
                
                uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            else:
                # Usar el canal especificado
                channels_response = self.youtube.channels().list(
                    part='contentDetails',
                    id=channel_id
                ).execute()
                
                if not channels_response.get('items'):
                    logger.error(f"No se encontró el canal {channel_id}")
                    return []
                
                uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Obtener videos de la playlist de uploads
            playlist_response = self.youtube.playlistItems().list(
                part='snippet,contentDetails',
                playlistId=uploads_playlist_id,
                maxResults=max_results
            ).execute()
            
            videos = []
            for item in playlist_response.get('items', []):
                video_id = item['contentDetails']['videoId']
                
                # Obtener estadísticas del video
                video_response = self.youtube.videos().list(
                    part='snippet,statistics',
                    id=video_id
                ).execute()
                
                if video_response.get('items'):
                    video_data = video_response['items'][0]
                    videos.append({
                        'video_id': video_id,
                        'title': video_data['snippet']['title'],
                        'description': video_data['snippet']['description'],
                        'published_at': datetime.strptime(
                            video_data['snippet']['publishedAt'],
                            '%Y-%m-%dT%H:%M:%SZ'
                        ),
                        'thumbnail_url': video_data['snippet']['thumbnails']['medium']['url'],
                        'url': f"https://www.youtube.com/watch?v={video_id}",
                        'view_count': int(video_data['statistics'].get('viewCount', 0)),
                        'comment_count': int(video_data['statistics'].get('commentCount', 0)),
                        'channel_title': video_data['snippet']['channelTitle']
                    })
            
            return videos
            
        except HttpError as e:
            logger.error(f"Error HTTP al obtener videos: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error al obtener videos: {str(e)}")
            return []
    
    def get_video_comments(self, video_id, max_results=100):
        """
        Obtiene los comentarios de un video
        
        Args:
            video_id (str): ID del video
            max_results (int): Número máximo de comentarios a obtener
            
        Returns:
            list: Lista de comentarios con su información
        """
        try:
            comments = []
            request = self.youtube.commentThreads().list(
                part='snippet,replies',
                videoId=video_id,
                maxResults=min(max_results, 100),  # API permite máx 100 por request
                textFormat='plainText',
                order='time'  # Ordenar por más recientes
            )
            
            while request and len(comments) < max_results:
                response = request.execute()
                
                for item in response.get('items', []):
                    top_comment = item['snippet']['topLevelComment']['snippet']
                    
                    comment_data = {
                        'comment_id': item['snippet']['topLevelComment']['id'],
                        'author': top_comment['authorDisplayName'],
                        'author_channel_id': top_comment.get('authorChannelId', {}).get('value', ''),
                        'content': top_comment['textDisplay'],
                        'like_count': top_comment.get('likeCount', 0),
                        'published_at': datetime.strptime(
                            top_comment['publishedAt'],
                            '%Y-%m-%dT%H:%M:%SZ'
                        ),
                        'updated_at': datetime.strptime(
                            top_comment['updatedAt'],
                            '%Y-%m-%dT%H:%M:%SZ'
                        ),
                        'parent_id': None,
                        'is_reply': False
                    }
                    comments.append(comment_data)
                    
                    # Obtener respuestas al comentario si existen
                    if 'replies' in item:
                        for reply in item['replies']['comments']:
                            reply_snippet = reply['snippet']
                            reply_data = {
                                'comment_id': reply['id'],
                                'author': reply_snippet['authorDisplayName'],
                                'author_channel_id': reply_snippet.get('authorChannelId', {}).get('value', ''),
                                'content': reply_snippet['textDisplay'],
                                'like_count': reply_snippet.get('likeCount', 0),
                                'published_at': datetime.strptime(
                                    reply_snippet['publishedAt'],
                                    '%Y-%m-%dT%H:%M:%SZ'
                                ),
                                'updated_at': datetime.strptime(
                                    reply_snippet['updatedAt'],
                                    '%Y-%m-%dT%H:%M:%SZ'
                                ),
                                'parent_id': item['snippet']['topLevelComment']['id'],
                                'is_reply': True
                            }
                            comments.append(reply_data)
                
                # Siguiente página si existe
                request = self.youtube.commentThreads().list_next(request, response)
                
                if len(comments) >= max_results:
                    break
            
            return comments[:max_results]
            
        except HttpError as e:
            if e.resp.status == 403:
                logger.error("Los comentarios están deshabilitados para este video")
            else:
                logger.error(f"Error HTTP al obtener comentarios: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error al obtener comentarios: {str(e)}")
            return []
    
    def reply_to_comment(self, comment_id, text):
        """
        Responde a un comentario
        
        Args:
            comment_id (str): ID del comentario (puede ser top-level o reply)
            text (str): Texto de la respuesta
            
        Returns:
            str: ID de la respuesta creada o None si falla
        """
        try:
            # Insertar respuesta
            response = self.youtube.comments().insert(
                part='snippet',
                body={
                    'snippet': {
                        'parentId': comment_id,
                        'textOriginal': text
                    }
                }
            ).execute()
            
            reply_id = response['id']
            logger.info(f"Respuesta publicada exitosamente: {reply_id}")
            return reply_id
            
        except HttpError as e:
            logger.error(f"Error HTTP al publicar respuesta: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error al publicar respuesta: {str(e)}")
            return None
    
    def test_connection(self):
        """
        Prueba la conexión con YouTube API
        
        Returns:
            bool: True si la conexión es exitosa
        """
        try:
            # Intentar obtener info del canal autenticado
            response = self.youtube.channels().list(
                part='snippet',
                mine=True
            ).execute()
            
            if response.get('items'):
                channel_title = response['items'][0]['snippet']['title']
                logger.info(f"Conexión exitosa. Canal: {channel_title}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error de conexión: {str(e)}")
            return False