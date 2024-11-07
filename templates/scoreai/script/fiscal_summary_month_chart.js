<script>
  const monthlySummaries = {{ monthly_summaries|safe }}.reverse();
  const monthsLabel = {{ months_label|safe }};
  const salesData = [];
  const grossProfitData = [];
  const operatingProfitData = [];

  monthlySummaries.forEach(summary => {
    const monthlySales = new Array(12).fill(0);
    const monthlyGrossProfit = new Array(12).fill(0);
    const monthlyOperatingProfit = new Array(12).fill(0);

    summary.data.forEach(month => {
      if (month.period) {
        monthlySales[month.period - 1] = month.sales;
        monthlyGrossProfit[month.period - 1] = month.gross_profit;
        monthlyOperatingProfit[month.period - 1] = month.operating_profit;
      }
    });

    salesData.push({
      label: `${summary.year} 売上高`,
      data: monthlySales,
      borderColor: 'rgba(75, 192, 192, 1)',
      fill: false,
    });

    grossProfitData.push({
      label: `${summary.year} 粗利益`,
      data: monthlyGrossProfit,
      borderColor: 'rgba(255, 99, 132, 1)',
      fill: false,
    });

    operatingProfitData.push({
      label: `${summary.year} 営業利益`,
      data: monthlyOperatingProfit,
      borderColor: 'rgba(255, 206, 86, 1)',
      fill: false,
    });
  });

  const ctx = document.getElementById('salesChart').getContext('2d');
  const salesChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: monthsLabel,
      datasets: salesData, // 初期データは売上のみ
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true
        }
      }
    }
  });
  updateChart();
  // チェックボックスのイベントリスナー
  document.getElementById('showGrossProfit').addEventListener('change', function() {
    updateChart();
  });

  document.getElementById('showOperatingProfit').addEventListener('change', function() {
    updateChart();
  });

  function updateChart() {
    const datasets = [...salesData]; // 売上データを常に含める
    // 年ごとのスタイル設定
    // スタイル設定を関数に抽出
    const setStyle = (dataArray) => {
        dataArray.forEach((data, dataIndex) => {
            if (dataIndex === 0) {
              data.borderDash = [2, 3]; // 点線
              data.borderWidth = 0; // 次の年は普通の直線
            } else if (dataIndex === 1) {
                data.borderWidth = 0; // 次の年は普通の直線
                data.backgroundColor = data.borderColor.replace('rgba', 'rgba(90, 90, 90, 0.6)');
            } else {
              data.borderWidth = 3; // 最新の年は太線
              data.backgroundColor = data.borderColor; // 同じ色で塗りつぶす
            }
        });
    };

    
    setStyle(datasets); // 売上データのスタイル設定

    if (document.getElementById('showGrossProfit').checked) {
        setStyle(grossProfitData); // 粗利益データのスタイル設定
        grossProfitData.forEach(data => data.type = 'line'); // 粗利益をラインチャートに変更
        datasets.push(...grossProfitData); // 粗利益データを追加
    }

    if (document.getElementById('showOperatingProfit').checked) {
        setStyle(operatingProfitData); // 営業利益データのスタイル設定
        operatingProfitData.forEach(data => data.type = 'line'); // 営業利益をラインチャートに変更
        datasets.push(...operatingProfitData); // 営業利益データを追加
    }

    salesChart.data.datasets = datasets;
    salesChart.update(); // チャートを更新
  }
</script>
