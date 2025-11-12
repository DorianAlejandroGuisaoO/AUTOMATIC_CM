from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class RedditPost(models.Model):
    """Post de Reddit que se está monitoreando"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reddit_posts')
    post_id = models.CharField(max_length=100, unique=True)
    title = models.TextField()
    url = models.URLField()
    permalink = models.URLField()
    subreddit = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    created_at = models.DateTimeField()
    last_checked = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    is_own_post = models.BooleanField(default=False)  # Para identificar posts creados por la app
    image = models.ImageField(upload_to='reddit_images/', null=True, blank=True)  # Para imágenes
    
    def can_edit(self):
        """Verifica si el post puede ser editado"""
        return self.is_own_post and self.author == self.user.username
    
    def can_delete(self):
        """Verifica si el post puede ser eliminado"""
        return self.is_own_post
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Reddit Post'
        verbose_name_plural = 'Reddit Posts'
    
    @property
    def unread_comments_count(self):
        """Cuenta comentarios sin respuesta o pendientes"""
        return self.comments.filter(
            models.Q(response__isnull=True) | 
            models.Q(response__status='pending')
        ).count()
    
    def __str__(self):
        return f"{self.title[:50]}..."

class Comment(models.Model):
    """Comentario en un post de Reddit"""
    post = models.ForeignKey(RedditPost, on_delete=models.CASCADE, related_name='comments')
    comment_id = models.CharField(max_length=100, unique=True)
    author = models.CharField(max_length=100)
    content = models.TextField()
    permalink = models.URLField()
    parent_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField()
    fetched_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Comment'
        verbose_name_plural = 'Comments'
    
    @property
    def status_badge(self):
        """Retorna el estado visual del comentario"""
        try:
            if self.response.status == 'published':
                return {'text': 'Publicado', 'class': 'status-published'}
            elif self.response.status == 'pending':
                return {'text': 'Pendiente', 'class': 'status-pending'}
            elif self.response.status == 'rejected':
                return {'text': 'Rechazado', 'class': 'status-rejected'}
        except Response.DoesNotExist:
            return {'text': 'Nuevo', 'class': 'status-new'}
    
    def __str__(self):
        return f"Comment by {self.author} on {self.post.title[:30]}"

class Response(models.Model):
    """Respuesta generada por IA para un comentario"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        PUBLISHED = 'published', 'Publicado'
        REJECTED = 'rejected', 'Rechazado'
    
    class Tone(models.TextChoices):
        FORMAL = 'formal', 'Formal'
        FRIENDLY = 'friendly', 'Amigable'
        INFORMATIVE = 'informative', 'Informativo'
    
    comment = models.OneToOneField(Comment, on_delete=models.CASCADE, related_name='response')
    generated_text = models.TextField()
    tone = models.CharField(max_length=20, choices=Tone.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    edited_text = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    reddit_reply_id = models.CharField(max_length=100, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Response'
        verbose_name_plural = 'Responses'
    
    @property
    def final_text(self):
        """Retorna el texto editado o el generado"""
        return self.edited_text if self.edited_text else self.generated_text
    
    def publish(self):
        """Marca la respuesta como publicada"""
        self.status = self.Status.PUBLISHED
        self.published_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"Response to {self.comment.author} - {self.status}"
    
class YouTubeVideo(models.Model):
    """Video de YouTube que se está monitoreando"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='youtube_videos')
    video_id = models.CharField(max_length=100, unique=True)
    title = models.TextField()
    description = models.TextField(blank=True)
    url = models.URLField()
    thumbnail_url = models.URLField()
    channel_title = models.CharField(max_length=255)
    published_at = models.DateTimeField()
    view_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    last_checked = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-published_at']
        verbose_name = 'YouTube Video'
        verbose_name_plural = 'YouTube Videos'
    
    @property
    def unread_comments_count(self):
        """Cuenta comentarios sin respuesta o pendientes"""
        return self.youtube_comments.filter(
            models.Q(youtube_response__isnull=True) | 
            models.Q(youtube_response__status='pending')
        ).count()
    
    def __str__(self):
        return f"{self.title[:50]}..."


class YouTubeComment(models.Model):
    """Comentario en un video de YouTube"""
    video = models.ForeignKey(YouTubeVideo, on_delete=models.CASCADE, related_name='youtube_comments')
    comment_id = models.CharField(max_length=100, unique=True)
    author = models.CharField(max_length=255)
    author_channel_id = models.CharField(max_length=100, blank=True)
    content = models.TextField()
    like_count = models.IntegerField(default=0)
    parent_id = models.CharField(max_length=100, null=True, blank=True)
    is_reply = models.BooleanField(default=False)
    published_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    fetched_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-published_at']
        verbose_name = 'YouTube Comment'
        verbose_name_plural = 'YouTube Comments'
    
    @property
    def status_badge(self):
        """Retorna el estado visual del comentario"""
        try:
            if self.youtube_response.status == 'published':
                return {'text': 'Publicado', 'class': 'status-published'}
            elif self.youtube_response.status == 'pending':
                return {'text': 'Pendiente', 'class': 'status-pending'}
            elif self.youtube_response.status == 'rejected':
                return {'text': 'Rechazado', 'class': 'status-rejected'}
        except YouTubeResponse.DoesNotExist:
            return {'text': 'Nuevo', 'class': 'status-new'}
    
    def __str__(self):
        return f"Comment by {self.author} on {self.video.title[:30]}"


class YouTubeResponse(models.Model):
    """Respuesta generada por IA para un comentario de YouTube"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        PUBLISHED = 'published', 'Publicado'
        REJECTED = 'rejected', 'Rechazado'
    
    class Tone(models.TextChoices):
        FORMAL = 'formal', 'Formal'
        FRIENDLY = 'friendly', 'Amigable'
        INFORMATIVE = 'informative', 'Informativo'
    
    comment = models.OneToOneField(YouTubeComment, on_delete=models.CASCADE, related_name='youtube_response')
    generated_text = models.TextField()
    tone = models.CharField(max_length=20, choices=Tone.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    edited_text = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    youtube_reply_id = models.CharField(max_length=100, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'YouTube Response'
        verbose_name_plural = 'YouTube Responses'
    
    @property
    def final_text(self):
        """Retorna el texto editado o el generado"""
        return self.edited_text if self.edited_text else self.generated_text
    
    def publish(self):
        """Marca la respuesta como publicada"""
        self.status = self.Status.PUBLISHED
        self.published_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"Response to {self.comment.author} - {self.status}"