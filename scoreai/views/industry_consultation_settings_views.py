"""
業界別相談室設定管理のビュー（Companyのmanager用）
"""
# IndustryCategoryとIndustryConsultationTypeは削除されました
# 設定画面は今後、IndustryClassificationを直接使用するように変更予定
# 現在は設定画面のビューを無効化しています

from ..mixins import SelectedCompanyMixin

# ダミークラス（urls.pyのインポートエラーを防ぐため）
# IndustryCategoryとIndustryConsultationTypeが削除されたため、これらのビューは使用できません
# 将来的にIndustryClassificationを直接管理するビューに置き換える予定

class IndustryCategoryListView:
    pass

class IndustryCategoryCreateView:
    pass

class IndustryCategoryUpdateView:
    pass

class IndustryCategoryDeleteView:
    pass

class IndustryConsultationTypeListView:
    pass

class IndustryConsultationTypeCreateView:
    pass

class IndustryConsultationTypeUpdateView:
    pass

class IndustryConsultationTypeDeleteView:
    pass
