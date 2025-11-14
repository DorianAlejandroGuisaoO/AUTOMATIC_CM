from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from .models import YouTubeVideo, YouTubeComment, YouTubeResponse
from ai_manager.response_generator import ResponseGenerator
from bots.youtube_bot import YouTubeBot
import logging

logger = logging.getLogger(__name__)

@login_required
def youtube_manager(request):
    """Vista principal - Lista de videos de YouTube"""
    from datetime import timedelta
    from django.db.models import Count
    import json
    
    videos = YouTubeVideo.objects.filter(user=request.user, is_active=True)
    
    # Calcular métricas
    total_videos = videos.count()
    total_comments = sum(video.youtube_comments.filter(is_reply=False).count() for video in videos)
    total_unread = sum(video.unread_comments_count for video in videos)
    
    # Respuestas pendientes y publicadas
    pending_responses = YouTubeResponse.objects.filter(
        comment__video__user=request.user,
        status='pending'
    ).count()
    
    published_responses = YouTubeResponse.objects.filter(
        comment__video__user=request.user,
        status='published'
    ).count()
    
    # Videos de los últimos 7 días
    seven_days_ago = timezone.now() - timedelta(days=7)
    videos_7d = videos.filter(published_at__gte=seven_days_ago).count()
    
    # Promedio de comentarios por video
    avg_comments = total_comments / total_videos if total_videos > 0 else 0
    
    # === DATOS PARA GRÁFICAS ===
    # Actividad semanal (últimas 4 semanas)
    activity_data = []
    for i in range(3, -1, -1):
        week_start = timezone.now() - timedelta(days=7*i + 7)
        week_end = timezone.now() - timedelta(days=7*i)
        week_videos = videos.filter(published_at__gte=week_start, published_at__lt=week_end).count()
        activity_data.append({
            'week': f'Semana {4-i}',
            'videos': week_videos
        })
    
    # Engagement por video (top 5 videos con más comentarios)
    top_videos = videos.annotate(total_youtube_comments=Count('youtube_comments')).order_by('-total_youtube_comments')[:5]
    engagement_data = [{
        'title': video.title[:30] + '...' if len(video.title) > 30 else video.title,
        'comments': video.youtube_comments.filter(is_reply=False).count()
    } for video in top_videos]
    
    # Tasa de respuesta
    videos_with_responses = videos.filter(youtube_comments__youtube_response__isnull=False).distinct().count()
    response_rate = (videos_with_responses / total_videos * 100) if total_videos > 0 else 0
    
    context = {
        'videos': videos,
        'total_videos': total_videos,
        'total_comments': total_comments,
        'total_unread': total_unread,
        'pending_responses': pending_responses,
        'published_responses': published_responses,
        'videos_7d': videos_7d,
        'avg_comments': round(avg_comments, 2),
        'activity_data': json.dumps(activity_data),
        'engagement_data': json.dumps(engagement_data),
        'response_rate': round(response_rate, 1)
    }
    
    return render(request, 'dashboard/youtube_manager.html', context)

