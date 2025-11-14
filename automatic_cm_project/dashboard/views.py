from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from .models import RedditPost, Comment, Response
from ai_manager.response_generator import ResponseGenerator
from bots.reddit_bot import RedditBot
import logging
from django.core.files.storage import FileSystemStorage
from ai_manager.post_generator import PostGenerator
from .forms import CreatePostForm, GenerateJobPostForm, EditPostForm

logger = logging.getLogger(__name__)

@login_required
def reddit_manager(request):
    """Vista principal - Lista de posts del subreddit"""
    from datetime import timedelta
    from django.db.models import Count
    import json
    
    posts = RedditPost.objects.filter(user=request.user, is_active=True)
    
    # Calcular métricas
    total_posts = posts.count()
    total_comments = sum(post.comments.count() for post in posts)
    total_unread = sum(post.unread_comments_count for post in posts)
    
    # Respuestas pendientes y publicadas
    pending_responses = Response.objects.filter(
        comment__post__user=request.user,
        status='pending'
    ).count()
    
    published_responses = Response.objects.filter(
        comment__post__user=request.user,
        status='published'
    ).count()
    
    # Posts de los últimos 7 días
    seven_days_ago = timezone.now() - timedelta(days=7)
    posts_7d = posts.filter(created_at__gte=seven_days_ago).count()
    
    # Promedio de comentarios por post
    avg_comments = total_comments / total_posts if total_posts > 0 else 0
    
    # === DATOS PARA GRÁFICAS ===
    # Actividad semanal (últimas 4 semanas)
    activity_data = []
    for i in range(3, -1, -1):
        week_start = timezone.now() - timedelta(days=7*i + 7)
        week_end = timezone.now() - timedelta(days=7*i)
        week_posts = posts.filter(created_at__gte=week_start, created_at__lt=week_end).count()
        activity_data.append({
            'week': f'Semana {4-i}',
            'posts': week_posts
        })
    
    # Engagement por post (top 5 posts con más comentarios)
    top_posts = posts.annotate(comment_count=Count('comments')).order_by('-comment_count')[:5]
    engagement_data = [{
        'title': post.title[:30] + '...' if len(post.title) > 30 else post.title,
        'comments': post.comments.count()
    } for post in top_posts]
    
    # Tasa de respuesta
    posts_with_responses = posts.filter(comments__response__isnull=False).distinct().count()
    response_rate = (posts_with_responses / total_posts * 100) if total_posts > 0 else 0
    
    context = {
        'posts': posts,
        'total_posts': total_posts,
        'total_comments': total_comments,
        'total_unread': total_unread,
        'pending_responses': pending_responses,
        'published_responses': published_responses,
        'posts_7d': posts_7d,
        'avg_comments': round(avg_comments, 2),
        'activity_data': json.dumps(activity_data),
        'engagement_data': json.dumps(engagement_data),
        'response_rate': round(response_rate, 1)
    }
    
    return render(request, 'dashboard/reddit_manager.html', context)

