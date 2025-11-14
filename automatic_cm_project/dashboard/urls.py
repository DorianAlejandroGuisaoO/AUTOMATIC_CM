from django.urls import path
from . import views
from . import views_youtube  # Importar vistas de YouTube

urlpatterns = [
    # ===== REDDIT =====
    # Vista principal
    path('reddit/', views.reddit_manager, name='reddit_manager'),
    
    # Sincronización
    path('reddit/sync-posts/', views.sync_posts, name='sync_posts'),
    path('reddit/post/<str:post_id>/sync-comments/', views.sync_comments, name='sync_comments'),
    
    # Posts y comentarios
    path('reddit/post/<str:post_id>/', views.post_detail, name='post_detail'),
    path('reddit/comment/<str:comment_id>/', views.comment_detail, name='comment_detail'),
    path('reddit/comment/<str:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    
    # Crear, editar y eliminar posts
    path('reddit/create-post/', views.create_post_view, name='create_post'),
    path('reddit/generate-job-post/', views.generate_job_post_view, name='generate_job_post'),
    path('reddit/post/<str:post_id>/edit/', views.edit_post_view, name='edit_post'),
    path('reddit/post/<str:post_id>/delete/', views.delete_post_view, name='delete_post'),
    
    # Generación y gestión de respuestas
    path('reddit/comment/<str:comment_id>/generate/', views.generate_response, name='generate_response'),
    path('reddit/response/<int:response_id>/update/', views.update_response, name='update_response'),
    path('reddit/response/<int:response_id>/publish/', views.publish_response, name='publish_response'),
    path('reddit/response/<int:response_id>/reject/', views.reject_response, name='reject_response'),
    
    # ===== YOUTUBE =====
    # Vista principal
    path('youtube/', views_youtube.youtube_manager, name='youtube_manager'),
    path('youtube/authenticate/', views_youtube.authenticate_youtube, name='authenticate_youtube'),
    
    # Sincronización
    path('youtube/sync-videos/', views_youtube.sync_videos_yt, name='sync_videos_yt'),
    path('youtube/video/<str:video_id>/sync-comments/', views_youtube.sync_comments_yt, name='sync_comments_yt'),
    
    # Videos y comentarios
    path('youtube/video/<str:video_id>/', views_youtube.video_detail_yt, name='video_detail_yt'),
    path('youtube/comment/<str:comment_id>/', views_youtube.comment_detail_yt, name='comment_detail_yt'),
    path('youtube/comment/<str:comment_id>/delete/', views_youtube.delete_comment_yt, name='delete_comment_yt'),
    
    # Generación y gestión de respuestas
    path('youtube/comment/<str:comment_id>/generate/', views_youtube.generate_response_yt, name='generate_response_yt'),
    path('youtube/response/<int:response_id>/update/', views_youtube.update_response_yt, name='update_response_yt'),
    path('youtube/response/<int:response_id>/publish/', views_youtube.publish_response_yt, name='publish_response_yt'),
    path('youtube/response/<int:response_id>/reject/', views_youtube.reject_response_yt, name='reject_response_yt'),
]