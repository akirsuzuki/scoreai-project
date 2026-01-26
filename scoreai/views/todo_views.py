"""
To Do機能のビュー
"""
from typing import Any, Dict
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views import generic
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q
import logging

from ..mixins import SelectedCompanyMixin
from ..models import Todo, TodoCategory, UserCompany
from ..forms import TodoForm

logger = logging.getLogger(__name__)


class TodoListView(SelectedCompanyMixin, generic.ListView):
    """To Do一覧ビュー"""
    model = Todo
    template_name = 'scoreai/todo_list.html'
    context_object_name = 'todos'
    paginate_by = 20

    def get_queryset(self):
        """選択中の会社のTo Doのみ取得"""
        queryset = Todo.objects.filter(
            company=self.this_company
        ).select_related('created_by').prefetch_related('categories')

        # フィルタリング
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        priority = self.request.GET.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)

        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(categories__id=category)

        # 検索
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(content__icontains=search)
            )

        # ソート
        sort = self.request.GET.get('sort', '-created_at')
        if sort in ['due_date', '-due_date', 'created_at', '-created_at', 'priority', '-priority']:
            queryset = queryset.order_by(sort)

        return queryset

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = 'To Do一覧'
        context['categories'] = TodoCategory.objects.filter(is_active=True)
        context['status_choices'] = Todo.STATUS_CHOICES
        context['priority_choices'] = Todo.PRIORITY_CHOICES
        context['current_filters'] = {
            'status': self.request.GET.get('status', ''),
            'priority': self.request.GET.get('priority', ''),
            'category': self.request.GET.get('category', ''),
            'search': self.request.GET.get('search', ''),
            'sort': self.request.GET.get('sort', '-created_at'),
        }
        # 統計情報
        all_todos = Todo.objects.filter(company=self.this_company)
        context['stats'] = {
            'total': all_todos.count(),
            'pending': all_todos.filter(status='pending').count(),
            'in_progress': all_todos.filter(status='in_progress').count(),
            'completed': all_todos.filter(status='completed').count(),
            'overdue': all_todos.filter(
                due_date__lt=timezone.now().date(),
                status__in=['pending', 'in_progress']
            ).count(),
        }
        return context


class TodoCreateView(SelectedCompanyMixin, generic.CreateView):
    """To Do作成ビュー"""
    model = Todo
    form_class = TodoForm
    template_name = 'scoreai/todo_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.this_company
        return kwargs

    def form_valid(self, form):
        form.instance.company = self.this_company
        form.instance.created_by = self.request.user
        messages.success(self.request, 'To Doを作成しました。')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('todo_list')

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = 'To Do作成'
        context['is_edit'] = False
        return context


class TodoUpdateView(SelectedCompanyMixin, generic.UpdateView):
    """To Do編集ビュー"""
    model = Todo
    form_class = TodoForm
    template_name = 'scoreai/todo_form.html'

    def get_queryset(self):
        """選択中の会社のTo Doのみ編集可能"""
        return Todo.objects.filter(company=self.this_company)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.this_company
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'To Doを更新しました。')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('todo_list')

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = 'To Do編集'
        context['is_edit'] = True
        return context


class TodoDeleteView(SelectedCompanyMixin, generic.DeleteView):
    """To Do削除ビュー"""
    model = Todo
    template_name = 'scoreai/todo_confirm_delete.html'
    success_url = reverse_lazy('todo_list')

    def get_queryset(self):
        """選択中の会社のTo Doのみ削除可能"""
        return Todo.objects.filter(company=self.this_company)

    def form_valid(self, form):
        messages.success(self.request, 'To Doを削除しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = 'To Do削除'
        return context


class TodoDetailView(SelectedCompanyMixin, generic.DetailView):
    """To Do詳細ビュー"""
    model = Todo
    template_name = 'scoreai/todo_detail.html'
    context_object_name = 'todo'

    def get_queryset(self):
        """選択中の会社のTo Doのみ表示"""
        return Todo.objects.filter(
            company=self.this_company
        ).select_related('created_by').prefetch_related('categories')

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = self.object.title
        return context


class TodoStatusUpdateView(SelectedCompanyMixin, generic.View):
    """To Doステータス更新"""

    def post(self, request, pk):
        todo = get_object_or_404(Todo, pk=pk, company=self.this_company)
        new_status = request.POST.get('status')

        if new_status in dict(Todo.STATUS_CHOICES):
            todo.status = new_status
            todo.save()
            
            # AJAXリクエストの場合はJSONを返す
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'status': todo.status,
                    'status_display': todo.get_status_display(),
                    'completed_at': todo.completed_at.isoformat() if todo.completed_at else None
                })
            
            # 通常のフォーム送信の場合はリダイレクト
            status_display = todo.get_status_display()
            messages.success(request, f'To Doのステータスを「{status_display}」に更新しました。')
            return redirect('todo_detail', pk=pk)

        # エラーの場合
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': '無効なステータスです。'}, status=400)
        
        messages.error(request, '無効なステータスです。')
        return redirect('todo_detail', pk=pk)
