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
    posts = RedditPost.objects.filter(user=request.user, is_active=True)
    
    context = {
        'posts': posts,
        'total_posts': posts.count(),
        'total_unread': sum(post.unread_comments_count for post in posts)
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