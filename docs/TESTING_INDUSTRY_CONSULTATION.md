# 業界別相談室の動作確認手順

## 変更内容の概要

1. `IndustryCategory`と`IndustryConsultationType`モデルを削除
2. `IzakayaPlan`モデルに`industry_classification`フィールドを追加
3. `IndustryClassification`を直接使用するように変更

## 動作確認手順

### 1. マイグレーション実行前の確認

現在、マイグレーションが未実行の状態です。以下のエラーが発生する可能性があります：

- `IndustryCategory`や`IndustryConsultationType`への参照エラー
- `IzakayaPlan`に`industry_classification`フィールドが存在しないエラー

### 2. 動作確認のための準備

#### 2.1 マイグレーションの作成と実行

```bash
python manage.py makemigrations scoreai
python manage.py migrate
```

#### 2.2 データベースの確認

- `IndustryClassification`にデータが存在することを確認
- 飲食業界の分類が存在することを確認（コードが"56"で始まる、または名前に"飲食"または"外食"が含まれる）

### 3. 動作確認項目

#### 3.1 業界別相談室トップページ

**URL**: `/ai-consultation/industry/`

**確認項目**:
- [ ] ページが正常に表示される
- [ ] `IndustryClassification`の一覧が表示される
- [ ] 各業界分類に「詳細を見る」ボタンが表示される
- [ ] 業界分類がない場合、適切なメッセージが表示される

#### 3.2 業界分類詳細ページ

**URL**: `/ai-consultation/industry/<classification_id>/`

**確認項目（飲食業界の場合）**:
- [ ] ページが正常に表示される
- [ ] 「居酒屋出店計画作成」カードが表示される
- [ ] 「始める」ボタンが表示される
- [ ] ボタンをクリックすると、居酒屋出店計画作成ページに遷移する

**確認項目（飲食業界以外の場合）**:
- [ ] ページが正常に表示される
- [ ] 「まだ計画テンプレートがありません」メッセージが表示される

#### 3.3 居酒屋出店計画作成ページ

**URL**: `/ai-consultation/industry/<classification_id>/izakaya-plan/create/`

**確認項目**:
- [ ] ページが正常に表示される
- [ ] フォームが正常に表示される
- [ ] 計画を作成すると、`industry_classification`が正しく設定される
- [ ] 作成後、プレビューページに遷移する

#### 3.4 既存の居酒屋出店計画

**確認項目**:
- [ ] 既存の計画が正常に表示される
- [ ] 更新・削除が正常に動作する
- [ ] `industry_classification`がnullでも動作する（後方互換性）

### 4. 既知の問題

#### 4.1 設定画面のエラー

`scoreai/views/industry_consultation_settings_views.py`にまだ`IndustryCategory`と`IndustryConsultationType`への参照が残っています。設定画面にアクセスするとエラーが発生する可能性があります。

**対処方法**:
- 設定画面へのアクセスを一時的に無効化する
- または、設定画面のコードを修正する

#### 4.2 管理コマンドのエラー

`scoreai/management/commands/init_industry_consultation.py`にまだ`IndustryCategory`と`IndustryConsultationType`への参照が残っています。

**対処方法**:
- 管理コマンドを実行しない
- または、管理コマンドのコードを修正する

### 5. テストデータの準備

#### 5.1 IndustryClassificationの作成

Django管理画面または以下のコマンドで作成：

```python
from scoreai.models import IndustryClassification

# 飲食業界の分類を作成（例）
IndustryClassification.objects.create(
    name='飲食業',
    code='560000',
    memo='飲食業界向けの相談室'
)
```

### 6. エラーが発生した場合の対処

#### 6.1 マイグレーションエラー

- 既存の`IndustryCategory`や`IndustryConsultationType`のデータがある場合、マイグレーション前に削除する必要があります
- または、マイグレーションでデータを移行する処理を追加する

#### 6.2 テンプレートエラー

- テンプレートの変数名が正しいか確認
- `classification`と`classifications`の使い分けを確認

#### 6.3 URLエラー

- URLパターンが正しいか確認
- `classification_id`が整数型で正しく渡されているか確認

## 次のステップ

動作確認が完了したら：

1. 設定画面のコードを修正
2. 管理コマンドのコードを修正
3. Admin画面の設定を修正
4. 不要なファイルの削除

