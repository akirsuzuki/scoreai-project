from django.apps import AppConfig


class ScoreaiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scoreai' # 元々はこれ
    # name = 'score.scoreai' # これだとDeployでエラー
    # name = 'src.score.scoreai' # これだとDeployでエラー