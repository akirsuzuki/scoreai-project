<script>
  const monthlySummaries = {{ monthly_summaries_json|safe }}.reverse();
  const monthsLabel = {{ months_label_json|safe }};
  const budgetChartData = {{ budget_chart_data_json|safe }};
  const actualChartData = {{ actual_chart_data_json|safe }};
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
  
  // 予算データを追加（最新年度の予算のみ）
  const latestYear = {% if latest_year %}{{ latest_year }}{% else %}null{% endif %};
  const budgetYear = latestYear || (monthlySummaries.length > 0 ? monthlySummaries[0].year : null);
  if (budgetYear && budgetChartData && (budgetChartData.sales.some(v => v > 0) || budgetChartData.gross_profit.some(v => v > 0) || budgetChartData.operating_profit.some(v => v > 0))) {
    salesData.push({
      label: `${budgetYear} 売上高（予算）`,
      data: budgetChartData.sales,
      borderColor: 'rgba(75, 192, 192, 0.5)',
      backgroundColor: 'rgba(75, 192, 192, 0.1)',
      borderDash: [5, 5],
      borderWidth: 2,
      fill: false,
      type: 'line',
    });

    grossProfitData.push({
      label: `${budgetYear} 粗利益（予算）`,
      data: budgetChartData.gross_profit,
      borderColor: 'rgba(255, 99, 132, 0.5)',
      backgroundColor: 'rgba(255, 99, 132, 0.1)',
      borderDash: [5, 5],
      borderWidth: 2,
      fill: false,
      type: 'line',
    });

    operatingProfitData.push({
      label: `${budgetYear} 営業利益（予算）`,
      data: budgetChartData.operating_profit,
      borderColor: 'rgba(255, 206, 86, 0.5)',
      backgroundColor: 'rgba(255, 206, 86, 0.1)',
      borderDash: [5, 5],
      borderWidth: 2,
      fill: false,
      type: 'line',
    });
  }
  
  // 実績データは monthlySummaries に既に含まれているため、ここでは追加しない

  const ctx = document.getElementById('salesChart').getContext('2d');
  const salesChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: monthsLabel,
      datasets: salesData, // 初期データは売上のみ
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: {
            font: {
              family: "'Noto Sans JP', 'Inter', sans-serif",
              size: 11,
              weight: '500'
            },
            padding: 16,
            usePointStyle: true,
            pointStyle: 'rect',
            color: '#0F0F0F',
            boxWidth: 12,
            boxHeight: 12
          }
        },
        tooltip: {
          backgroundColor: '#FFFFFF',
          titleColor: '#0F0F0F',
          bodyColor: '#0F0F0F',
          borderColor: '#E0E0E0',
          borderWidth: 1,
          padding: 12,
          titleFont: {
            family: "'Noto Serif JP', 'Cormorant Garamond', serif",
            size: 13,
            weight: '600'
          },
          bodyFont: {
            family: "'Noto Sans Mono CJK JP', 'JetBrains Mono', monospace",
            size: 12,
            weight: '500'
          },
          displayColors: true,
          boxPadding: 4,
          cornerRadius: 0,
          callbacks: {
            label: function(context) {
              let label = context.dataset.label || '';
              if (label) {
                label += ': ';
              }
              if (context.parsed.y !== null) {
                label += context.parsed.y.toLocaleString('ja-JP') + ' 千円';
              }
              return label;
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: {
            color: '#E0E0E0',
            lineWidth: 1,
            drawBorder: false
          },
          ticks: {
            font: {
              family: "'Noto Sans Mono CJK JP', 'JetBrains Mono', monospace",
              size: 11,
              weight: '500'
            },
            color: '#666666',
            padding: 8,
            callback: function(value) {
              return value.toLocaleString('ja-JP');
            }
          }
        },
        x: {
          grid: {
            display: false,
            drawBorder: false
          },
          ticks: {
            font: {
              family: "'Noto Sans JP', 'Inter', sans-serif",
              size: 11,
              weight: '500'
            },
            color: '#666666',
            padding: 8
          }
        }
      },
      elements: {
        bar: {
          borderRadius: 0,
          borderSkipped: false
        },
        line: {
          borderWidth: 2,
          tension: 0,
          fill: false
        },
        point: {
          radius: 4,
          hoverRadius: 6,
          borderWidth: 2,
          borderColor: '#FFFFFF'
        }
      },
      animation: {
        duration: 600,
        easing: 'easeOutQuart'
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
