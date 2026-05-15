import os
import random
import string
import json
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = '3d-figurki-secret-key-2024'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ==================== ПРОСТАЯ БД НА JSON ====================
USERS_FILE = 'data/users.json'
ORDERS_FILE = 'data/orders.json'
PRODUCTS_FILE = 'data/products.json'

os.makedirs('data', exist_ok=True)
@app.route('/product/<product_id>')
def product_page(product_id):
    products = {
        '1': {'name': 'Чиби-фигурка пары', 'price': 3500, 'description': 'Милые чиби-фигурки вас двоих. Высота 8-10 см. Ручная покраска. Идеальный подарок для годовщины или просто так.', 'features': ['Ручная покраска', 'Красивая упаковка', 'Срок 5-7 дней']},
        '2': {'name': 'Фигурка с питомцем', 'price': 4200, 'description': 'Вы и ваш любимый питомец в одном кадре. Собака, кот или хомячок — любой!', 'features': ['С любым питомцем', 'Ручная покраска', 'Срок 5-7 дней']},
        '3': {'name': 'Спортивная фигурка', 'price': 4500, 'description': 'Для спортсменов: футбол, бокс, пауэрлифтинг. Любой вид спорта.', 'features': ['Любой вид спорта', 'Детализация экипировки', 'Срок 5-7 дней']},
        '4': {'name': 'Премиум фигурка', 'price': 6500, 'description': 'Максимальная детализация, полная покраска, особенная упаковка.', 'features': ['Макс. детализация', 'Подарочная коробка', 'Срок 7-10 дней']},
        '5': {'name': 'Брелок-фигурка', 'price': 1500, 'description': 'Маленькая копия, которую всегда можно носить с собой.', 'features': ['Размер 4-5 см', 'Ручная покраска', 'Срок 3-5 дней']},
        '6': {'name': 'Фигурка семьи', 'price': 5500, 'description': 'Вся семья в одной композиции. До 5 человек.', 'features': ['До 5 человек', 'Общая подставка', 'Срок 7-10 дней']},
    }
    product = products.get(product_id)
    if not product:
        return redirect(url_for('index'))
    return render_template('product.html', product=product, product_id=product_id)
def load_json(file):
    try:
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return [] if 'users' in file or 'orders' in file else {}

