"""
SCore_AIについて - リンク集ビュー
"""
from django.views.generic import TemplateView
from ..mixins import SelectedCompanyMixin


class AboutLinksView(SelectedCompanyMixin, TemplateView):
    """SCore_AIについて - リンク集ページ"""
    template_name = 'scoreai/about_links.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'SCore_AIについて'
        return context

