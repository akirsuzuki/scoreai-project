"""
お知らせ機能のビュー（ブログ記事を表示）
"""
from typing import Any, Dict
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin

from ..models import Blog, BlogCategory
from ..mixins import SelectedCompanyMixin


class AnnouncementListView(SelectedCompanyMixin, LoginRequiredMixin, ListView):
    """お知らせ一覧（ログイン必須）"""
    model = Blog
    template_name = 'scoreai/announcement/list.html'
    context_object_name = 'announcements'
    paginate_by = 10
    
    def get_queryset(self):
        """公開済みのブログのみを取得"""
        # 下書きでないブログを取得
        queryset = Blog.objects.filter(is_draft=False).select_related('written_by').prefetch_related('categories').order_by('-post_date', '-created_at')
        
        # カテゴリーでフィルタリング
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(categories__slug=category_slug)
        
        # 検索機能
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(article__icontains=search_query)
            )
        
        return queryset.distinct()
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Blog'
        context['categories'] = BlogCategory.objects.filter(is_active=True).order_by('order', 'name')
        context['selected_category'] = self.request.GET.get('category', '')
        context['search_query'] = self.request.GET.get('q', '')
        return context


class AnnouncementDetailView(SelectedCompanyMixin, LoginRequiredMixin, DetailView):
    """お知らせ詳細（ログイン必須）"""
    model = Blog
    template_name = 'scoreai/announcement/detail.html'
    context_object_name = 'announcement'
    
    def get_queryset(self):
        """公開済みのブログのみを取得"""
        return Blog.objects.filter(is_draft=False).select_related('written_by').prefetch_related('categories')
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """コンテキストデータの取得"""
        context = super().get_context_data(**kwargs)
        announcement = self.object
        context['title'] = announcement.title
        
        # 関連記事（同じカテゴリーの最新記事）
        if announcement.categories.exists():
            category_ids = announcement.categories.values_list('id', flat=True)
            related_announcements = Blog.objects.filter(
                categories__id__in=category_ids,
                is_draft=False
            ).exclude(id=announcement.id).distinct().order_by('-post_date')[:5]
            context['related_announcements'] = related_announcements
        
        # 最新記事
        context['recent_announcements'] = Blog.objects.filter(
            is_draft=False
        ).exclude(id=announcement.id).order_by('-post_date')[:5]
        
        return context

