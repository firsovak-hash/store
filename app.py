from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_cors import CORS
import json
import os

app = Flask(__name__)
app.secret_key = 'секретный-ключ-для-корзины-поменяй-потом'  # ОБЯЗАТЕЛЬНО для session
CORS(app)  # Разрешаем запросы с Тильды

# GLB mime type
import mimetypes
mimetypes.add_type('model/gltf-binary', '.glb')
mimetypes.add_type('model/gltf+json', '.gltf')

# Товары
PRODUCTS = {
    '1': {
        'id': '1',
        'name': 'Оверсайз худи',
        'price': 4900,
        'image': 'https://via.placeholder.com/600x400?text=Hoodie',
        'description': 'Тяжёлый хлопок, свободный крой.',
        'full_description': 'Оверсайз худи из 100% хлопка 380г. Плотный, тёплый, садится идеально. Доступен в чёрном и молочном.',
        'badge': 'Хит'
    },
    '2': {
        'id': '2',
        'name': 'Карго-брюки',
        'price': 6200,
        'image': 'https://via.placeholder.com/600x400?text=Cargo',
        'description': 'Широкий крой, функциональные карманы.',
        'full_description': 'Карго-брюки из плотной хлопковой смеси. Регулируемый пояс, 6 карманов, зауженный низ.',
        'badge': 'Новинка'
    },
    '3': {
        'id': '3',
        'name': 'Базовая футболка',
        'price': 2800,
        'image': 'https://via.placeholder.com/600x400?text=Tee',
        'description': 'Плотный хлопок, минимализм.',
        'full_description': 'Футболка из 100% хлопка 220г. Прямой крой, усиленные швы, не деформируется после стирки.',
        'badge': ''
    },
    '4': {
        'id': '4',
        'name': 'Бомбер',
        'price': 9500,
        'image': 'https://via.placeholder.com/600x400?text=Bomber',
        'description': 'Классический силуэт, современные детали.',
        'full_description': 'Бомбер из нейлона с подкладкой. Рёбра из риба, двусторонняя молния, внутренние карманы.',
        'badge': 'Премиум'
    },
    '5': {
        'id': '5',
        'name': 'Широкие джинсы',
        'price': 7200,
        'image': 'https://via.placeholder.com/600x400?text=Jeans',
        'description': 'Straight fit, необработанный край.',
        'full_description': 'Прямые джинсы из 100% денима 14oz. Необработанный низ, потёртости вручную.',
        'badge': ''
    },
    '6': {
        'id': '6',
        'name': 'Трекинговая куртка',
        'price': 12500,
        'image': 'https://via.placeholder.com/600x400?text=Jacket',
        'description': 'Ветрозащита, минималистичный дизайн.',
        'full_description': 'Лёгкая куртка из дышащего нейлона. Убирается в собственный карман, ветро- и водозащита.',
        'badge': ''
    }
}
DEPLOY_TOKEN = '3cbde1eedf6de1b7f800a9f92f506452b6ff7113'

@app.route('/deploy', methods=['POST'])
def deploy():
    token = request.headers.get('X-Deploy-Token') or request.args.get('token')
    if token != DEPLOY_TOKEN:
        return jsonify({'error': 'unauthorized'}), 403
    import subprocess
    result = subprocess.run(['bash', '/home/DODGE/deploy.sh'],
                           capture_output=True, text=True)
    return jsonify({'ok': True, 'out': result.stdout, 'err': result.stderr})

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/likes')
def likes():
    return render_template('likes.html', products=PRODUCTS_LIST)
PRODUCTS_LIST = list(PRODUCTS.values())

# Файл для хранения отзывов
REVIEWS_FILE = 'reviews.json'

