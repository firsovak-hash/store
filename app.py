from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_cors import CORS
import json
import os
import hmac
import hashlib
import time
import urllib.request
import urllib.parse
from urllib.parse import parse_qsl

# .env для локальной разработки (на PythonAnywhere переменные ставятся в WSGI).
# python-dotenv не обязателен для веба — если его нет, просто пропускаем.
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

app = Flask(__name__)
app.secret_key = 'секретный-ключ-для-корзины-поменяй-потом'  # ОБЯЗАТЕЛЬНО для session
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Jinja подхватывает правки шаблонов без рестарта
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # static не кэшируется на сервере
CORS(app)  # Разрешаем запросы с Тильды

# ── Telegram Mini App: секреты только на сервере ──
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID', '')
USERS_FILE = 'users.json'


def verify_init_data(init_data, max_age=86400):
    """Проверяет подпись Telegram WebApp initData (HMAC-SHA256 на BOT_TOKEN).

    Возвращает dict пользователя (id, first_name, username, …) если подпись
    верна и не протухла, иначе None. Личность НИКОГДА не берём из данных
    клиента напрямую — только из проверенной здесь подписи.
    """
    if not init_data or not BOT_TOKEN:
        return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception:
        return None
    recv_hash = pairs.pop('hash', None)
    if not recv_hash:
        return None
    data_check = '\n'.join('{}={}'.format(k, pairs[k]) for k in sorted(pairs))
    secret = hmac.new(b'WebAppData', BOT_TOKEN.encode(), hashlib.sha256).digest()
    calc = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc, recv_hash):
        return None
    try:
        if max_age and (time.time() - int(pairs.get('auth_date', '0'))) > max_age:
            return None
    except Exception:
        return None
    try:
        user = json.loads(pairs.get('user', '{}'))
    except Exception:
        user = {}
    if not user.get('id'):
        return None
    return user


def current_tg_user():
    """Достаёт и валидирует пользователя из текущего запроса.

    initData передаётся заголовком X-Telegram-Init-Data (или полем initData
    в JSON-теле). Возвращает проверенный dict пользователя или None.
    """
    init_data = request.headers.get('X-Telegram-Init-Data', '')
    if not init_data and request.is_json:
        init_data = (request.get_json(silent=True) or {}).get('initData', '')
    return verify_init_data(init_data)


def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def get_profile(uid):
    return load_users().get(str(uid), {})


def upsert_profile(user, **fields):
    """Создаёт/обновляет профиль по проверенному Telegram-пользователю.

    Возвращает (профиль, first_visit). Непустые поля из fields (name/phone/
    address) сохраняются для подстановки в будущих заказах.
    """
    users = load_users()
    uid = str(user['id'])
    prof = users.get(uid, {})
    first_visit = not prof
    prof.setdefault('first_seen', int(time.time()))
    prof['tg_id'] = user['id']
    prof['username'] = user.get('username', '')
    prof['first_name'] = user.get('first_name', '')
    prof['last_name'] = user.get('last_name', '')
    prof['last_seen'] = int(time.time())
    for k, v in fields.items():
        if v:
            prof[k] = v
    users[uid] = prof
    save_users(users)
    return prof, first_visit


