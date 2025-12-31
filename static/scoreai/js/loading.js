/**
 * ローディング状態管理用のJavaScript
 */

// ローディングオーバーレイの表示/非表示
function showLoadingOverlay(message = '処理中...') {
    let overlay = document.getElementById('loading-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-overlay-content">
                <div class="loading-spinner"></div>
                <p>${message}</p>
            </div>
        `;
        document.body.appendChild(overlay);
    }
    overlay.classList.add('active');
}

function hideLoadingOverlay() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

// フォーム送信時のローディング状態
function setupFormLoading() {
    const forms = document.querySelectorAll('form:not(.no-auto-loading)');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // 既にpreventDefaultが呼ばれている場合は何もしない
            if (e.defaultPrevented) {
                return;
            }
            
            // onsubmit属性がある場合、その結果を確認
            // onsubmitがfalseを返す可能性がある場合は、先に評価する必要がある
            // ただし、これは非同期で実行されるため、setTimeoutで遅延させる
            const onsubmitAttr = form.getAttribute('onsubmit');
            if (onsubmitAttr && onsubmitAttr.includes('confirm')) {
                // confirmを含むonsubmitの場合は、少し遅延させて処理
                // これにより、onsubmitの結果を確認できる
                setTimeout(function() {
                    if (!e.defaultPrevented) {
                        const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
                        if (submitButton && !submitButton.disabled) {
                            submitButton.classList.add('btn-loading');
                            submitButton.disabled = true;
                            const originalText = submitButton.textContent || submitButton.value;
                            submitButton.dataset.originalText = originalText;
                            submitButton.textContent = '処理中...';
                            if (submitButton.tagName === 'INPUT') {
                                submitButton.value = '処理中...';
                            }
                        }
                        form.classList.add('form-loading');
                    }
                }, 10);
                return;
            }
            
            const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
            if (submitButton) {
                submitButton.classList.add('btn-loading');
                submitButton.disabled = true;
                const originalText = submitButton.textContent || submitButton.value;
                submitButton.dataset.originalText = originalText;
                submitButton.textContent = '処理中...';
                if (submitButton.tagName === 'INPUT') {
                    submitButton.value = '処理中...';
                }
            }
            form.classList.add('form-loading');
        });
    });
}

// ボタンクリック時のローディング状態
function setupButtonLoading() {
    const buttons = document.querySelectorAll('button[data-loading], a[data-loading]');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (this.dataset.loading !== 'false') {
                this.classList.add('btn-loading');
                const originalText = this.textContent;
                this.dataset.originalText = originalText;
                this.textContent = '処理中...';
            }
        });
    });
}

// AJAXリクエスト時のローディング状態
function setupAjaxLoading() {
    // jQueryが利用可能な場合
    if (typeof jQuery !== 'undefined') {
        $(document).ajaxStart(function() {
            showLoadingOverlay('データを読み込んでいます...');
        });
        
        $(document).ajaxStop(function() {
            hideLoadingOverlay();
        });
        
        $(document).ajaxError(function(event, xhr, settings, thrownError) {
            hideLoadingOverlay();
            console.error('AJAX Error:', thrownError);
        });
    }
    
    // Fetch APIの場合
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        showLoadingOverlay('データを読み込んでいます...');
        return originalFetch.apply(this, args)
            .then(response => {
                hideLoadingOverlay();
                return response;
            })
            .catch(error => {
                hideLoadingOverlay();
                throw error;
            });
    };
}

// CSVインポート時のプログレスバー
function showProgressBar(containerId, message = 'インポート中...') {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const progressHtml = `
        <div class="progress-container">
            <div class="progress-bar"></div>
        </div>
        <p class="text-center">${message}</p>
    `;
    container.innerHTML = progressHtml;
}

// ページ読み込み完了時に初期化
document.addEventListener('DOMContentLoaded', function() {
    setupFormLoading();
    setupButtonLoading();
    setupAjaxLoading();
});

// エクスポート
window.loadingUtils = {
    showLoadingOverlay,
    hideLoadingOverlay,
    showProgressBar,
    setupFormLoading,
    setupButtonLoading,
    setupAjaxLoading
};

