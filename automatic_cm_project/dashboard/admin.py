from django.contrib import admin
from .models import RedditPost, Comment, Response


@admin.register(RedditPost)
class RedditPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'subreddit', 'author', 'created_at', 'is_active', 'unread_comments_count')
    list_filter = ('subreddit', 'is_active', 'created_at')
    search_fields = ('title', 'author', 'post_id')
    readonly_fields = ('post_id', 'created_at', 'last_checked')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'created_at', 'get_status')
    list_filter = ('created_at', 'fetched_at')
    search_fields = ('author', 'content', 'comment_id')
    readonly_fields = ('comment_id', 'created_at', 'fetched_at')

    def get_status(self, obj):
        try:
            badge = getattr(obj, "status_badge", None)
            return badge["text"] if badge else "Desconocido"
        except Exception:
            return "Desconocido"

    get_status.short_description = 'Estado'


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ('comment', 'tone', 'status', 'created_at', 'published_at')
    list_filter = ('status', 'tone', 'created_at')
    search_fields = ('generated_text', 'edited_text')
    readonly_fields = ('created_at', 'published_at', 'reddit_reply_id')


from .models import YouTubeVideo, YouTubeComment, YouTubeResponse

@admin.register(YouTubeVideo)
class YouTubeVideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'channel_title', 'published_at', 'view_count', 'comment_count', 'is_active')
    list_filter = ('is_active', 'published_at')
    search_fields = ('title', 'video_id', 'channel_title')
    readonly_fields = ('video_id', 'published_at', 'last_checked')

@admin.register(YouTubeComment)
class YouTubeCommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'video', 'published_at', 'like_count', 'get_status')
    list_filter = ('is_reply', 'published_at')
    search_fields = ('author', 'content', 'comment_id')
    readonly_fields = ('comment_id', 'published_at', 'fetched_at')
    
    def get_status(self, obj):
        return obj.status_badge['text']
    get_status.short_description = 'Estado'

@admin.register(YouTubeResponse)
class YouTubeResponseAdmin(admin.ModelAdmin):
    list_display = ('comment', 'tone', 'status', 'created_at', 'published_at')
    list_filter = ('status', 'tone', 'created_at')
    search_fields = ('generated_text', 'edited_text')
    readonly_fields = ('created_at', 'published_at', 'youtube_reply_id')