@login_required
def sync_videos_yt(request):
    """Sincroniza videos de YouTube con la base de datos"""
    if request.method == 'POST':
        try:
            bot = YouTubeBot()
            videos_data = bot.get_channel_videos(max_results=25)
            
            synced_count = 0
            for video_data in videos_data:
                video, created = YouTubeVideo.objects.get_or_create(
                    video_id=video_data['video_id'],
                    defaults={
                        'user': request.user,
                        'title': video_data['title'],
                        'description': video_data['description'],
                        'url': video_data['url'],
                        'thumbnail_url': video_data['thumbnail_url'],
                        'channel_title': video_data['channel_title'],
                        'published_at': video_data['published_at'],
                        'view_count': video_data['view_count'],
                        'comment_count': video_data['comment_count']
                    }
                )
                
                # Actualizar estadísticas si ya existe
                if not created:
                    video.view_count = video_data['view_count']
                    video.comment_count = video_data['comment_count']
                    video.save()
                else:
                    synced_count += 1
            
            messages.success(request, f'Se sincronizaron {synced_count} videos nuevos')
            return JsonResponse({
                'success': True,
                'synced_count': synced_count
            })
        except Exception as e:
            logger.error(f"Error al sincronizar videos: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False}, status=400)

@login_required
def video_detail_yt(request, video_id):
    """Vista de comentarios de un video específico"""
    video = get_object_or_404(YouTubeVideo, video_id=video_id, user=request.user)
    comments = video.youtube_comments.filter(is_reply=False).order_by('-published_at')
    
    context = {
        'video': video,
        'comments': comments,
        'comments_count': comments.count()
    }
    
    return render(request, 'dashboard/video_detail_yt.html', context)

@login_required
def sync_comments_yt(request, video_id):
    """Sincroniza comentarios de un video específico"""
    if request.method == 'POST':
        try:
            video = get_object_or_404(YouTubeVideo, video_id=video_id, user=request.user)
            bot = YouTubeBot()
            comments_data = bot.get_video_comments(video_id)
            
            synced_count = 0
            for comment_data in comments_data:
                comment, created = YouTubeComment.objects.get_or_create(
                    comment_id=comment_data['comment_id'],
                    defaults={
                        'video': video,
                        'author': comment_data['author'],
                        'author_channel_id': comment_data['author_channel_id'],
                        'content': comment_data['content'],
                        'like_count': comment_data['like_count'],
                        'parent_id': comment_data['parent_id'],
                        'is_reply': comment_data['is_reply'],
                        'published_at': comment_data['published_at'],
                        'updated_at': comment_data['updated_at']
                    }
                )
                if created:
                    synced_count += 1
            
            return JsonResponse({
                'success': True,
                'synced_count': synced_count
            })
        except Exception as e:
            logger.error(f"Error al sincronizar comentarios: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False}, status=400)

@login_required
def comment_detail_yt(request, comment_id):
    """Vista de detalle de un comentario con opciones de respuesta"""
    comment = get_object_or_404(YouTubeComment, comment_id=comment_id)
    
    # Verificar que el video pertenece al usuario
    if comment.video.user != request.user:
        messages.error(request, 'No tienes permiso para ver este comentario')
        return redirect('youtube_manager')
    
    try:
        response = comment.youtube_response
    except YouTubeResponse.DoesNotExist:
        response = None
    
    context = {
        'comment': comment,
        'response': response,
        'available_tones': ['formal', 'friendly', 'informative']
    }
    
    return render(request, 'dashboard/comment_detail_yt.html', context)

@login_required
def delete_comment_yt(request, comment_id):
    """Elimina un comentario de YouTube y la base de datos"""
    if request.method == 'POST':
        try:
            comment = get_object_or_404(YouTubeComment, comment_id=comment_id)
            
            # Verificar permisos - solo puede eliminar comentarios de sus propios videos
            if comment.video.user != request.user:
                return JsonResponse({
                    'success': False,
                    'error': 'No autorizado'
                }, status=403)
            
            # Eliminar de YouTube
            bot = YouTubeBot()
            success = bot.delete_comment(comment_id)
            
            if success:
                # Eliminar de la base de datos
                video_id = comment.video.video_id
                comment.delete()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Comentario eliminado exitosamente',
                    'video_id': video_id
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Error al eliminar el comentario de YouTube'
                }, status=500)
                
        except Exception as e:
            logger.error(f"Error al eliminar comentario: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False}, status=400)

@login_required
def generate_response_yt(request, comment_id):
    """Genera una respuesta con IA para un comentario de YouTube"""
    if request.method == 'POST':
        try:
            comment = get_object_or_404(YouTubeComment, comment_id=comment_id)
            
            # Verificar permisos
            if comment.video.user != request.user:
                return JsonResponse({
                    'success': False,
                    'error': 'No autorizado'
                }, status=403)
            
            tone = request.POST.get('tone', 'friendly')
            
            # Generar respuesta
            generator = ResponseGenerator()
            generated_text = generator.generate(
                comment_text=comment.content,
                tone=tone,
                context=f"Video: {comment.video.title}"
            )
            
            # Guardar o actualizar respuesta
            response, created = YouTubeResponse.objects.update_or_create(
                comment=comment,
                defaults={
                    'generated_text': generated_text,
                    'tone': tone,
                    'status': 'pending',
                    'edited_text': None
                }
            )
            
            return JsonResponse({
                'success': True,
                'response_text': generated_text,
                'response_id': response.id,
                'tone': tone
            })
            
        except Exception as e:
            logger.error(f"Error al generar respuesta: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False}, status=400)

@login_required
def update_response_yt(request, response_id):
    """Actualiza el texto de una respuesta (edición manual)"""
    if request.method == 'POST':
        try:
            response = get_object_or_404(YouTubeResponse, id=response_id)
            
            # Verificar permisos
            if response.comment.video.user != request.user:
                return JsonResponse({
                    'success': False,
                    'error': 'No autorizado'
                }, status=403)
            
            edited_text = request.POST.get('edited_text', '').strip()
            
            if not edited_text:
                return JsonResponse({
                    'success': False,
                    'error': 'El texto no puede estar vacío'
                }, status=400)
            
            response.edited_text = edited_text
            response.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Respuesta actualizada correctamente'
            })
            
        except Exception as e:
            logger.error(f"Error al actualizar respuesta: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False}, status=400)

@login_required
def publish_response_yt(request, response_id):
    """Publica la respuesta en YouTube"""
    if request.method == 'POST':
        try:
            response = get_object_or_404(YouTubeResponse, id=response_id)
            
            # Verificar permisos
            if response.comment.video.user != request.user:
                return JsonResponse({
                    'success': False,
                    'error': 'No autorizado'
                }, status=403)
            
            # Verificar que no esté ya publicada
            if response.status == 'published':
                return JsonResponse({
                    'success': False,
                    'error': 'Esta respuesta ya fue publicada'
                }, status=400)
            
            # Publicar en YouTube
            bot = YouTubeBot()
            reply_id = bot.reply_to_comment(
                comment_id=response.comment.comment_id,
                text=response.final_text
            )
            
            if reply_id:
                response.youtube_reply_id = reply_id
                response.publish()
                
                messages.success(request, '¡Respuesta publicada exitosamente en YouTube!')
                return JsonResponse({
                    'success': True,
                    'message': 'Respuesta publicada exitosamente',
                    'reply_id': reply_id
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Error al publicar en YouTube'
                }, status=500)
                
        except Exception as e:
            logger.error(f"Error al publicar respuesta: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False}, status=400)

@login_required
def reject_response_yt(request, response_id):
    """Rechaza una respuesta generada"""
    if request.method == 'POST':
        try:
            response = get_object_or_404(YouTubeResponse, id=response_id)
            
            # Verificar permisos
            if response.comment.video.user != request.user:
                return JsonResponse({
                    'success': False,
                    'error': 'No autorizado'
                }, status=403)
            
            response.status = 'rejected'
            response.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Respuesta rechazada'
            })
            
        except Exception as e:
            logger.error(f"Error al rechazar respuesta: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False}, status=400)

@login_required
def authenticate_youtube(request):
    """Vista para iniciar el proceso de autenticación OAuth"""
    try:
        # Esto iniciará el flujo OAuth
        bot = YouTubeBot()
        
        if bot.test_connection():
            messages.success(request, '¡Autenticación exitosa con YouTube!')
            return redirect('youtube_manager')
        else:
            messages.error(request, 'Error en la autenticación')
            return redirect('youtube_manager')
            
    except Exception as e:
        logger.error(f"Error en autenticación: {str(e)}")
        messages.error(request, f'Error: {str(e)}')
        return redirect('youtube_manager')