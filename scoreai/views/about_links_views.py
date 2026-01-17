"""
SCore_AIについて - リンク集ビュー
"""
from django.views.generic import TemplateView
from ..mixins import SelectedCompanyMixin
from ..models import FirmPlan


class AboutLinksView(SelectedCompanyMixin, TemplateView):
    """SCore_AIについて - リンク集ページ"""
    template_name = 'scoreai/about_links.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'SCore_AIについて'
        context['show_title_card'] = False  # タイトルカードを非表示（他のページと統一）
        # 有効なプラン一覧を取得（Supportセクションで使用）
        context['plans'] = FirmPlan.objects.filter(is_active=True).order_by('order', 'plan_type')
        return context