def load_reviews():
    if os.path.exists(REVIEWS_FILE):
        with open(REVIEWS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_reviews(reviews):
    with open(REVIEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)

# ========== API ДЛЯ КОРЗИНЫ (ТО, ЧЕГО НЕ ХВАТАЛО) ==========

@app.route('/api/cart/count')
def cart_count():
    """Возвращает количество товаров в корзине"""
    cart = session.get('cart', [])
    count = sum(item.get('quantity', 1) for item in cart)
    return jsonify({'count': count})

@app.route('/api/cart/total')
def cart_total():
    """Возвращает общую сумму корзины"""
    cart = session.get('cart', [])
    total = sum(item['price'] * item.get('quantity', 1) for item in cart)
    return jsonify({'total': total})

@app.route('/api/cart/items')
def cart_items():
    """Возвращает все товары в корзине"""
    cart = session.get('cart', [])
    return jsonify({'items': cart})

@app.route('/api/cart/add', methods=['POST'])
def cart_add():
    """Добавляет товар в корзину"""
    data = request.json
    product_id = data.get('product_id')
    product_name = data.get('name')
    product_price = data.get('price')
    
    cart = session.get('cart', [])
    
    # Проверяем, есть ли уже такой товар
    for item in cart:
        if item['id'] == product_id:
            item['quantity'] = item.get('quantity', 1) + 1
            session['cart'] = cart
            return jsonify({'success': True, 'count': len(cart)})
    
    # Добавляем новый товар
    cart.append({
        'id': product_id,
        'name': product_name,
        'price': product_price,
        'quantity': 1
    })
    session['cart'] = cart
    
    return jsonify({'success': True, 'count': len(cart)})

@app.route('/api/cart/remove', methods=['POST'])
def cart_remove():
    """Удаляет товар из корзины"""
    data = request.json
    product_id = data.get('product_id')
    
    cart = session.get('cart', [])
    cart = [item for item in cart if item['id'] != product_id]
    session['cart'] = cart
    
    return jsonify({'success': True, 'count': len(cart)})

@app.route('/api/cart/clear', methods=['POST'])
def cart_clear():
    """Очищает корзину"""
    session['cart'] = []
    return jsonify({'success': True})

@app.route('/api/order/create', methods=['POST'])
def order_create():
    """Создаёт заказ"""
    data = request.json
    orders = []
    if os.path.exists('orders.json'):
        with open('orders.json', 'r', encoding='utf-8') as f:
            orders = json.load(f)
    order = {
        'id': len(orders) + 1,
        'name': data.get('name'),
        'phone': data.get('phone'),
        'email': data.get('email'),
        'address': data.get('address'),
        'comment': data.get('comment'),
        'pay_method': data.get('pay_method'),
        'items': data.get('items', []),
        'total': data.get('total', 0),
        'status': 'new'
    }
    orders.append(order)
    with open('orders.json', 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)
    return jsonify({'success': True, 'order_id': order['id']})

# ========== ОСНОВНЫЕ МАРШРУТЫ ==========

@app.route('/')
def index():
    return render_template('index.html', products=PRODUCTS_LIST)

@app.route('/catalog')
def catalog():
    return render_template('catalog.html', products=PRODUCTS_LIST)

@app.route('/order')
def order_page():
    cart = session.get('cart', [])
    total = sum(item['price'] * item.get('quantity', 1) for item in cart)
    return render_template('order.html', cart=cart, total=total)

@app.route('/cart')
def cart_page():
    """Страница корзины"""
    cart = session.get('cart', [])
    total = sum(item['price'] * item.get('quantity', 1) for item in cart)
    return render_template('cart.html', cart=cart, total=total)

@app.route('/product/<product_id>', methods=['GET', 'POST'])
def product_page(product_id):
    product = PRODUCTS.get(product_id)
    if not product:
        return redirect(url_for('index'))
    
    reviews = load_reviews()
    product_reviews = reviews.get(product_id, [])
    
    if request.method == 'POST':
        name = request.form.get('name', 'Аноним')
        rating = int(request.form.get('rating', 5))
        text = request.form.get('text', '')
        
        if text:
            new_review = {
                'id': len(product_reviews) + 1,
                'name': name,
                'rating': rating,
                'text': text,
                'date': 'Сегодня'
            }
            product_reviews.append(new_review)
            reviews[product_id] = product_reviews
            save_reviews(reviews)
    
    return render_template('product.html', product=product, reviews=product_reviews)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
