/**
 * フッターの高さを動的に計算し、コンテンツエリアのパディングを調整
 * コンテンツが少ない場合でもフッターが最下部に固定されるようにする
 */
(function() {
    'use strict';
    
    function adjustFooterLayout() {
        const footer = document.querySelector('footer');
        const bodyWrapper = document.querySelector('.body-wrapper');
        const containerFluid = document.querySelector('.body-wrapper > .container-fluid');
        const header = document.querySelector('.app-header');
        
        if (!footer || !bodyWrapper || !containerFluid) {
            return;
        }
        
        // 各要素の高さを取得
        const footerHeight = footer.offsetHeight;
        const headerHeight = header ? header.offsetHeight : 70; // デフォルト70px（Modernizeテーマ）
        const viewportHeight = window.innerHeight;
        
        // コンテンツの実際の高さを取得
        const containerScrollHeight = containerFluid.scrollHeight;
        
        // body-wrapperの最小高さを設定（常に100vh）
        bodyWrapper.style.minHeight = viewportHeight + 'px';
        
        // コンテンツが少ない場合、container-fluidの最小高さを調整
        // フッターが最下部に来るようにする
        const availableHeight = viewportHeight - headerHeight;
        const minContainerHeight = availableHeight - footerHeight;
        
        if (containerScrollHeight < minContainerHeight) {
            // コンテンツが少ない場合
            // container-fluidの最小高さを設定して、フッターの下に空白が生じないようにする
            containerFluid.style.minHeight = minContainerHeight + 'px';
            containerFluid.style.paddingBottom = '0';
        } else {
            // コンテンツが多い場合、フッターに隠れないようにパディングを追加
            containerFluid.style.paddingBottom = (footerHeight + 20) + 'px';
            containerFluid.style.minHeight = 'auto';
        }
        
        // CSS変数も設定（他の用途で使用する場合）
        document.documentElement.style.setProperty('--footer-height', footerHeight + 'px');
        document.documentElement.style.setProperty('--header-height', headerHeight + 'px');
    }
    
    // 実行関数
    function runAdjustment() {
        // 少し遅延させて、すべての要素が完全にレンダリングされるのを待つ
        setTimeout(adjustFooterLayout, 100);
    }
    
    // ページ読み込み時とリサイズ時に実行
    window.addEventListener('load', runAdjustment);
    window.addEventListener('resize', runAdjustment);
    
    // DOMContentLoaded時にも実行
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', runAdjustment);
    } else {
        runAdjustment();
    }
    
    // フッターの内容が変更された場合にも実行（MutationObserver）
    const footer = document.querySelector('footer');
    if (footer) {
        const observer = new MutationObserver(function(mutations) {
            runAdjustment();
        });
        
        observer.observe(footer, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['style', 'class']
        });
    }
    
    // コンテンツが動的に変更される場合にも対応
    const containerFluid = document.querySelector('.body-wrapper > .container-fluid');
    if (containerFluid) {
        const contentObserver = new MutationObserver(function(mutations) {
            runAdjustment();
        });
        
        contentObserver.observe(containerFluid, {
            childList: true,
            subtree: true,
            attributes: false
        });
    }
})();

