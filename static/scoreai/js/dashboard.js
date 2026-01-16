/**
 * ダッシュボード KPIカードの表示（アニメーションなし）
 */

// ページ読み込み時にKPIカードの値を設定
document.addEventListener('DOMContentLoaded', function () {
  // 各KPIカードの値を設定
  const kpiValues = document.querySelectorAll('.kpi-value[data-target]');

  kpiValues.forEach((element) => {
    const targetValue = parseFloat(element.getAttribute('data-target')) || 0;
    const suffix = element.getAttribute('data-suffix') || '';
    const isPercentage = element.getAttribute('data-type') === 'percentage';

    // 値を直接設定
    if (isPercentage) {
      element.textContent = targetValue.toFixed(2) + '%';
    } else {
      element.textContent = targetValue.toLocaleString('ja-JP') + suffix;
    }
  });

  // 前年比の計算と表示
  const trendBadges = document.querySelectorAll('.kpi-trend-badge[data-current][data-previous]');
  trendBadges.forEach((badge) => {
    const current = parseFloat(badge.getAttribute('data-current')) || 0;
    const previous = parseFloat(badge.getAttribute('data-previous')) || 0;

    if (previous === 0) {
      badge.style.display = 'none';
      return;
    }

    const ratio = (current / previous) * 100;
    const change = ratio - 100;
    const changeAbs = Math.abs(change);

    // バッジのクラスを更新
    badge.className = 'kpi-trend-badge';
    if (change > 0) {
      badge.classList.add('success');
      badge.innerHTML = `<i class="ti ti-arrow-up"></i> +${changeAbs.toFixed(1)}% 前年比`;
    } else if (change < 0) {
      badge.classList.add('danger');
      badge.innerHTML = `<i class="ti ti-arrow-down"></i> ${changeAbs.toFixed(1)}% 前年比`;
    } else {
      badge.classList.add('warning');
      badge.innerHTML = `<i class="ti ti-minus"></i> 0% 前年比`;
    }
  });
});