def _esc(s):
    return str(s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def format_order_msg(order):
    lines = ['🛒 <b>Новый заказ #{}</b>'.format(order['id']), '']
    for it in order.get('items', []):
        q = it.get('quantity', 1) or 1
        lines.append('• {} × {} — {} р.'.format(_esc(it.get('name', '')), q, (it.get('price', 0) or 0) * q))
    lines.append('')
    lines.append('💰 <b>Итого: {} р.</b>'.format(order.get('total', 0)))
    lines.append('')
    lines.append('👤 {}'.format(_esc(order.get('name') or '—')))
    lines.append('📞 {}'.format(_esc(order.get('phone') or '—')))
    lines.append('📍 {}'.format(_esc(order.get('address') or '—')))
    if order.get('comment'):
        lines.append('💬 {}'.format(_esc(order['comment'])))
    lines.append('')
    if order.get('tg_username'):
        lines.append('✅ Telegram: @{} (id <code>{}</code>)'.format(_esc(order['tg_username']), order['tg_id']))
    elif order.get('tg_id'):
        lines.append('✅ Telegram id <code>{}</code> (подтверждён)'.format(order['tg_id']))
    else:
        lines.append('⚠️ Заказ без подтверждённого Telegram-профиля')
    if order.get('pay_method'):
        lines.append('💳 Оплата: {}'.format(_esc(order['pay_method'])))
    return '\n'.join(lines)


def notify_admin(text):
    """Шлёт сообщение админу в личку через Bot API. Не роняет заказ при ошибке."""
    if not (BOT_TOKEN and ADMIN_CHAT_ID):
        return False
    try:
        data = urllib.parse.urlencode({
            'chat_id': ADMIN_CHAT_ID,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': 'true',
        }).encode()
        req = urllib.request.Request(
            'https://api.telegram.org/bot{}/sendMessage'.format(BOT_TOKEN), data=data)
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        print('notify_admin error:', e)
        return False

# GLB mime type
import mimetypes
mimetypes.add_type('model/gltf-binary', '.glb')
mimetypes.add_type('model/gltf+json', '.gltf')

# Товары (вейп-магазин: жидкости / под-системы / картриджи)
LIQUID_IMG = '/static/images/liquid.jpg'
POD_IMG = '/static/images/pod.jpg'
CARTRIDGE_IMG = '/static/images/cartridge.jpg'

PRODUCTS = {
    '1': {
        'id': '1', 'name': 'Жидкость Mango Ice', 'price': 450, 'image': LIQUID_IMG,
        'description': 'Манго с холодком, 20 мг.',
        'full_description': 'Жидкость для пода: спелое манго с лёгким холодком. Крепость 20 мг (соль), объём 30 мл.',
        'badge': 'Хит'
    },
    '2': {
        'id': '2', 'name': 'Жидкость Berry Mix', 'price': 400, 'image': LIQUID_IMG,
        'description': 'Микс лесных ягод.',
        'full_description': 'Жидкость для пода: черника, малина и ежевика. Крепость 20 мг (соль), объём 30 мл.',
        'badge': ''
    },
    '3': {
        'id': '3', 'name': 'Жидкость Tobacco', 'price': 380, 'image': LIQUID_IMG,
        'description': 'Классический табак.',
        'full_description': 'Жидкость для пода: мягкий табачный вкус без лишней сладости. Крепость 20 мг (соль), объём 30 мл.',
        'badge': ''
    },
    '4': {
        'id': '4', 'name': 'Жидкость Mint Fresh', 'price': 420, 'image': LIQUID_IMG,
        'description': 'Свежая мята.',
        'full_description': 'Жидкость для пода: чистая холодная мята. Крепость 20 мг (соль), объём 30 мл.',
        'badge': ''
    },
    '5': {
        'id': '5', 'name': 'Pod-система Caliburn', 'price': 2200, 'image': POD_IMG,
        'description': 'Компактная под-система.',
        'full_description': 'Uwell Caliburn: надёжная под-система с плотной затяжкой, аккумулятор 520 мАч, USB-C.',
        'badge': ''
    },
    '6': {
        'id': '6', 'name': 'Pod-система Xros', 'price': 1900, 'image': POD_IMG,
        'description': 'Экран, USB-C, лёгкая.',
        'full_description': 'Vaporesso XROS: под-система с индикацией заряда, регулировкой обдува и аккумулятором 1000 мАч.',
        'badge': ''
    },
    '7': {
        'id': '7', 'name': 'Pod-система Luxe', 'price': 2800, 'image': POD_IMG,
        'description': 'Премиум под-система.',
        'full_description': 'Vaporesso LUXE: цветной экран, мощность до 40 Вт, аккумулятор 1500 мАч.',
        'badge': 'Премиум'
    },
    '8': {
        'id': '8', 'name': 'Картридж Caliburn', 'price': 350, 'image': CARTRIDGE_IMG,
        'description': 'Сменный картридж.',
        'full_description': 'Сменный картридж для Uwell Caliburn, сопротивление 1.0 Ом, объём 2 мл. В упаковке 1 шт.',
        'badge': ''
    },
    '9': {
        'id': '9', 'name': 'Картридж Xros', 'price': 300, 'image': CARTRIDGE_IMG,
        'description': 'Сменный картридж.',
        'full_description': 'Сменный картридж для Vaporesso XROS, сопротивление 1.2 Ом, объём 2 мл. В упаковке 1 шт.',
        'badge': ''
    },
    '10': {
        'id': '10', 'name': 'Картридж Luxe', 'price': 400, 'image': CARTRIDGE_IMG,
        'description': 'Сменный картридж.',
        'full_description': 'Сменный картридж для Vaporesso LUXE, сопротивление 0.8 Ом, объём 2 мл. В упаковке 1 шт.',
        'badge': ''
    },
    '11': {
        'id': '11', 'name': 'Картридж Nord', 'price': 320, 'image': CARTRIDGE_IMG,
        'description': 'Сменный картридж.',
        'full_description': 'Сменный картридж для SMOK Nord, сопротивление 0.8 Ом, объём 3 мл. В упаковке 1 шт.',
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

@app.route('/api/tg/verify', methods=['POST'])
def tg_verify():
    """Проверяет initData, заводит/обновляет профиль, отдаёт сохранённые данные."""
    user = current_tg_user()
    if not user:
        return jsonify({'ok': False}), 401
    prof, first_visit = upsert_profile(user)
    return jsonify({
        'ok': True,
        'first_visit': first_visit,
        'user': {
            'id': user['id'],
            'first_name': user.get('first_name', ''),
            'username': user.get('username', ''),
        },
        'profile': {
            'name': prof.get('name', '') or user.get('first_name', ''),
            'phone': prof.get('phone', ''),
            'address': prof.get('address', ''),
        },
    })


@app.route('/api/order/create', methods=['POST'])
def order_create():
    """Создаёт заказ: сохраняет профиль (адрес/телефон) и шлёт заказ админу."""
    data = request.get_json(silent=True) or {}
    user = current_tg_user()  # проверенный TG-профиль (или None вне Telegram)

    # Запоминаем адрес/телефон/имя для будущих заказов
    if user:
        upsert_profile(
            user,
            name=data.get('name'),
            phone=data.get('phone'),
            address=data.get('address'),
        )

    orders = []
    if os.path.exists('orders.json'):
        with open('orders.json', 'r', encoding='utf-8') as f:
            orders = json.load(f)
    order = {
        'id': len(orders) + 1,
        'name': data.get('name'),
        'phone': data.get('phone'),
        'address': data.get('address'),
        'comment': data.get('comment'),
        'pay_method': data.get('pay_method'),
        'items': data.get('items', []),
        'total': data.get('total', 0),
        'status': 'new',
        'created': int(time.time()),
        'tg_id': user.get('id') if user else None,
        'tg_username': user.get('username') if user else None,
        'tg_name': (
            (user.get('first_name', '') + ' ' + user.get('last_name', '')).strip()
            if user else None
        ),
    }
    orders.append(order)
    with open('orders.json', 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

    notify_admin(format_order_msg(order))
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

@app.route('/policy')
def policy():
    return render_template('policy.html')

@app.route('/agreement')
def agreement():
    return render_template('agreement.html')

@app.route('/delivery')
def delivery():
    return render_template('delivery.html')

@app.route('/returns')
def returns():
    return render_template('returns.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
