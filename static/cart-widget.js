// static/cart-widget.js
// Этот виджет можно вставить в Тильду

(function() {
    // Создаем HTML для виджета корзины
    const widgetHtml = `
        <div id="tilda-cart-widget" style="position: fixed; bottom: 20px; right: 20px; z-index: 9999;">
            <a href="https://твой-сайт.railway.app/cart" style="
                display: flex;
                align-items: center;
                gap: 8px;
                background: #000;
                color: #fff;
                padding: 12px 20px;
                border-radius: 40px;
                text-decoration: none;
                font-family: sans-serif;
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            ">
                <span>🛒</span>
                <span id="cart-count-widget">0</span>
                <span>товаров</span>
            </a>
        </div>
    `;
    
    // Добавляем виджет на страницу
    document.body.insertAdjacentHTML('beforeend', widgetHtml);
    
    // Функция обновления счетчика
    function updateCartCount() {
        fetch('https://твой-сайт.railway.app/api/cart/count')
            .then(res => res.json())
            .then(data => {
                const countEl = document.getElementById('cart-count-widget');
                if (countEl) countEl.textContent = data.count;
            })
            .catch(err => console.log('Ошибка загрузки корзины:', err));
    }
    
    // Обновляем при загрузке
    updateCartCount();
    
    // Обновляем каждые 5 секунд (на случай, если корзина изменилась на другой вкладке)
    setInterval(updateCartCount, 5000);
})();