@login_required
def sync_posts(request):
    """Sincroniza posts del subreddit con la base de datos"""
    if request.method == 'POST':
        try:
            bot = RedditBot()
            subreddit_name = "ACM_Magneto"
            posts_data = bot.get_subreddit_posts(subreddit_name, limit=25)
            
            synced_count = 0
            for post_data in posts_data:
                post, created = RedditPost.objects.get_or_create(
                    post_id=post_data['post_id'],
                    defaults={
                        'user': request.user,
                        'title': post_data['title'],
                        'url': post_data['url'],
                        'permalink': post_data['permalink'],
                        'subreddit': post_data['subreddit'],
                        'author': post_data['author'],
                        'created_at': post_data['created_at']
                    }
                )
                if created:
                    synced_count += 1
            
            messages.success(request, f'Se sincronizaron {synced_count} posts nuevos')
            return JsonResponse({
                'success': True,
                'synced_count': synced_count
            })
        except Exception as e:
            logger.error(f"Error al sincronizar posts: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False}, status=400)

@login_required
def post_detail(request, post_id):
    """Vista de comentarios de un post específico"""
    post = get_object_or_404(RedditPost, post_id=post_id, user=request.user)
    comments = post.comments.all().order_by('-created_at')
    
    context = {
        'post': post,
        'comments': comments,
        'comments_count': comments.count()
    }
    
    return render(request, 'dashboard/post_detail.html', context)

@login_required
def sync_comments(request, post_id):
    """Sincroniza comentarios de un post específico"""
    if request.method == 'POST':
        try:
            post = get_object_or_404(RedditPost, post_id=post_id, user=request.user)
            bot = RedditBot()
            comments_data = bot.get_post_comments(post_id)
            
            synced_count = 0
            for comment_data in comments_data:
                comment, created = Comment.objects.get_or_create(
                    comment_id=comment_data['comment_id'],
                    defaults={
                        'post': post,
                        'author': comment_data['author'],
                        'content': comment_data['content'],
                        'permalink': comment_data['permalink'],
                        'parent_id': comment_data['parent_id'],
                        'created_at': comment_data['created_at']
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
def comment_detail(request, comment_id):
    """Vista de detalle de un comentario con opciones de respuesta"""
    comment = get_object_or_404(Comment, comment_id=comment_id)
    
    # Verificar que el post pertenece al usuario
    if comment.post.user != request.user:
        messages.error(request, 'No tienes permiso para ver este comentario')
        return redirect('reddit_manager')
    
    try:
        response = comment.response
    except Response.DoesNotExist:
        response = None
    
    context = {
        'comment': comment,
        'response': response,
        'available_tones': ['formal', 'friendly', 'informative']
    }
    
    return render(request, 'dashboard/comment_detail.html', context)

@login_required
def delete_comment(request, comment_id):
    """Elimina un comentario de Reddit y la base de datos"""
    if request.method == 'POST':
        try:
            comment = get_object_or_404(Comment, comment_id=comment_id)
            
            # Verificar permisos - solo puede eliminar comentarios de sus propios posts
            if comment.post.user != request.user:
                return JsonResponse({
                    'success': False,
                    'error': 'No autorizado'
                }, status=403)
            
            post_id = comment.post.post_id
            reddit_deleted = False
            
            # Intentar eliminar el comentario original de Reddit
            try:
                bot = RedditBot()
                reddit_deleted = bot.delete_comment(comment_id)
                if reddit_deleted:
                    logger.info(f"Comentario {comment_id} eliminado de Reddit")
            except Exception as e:
                logger.warning(f"No se pudo eliminar comentario de Reddit: {str(e)}")
            
            # Eliminar la respuesta del bot si existe
            try:
                response = comment.response
                if response and response.reddit_reply_id:
                    try:
                        bot = RedditBot()
                        bot.delete_comment(response.reddit_reply_id)
                        logger.info(f"Respuesta {response.reddit_reply_id} eliminada de Reddit")
                    except Exception as e:
                        logger.warning(f"No se pudo eliminar respuesta de Reddit: {str(e)}")
                    finally:
                        response.delete()
            except Response.DoesNotExist:
                pass
            
            # Eliminar el comentario de la base de datos
            comment.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Comentario eliminado exitosamente',
                'post_id': post_id
            })
                
        except Exception as e:
            logger.error(f"Error al eliminar comentario: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False}, status=400)

@login_required
def generate_response(request, comment_id):
    """Genera una respuesta con IA para un comentario"""
    if request.method == 'POST':
        try:
            comment = get_object_or_404(Comment, comment_id=comment_id)
            
            # Verificar permisos
            if comment.post.user != request.user:
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
                context=f"Post: {comment.post.title}"
            )
            
            # Guardar o actualizar respuesta
            response, created = Response.objects.update_or_create(
                comment=comment,
                defaults={
                    'generated_text': generated_text,
                    'tone': tone,
                    'status': 'pending',
                    'edited_text': None  # Resetear texto editado
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
def update_response(request, response_id):
    """Actualiza el texto de una respuesta (edición manual)"""
    if request.method == 'POST':
        try:
            response = get_object_or_404(Response, id=response_id)
            
            # Verificar permisos
            if response.comment.post.user != request.user:
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
def publish_response(request, response_id):
    """Publica la respuesta en Reddit"""
    if request.method == 'POST':
        try:
            response = get_object_or_404(Response, id=response_id)
            
            # Verificar permisos
            if response.comment.post.user != request.user:
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
            
            # Publicar en Reddit
            bot = RedditBot()
            reply_id = bot.reply_to_comment(
                comment_id=response.comment.comment_id,
                text=response.final_text
            )
            
            if reply_id:
                response.reddit_reply_id = reply_id
                response.publish()
                
                messages.success(request, '¡Respuesta publicada exitosamente en Reddit!')
                return JsonResponse({
                    'success': True,
                    'message': 'Respuesta publicada exitosamente',
                    'reply_id': reply_id
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Error al publicar en Reddit'
                }, status=500)
                
        except Exception as e:
            logger.error(f"Error al publicar respuesta: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False}, status=400)

@login_required
def reject_response(request, response_id):
    """Rechaza una respuesta generada"""
    if request.method == 'POST':
        try:
            response = get_object_or_404(Response, id=response_id)
            
            # Verificar permisos
            if response.comment.post.user != request.user:
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
def create_post_view(request):
    """Vista para crear un nuevo post en Reddit"""
    if request.method == 'POST':
        form = CreatePostForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                bot = RedditBot()
                post_type = form.cleaned_data['post_type']
                image_path = None
                
                # Manejar imagen si es necesario
                if post_type == 'image' and request.FILES.get('image'):
                    fs = FileSystemStorage()
                    image_file = request.FILES['image']
                    filename = fs.save(image_file.name, image_file)
                    image_path = fs.path(filename)
                
                post_data = bot.create_post(
                    subreddit_name=form.cleaned_data['subreddit'],
                    title=form.cleaned_data['title'],
                    content=form.cleaned_data['content'] or '',
                    post_type=post_type,
                    image_path=image_path
                )
                
                if post_data:
                    # Guardar en la base de datos
                    post = RedditPost.objects.create(
                        user=request.user,
                        post_id=post_data['post_id'],
                        title=post_data['title'],
                        url=post_data['url'],
                        permalink=post_data['permalink'],
                        subreddit=form.cleaned_data['subreddit'],
                        author=request.user.username,
                        created_at=post_data['created_at'],
                        is_own_post=True,
                        image=request.FILES.get('image')
                    )
                    
                    messages.success(request, '¡Post creado exitosamente en Reddit!')
                    return redirect('post_detail', post_id=post.post_id)
                else:
                    messages.error(request, 'Error al crear el post en Reddit')
            except Exception as e:
                logger.error(f"Error al crear post: {str(e)}")
                messages.error(request, f'Error: {str(e)}')
    else:
        form = CreatePostForm()
    
    context = {
        'form': form
    }
    
    return render(request, 'dashboard/create_post.html', context)


@login_required
def generate_job_post_view(request):
    """Vista para generar post de empleo con IA"""
    if request.method == 'POST':
        form = GenerateJobPostForm(request.POST)
        if form.is_valid():
            try:
                generator = PostGenerator()
                
                # Procesar requisitos y beneficios
                requirements = None
                if form.cleaned_data['requirements']:
                    requirements = [
                        req.strip().lstrip('-').strip() 
                        for req in form.cleaned_data['requirements'].split('\n') 
                        if req.strip()
                    ]
                
                benefits = None
                if form.cleaned_data['benefits']:
                    benefits = [
                        benefit.strip().lstrip('-').strip() 
                        for benefit in form.cleaned_data['benefits'].split('\n') 
                        if benefit.strip()
                    ]
                
                # Generar post
                generated = generator.generate_job_post(
                    job_title=form.cleaned_data['job_title'],
                    company_name=form.cleaned_data['company_name'],
                    job_type=form.cleaned_data['job_type'],
                    location=form.cleaned_data['location'],
                    salary_range=form.cleaned_data.get('salary_range'),
                    requirements=requirements,
                    benefits=benefits
                )
                
                return JsonResponse({
                    'success': True,
                    'title': generated['title'],
                    'content': generated['content']
                })
                
            except Exception as e:
                logger.error(f"Error al generar post: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=500)
    else:
        form = GenerateJobPostForm()
    
    context = {
        'form': form
    }
    
    return render(request, 'dashboard/generate_job_post.html', context)


@login_required
def edit_post_view(request, post_id):
    """Vista para editar un post"""
    post = get_object_or_404(RedditPost, post_id=post_id, user=request.user)
    
    if not post.can_edit():
        messages.error(request, 'No puedes editar este post')
        return redirect('post_detail', post_id=post_id)
    
    if request.method == 'POST':
        form = EditPostForm(request.POST)
        if form.is_valid():
            try:
                bot = RedditBot()
                success = bot.edit_post(post_id, form.cleaned_data['content'])
                
                if success:
                    messages.success(request, '¡Post editado exitosamente!')
                    return redirect('post_detail', post_id=post_id)
                else:
                    messages.error(request, 'Error al editar el post')
            except Exception as e:
                logger.error(f"Error al editar post: {str(e)}")
                messages.error(request, f'Error: {str(e)}')
    else:
        # Obtener contenido actual del post desde Reddit
        bot = RedditBot()
        try:
            submission = bot.reddit.submission(id=post_id)
            initial_content = submission.selftext
        except:
            initial_content = ""
        
        form = EditPostForm(initial={'content': initial_content})
    
    context = {
        'form': form,
        'post': post
    }
    
    return render(request, 'dashboard/edit_post.html', context)


@login_required
def delete_post_view(request, post_id):
    """Vista para eliminar un post"""
    if request.method == 'POST':
        try:
            post = get_object_or_404(RedditPost, post_id=post_id, user=request.user)
            
            if not post.can_delete():
                return JsonResponse({
                    'success': False,
                    'error': 'No puedes eliminar este post'
                }, status=403)
            
            bot = RedditBot()
            success = bot.delete_post(post_id)
            
            if success:
                post.delete()  # Eliminar de la BD también
                return JsonResponse({
                    'success': True,
                    'message': 'Post eliminado exitosamente'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Error al eliminar el post'
                }, status=500)
                
        except Exception as e:
            logger.error(f"Error al eliminar post: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False}, status=400)