def save_json(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Товары
PRODUCTS = {
    '1': {
        'id': '1',
        'name': 'Чиби-фигурка пары',
        'price': 3500,
        'old_price': 5000,
        'description': 'Милые чиби-фигурки вас двоих. Идеальный подарок для второй половинки.',
        'features': ['Высота 8-10 см', 'Ручная покраска', 'Красивая упаковка', 'Срок изготовления 5-7 дней'],
        'image': '/static/images/couple-chibi.jpg',
        'badge': 'Хит',
        'popular': True
    },
    '2': {
        'id': '2',
        'name': 'Фигурка с питомцем',
        'price': 4200,
        'old_price': 6000,
        'description': 'Вы и ваш любимый питомец в одном кадре. Собака, кот или хомячок — любой!',
        'features': ['Фигурка человека + питомца', 'Высота 8-10 см', 'Ручная покраска', 'Учитываем окрас животного'],
        'image': '/static/images/couple-pet.jpg',
        'badge': 'Новинка',
        'popular': True
    },
    '3': {
        'id': '3',
        'name': 'Спортивная фигурка',
        'price': 4500,
        'old_price': 6500,
        'description': 'Для спортсменов и активных людей. Любой вид спорта: футбол, бокс, пауэрлифтинг и другие.',
        'features': ['Любой вид спорта', 'Детализация экипировки', 'Ручная покраска', 'Инвентарь в подарок'],
        'image': '/static/images/sport-figure.jpg',
        'badge': '',
        'popular': False
    },
    '4': {
        'id': '4',
        'name': 'Премиум фигурка',
        'price': 6500,
        'old_price': 9000,
        'description': 'Максимальная детализация, полная покраска, особая упаковка. Для самых важных подарков.',
        'features': ['Высота 12-15 см', 'Полная покраска всех деталей', 'Подарочная коробка с магнитным замком', 'Именная гравировка'],
        'image': '/static/images/premium-figure.jpg',
        'badge': 'Премиум',
        'popular': True
    },
    '5': {
        'id': '5',
        'name': 'Брелок-фигурка',
        'price': 1500,
        'old_price': 2500,
        'description': 'Маленькая копия, которую всегда можно носить с собой на ключах или рюкзаке.',
        'features': ['Высота 4-5 см', 'Крепление для ключей', 'Компактная упаковка', 'Срок 3-5 дней'],
        'image': '/static/images/keychain.jpg',
        'badge': '',
        'popular': False
    },
    '6': {
        'id': '6',
        'name': 'Фигурка семьи',
        'price': 5500,
        'old_price': 8000,
        'description': 'Вся семья в одной композиции. Мама, папа, дети — до 5 человек.',
        'features': ['До 5 фигурок', 'Высота 8-10 см', 'Общая подставка с именами', 'Подарочная упаковка'],
        'image': '/static/images/family-figure.jpg',
        'badge': '',
        'popular': False
    }
}

# ==================== КЛАССЫ ====================
class User(UserMixin):
    def __init__(self, id, username, email, password):
        self.id = id
        self.username = username
        self.email = email
        self.password = password

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    users = load_json(USERS_FILE)
    for u in users:
        if str(u['id']) == str(user_id):
            return User(u['id'], u['username'], u['email'], u['password'])
    return None

# ==================== МАРШРУТЫ ====================
@app.route('/')
def index():
    popular = [p for p in PRODUCTS.values() if p.get('popular', False)]
    return render_template('index.html', products=popular)

@app.route('/catalog')
def catalog():
    return render_template('catalog.html', products=PRODUCTS.values())

@app.route('/product/<product_id>')
def product(product_id):
    product = PRODUCTS.get(product_id)
    if not product:
        return redirect(url_for('catalog'))
    return render_template('product.html', product=product)

@app.route('/order/<product_id>', methods=['GET', 'POST'])
@login_required
def order(product_id):
    product = PRODUCTS.get(product_id)
    if not product:
        return redirect(url_for('catalog'))
    
    if request.method == 'POST':
        # Сохраняем заказ
        photo1 = request.files.get('photo1')
        photo2 = request.files.get('photo2')
        comment = request.form.get('comment', '')
        
        order_id = ''.join(random.choices(string.digits, k=8))
        
        # Сохраняем фото
        photo1_path = ''
        photo2_path = ''
        if photo1:
            filename = f"{order_id}_1_{secure_filename(photo1.filename)}"
            photo1.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            photo1_path = filename
        if photo2:
            filename = f"{order_id}_2_{secure_filename(photo2.filename)}"
            photo2.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            photo2_path = filename
        
        orders = load_json(ORDERS_FILE)
        orders.append({
            'id': order_id,
            'user_id': current_user.id,
            'username': current_user.username,
            'product_id': product_id,
            'product_name': product['name'],
            'price': product['price'],
            'photo1': photo1_path,
            'photo2': photo2_path,
            'comment': comment,
            'status': 'new',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        save_json(ORDERS_FILE, orders)
        
        flash('Заказ принят! Мы свяжемся с вами в ближайшее время.', 'success')
        return redirect(url_for('my_orders'))
    
    return render_template('order.html', product=product)

@app.route('/my-orders')
@login_required
def my_orders():
    orders = load_json(ORDERS_FILE)
    user_orders = [o for o in orders if o['user_id'] == current_user.id]
    return render_template('my_orders.html', orders=user_orders)

#@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        
        users = load_json(USERS_FILE)
        
        if any(u['username'] == username for u in users):
            flash('Логин занят', 'error')
            return redirect(url_for('register'))
        
        if any(u['email'] == email for u in users):
            flash('Email уже используется', 'error')
            return redirect(url_for('register'))
        
        new_id = max([u['id'] for u in users] + [0]) + 1
        users.append({
            'id': new_id,
            'username': username,
            'email': email,
            'password': password
        })
        save_json(USERS_FILE, users)
        
        flash('Регистрация успешна! Войдите в аккаунт.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

#@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        users = load_json(USERS_FILE)
        user = next((u for u in users if u['username'] == username), None)
        
        if user and check_password_hash(user['password'], password):
            login_user(User(user['id'], user['username'], user['email'], user['password']))
            return redirect(url_for('index'))
        
        flash('Неверный логин или пароль', 'error')
    
    return render_template('login.html')

#@app.route('/logout')
#@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ==================== АДМИН-ПАНЕЛЬ ====================
@app.route('/admin')
@login_required
def admin():
    if current_user.username != 'admin':
        flash('Нет доступа', 'error')
        return redirect(url_for('index'))
    
    orders = load_json(ORDERS_FILE)
    return render_template('admin.html', orders=orders)

#@app.route('/admin/update-status/<order_id>/<status>')
#@login_required
def update_status(order_id, status):
    if current_user.username != 'admin':
        return jsonify({'error': 'No access'}), 403
    
    orders = load_json(ORDERS_FILE)
    for order in orders:
        if order['id'] == order_id:
            order['status'] = status
            break
    save_json(ORDERS_FILE, orders)
    
    flash(f'Статус заказа #{order_id} обновлён', 'success')
    return redirect(url_for('admin'))

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
