"""
django-filterを使用したフィルタリング機能
"""
import django_filters
from .models import Debt, FiscalSummary_Year, FiscalSummary_Month


class DebtFilter(django_filters.FilterSet):
    """借入データのフィルタリング"""
    search = django_filters.CharFilter(
        method='filter_search',
        label='検索',
        help_text='金融機関名、保証協会名で検索'
    )
    financial_institution = django_filters.ModelChoiceFilter(
        queryset=None,
        label='金融機関',
        empty_label='すべて'
    )
    secured_type = django_filters.ModelChoiceFilter(
        queryset=None,
        label='保証協会',
        empty_label='すべて'
    )
    is_rescheduled = django_filters.BooleanFilter(
        label='リスケ',
        widget=django_filters.widgets.BooleanWidget()
    )
    is_nodisplay = django_filters.BooleanFilter(
        label='非表示',
        widget=django_filters.widgets.BooleanWidget()
    )
    is_securedby_management = django_filters.BooleanFilter(
        label='経営者保証',
        widget=django_filters.widgets.BooleanWidget()
    )
    is_collateraled = django_filters.BooleanFilter(
        label='担保',
        widget=django_filters.widgets.BooleanWidget()
    )
    issue_date = django_filters.DateFromToRangeFilter(
        label='実行日',
        help_text='実行日の範囲でフィルタ'
    )
    start_date = django_filters.DateFromToRangeFilter(
        label='返済開始日',
        help_text='返済開始日の範囲でフィルタ'
    )
    
    class Meta:
        model = Debt
        fields = [
            'search',
            'financial_institution',
            'secured_type',
            'is_rescheduled',
            'is_nodisplay',
            'is_securedby_management',
            'is_collateraled',
            'issue_date',
            'start_date',
        ]
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        # 金融機関と保証協会のクエリセットを設定
        if company:
            from .models import FinancialInstitution, SecuredType
            self.filters['financial_institution'].queryset = FinancialInstitution.objects.all().order_by('name')
            self.filters['secured_type'].queryset = SecuredType.objects.all().order_by('name')
    
    def filter_search(self, queryset, name, value):
        """検索フィルタ（金融機関名、保証協会名）"""
        from django.db.models import Q
        if value:
            return queryset.filter(
                Q(financial_institution__name__icontains=value) |
                Q(financial_institution__short_name__icontains=value) |
                Q(secured_type__name__icontains=value)
            )
        return queryset


class FiscalSummaryYearFilter(django_filters.FilterSet):
    """決算年次データのフィルタリング"""
    year = django_filters.NumberFilter(
        label='年度',
        lookup_expr='exact'
    )
    year_range = django_filters.RangeFilter(
        field_name='year',
        label='年度範囲'
    )
    is_draft = django_filters.BooleanFilter(
        label='下書き',
        widget=django_filters.widgets.BooleanWidget()
    )
    is_budget = django_filters.BooleanFilter(
        label='予算',
        widget=django_filters.widgets.BooleanWidget()
    )
    
    class Meta:
        model = FiscalSummary_Year
        fields = ['year', 'year_range', 'is_draft', 'is_budget']


class FiscalSummaryMonthFilter(django_filters.FilterSet):
    """決算月次データのフィルタリング"""
    fiscal_summary_year = django_filters.ModelChoiceFilter(
        queryset=None,
        label='年度',
        empty_label='すべて'
    )
    period = django_filters.NumberFilter(
        label='月度',
        lookup_expr='exact'
    )
    period_range = django_filters.RangeFilter(
        field_name='period',
        label='月度範囲'
    )
    is_budget = django_filters.BooleanFilter(
        label='予算',
        widget=django_filters.widgets.BooleanWidget()
    )
    
    class Meta:
        model = FiscalSummary_Month
        fields = ['fiscal_summary_year', 'period', 'period_range', 'is_budget']
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        # 年度のクエリセットを設定
        if company:
            from .models import FiscalSummary_Year
            self.filters['fiscal_summary_year'].queryset = FiscalSummary_Year.objects.filter(
                company=company
            ).order_by('-year')

