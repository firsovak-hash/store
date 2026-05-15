from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os

app = Flask(__name__)

# Товары
PRODUCTS = {
    '1': {
        'id': '1',
        'name': 'Чиби-фигурка пары',
        'price': 3500,
        'image': 'https://via.placeholder.com/600x400?text=Chibi+Couple',
        'description': 'Милые чиби-фигурки вас двоих. Высота 8-10 см.',
        'full_description': 'Персонализированные чиби-фигурки создаются по вашим фотографиям. Мы передаём причёску, цвет глаз, любимую одежду и даже мелкие детали. Ручная работа, акриловые краски, красивая упаковка. Срок 5-7 дней.',
        'badge': 'Хит'
    },
    '2': {
        'id': '2',
        'name': 'Фигурка с питомцем',
        'price': 4200,
        'image': 'https://via.placeholder.com/600x400?text=With+Pet',
        'description': 'Вы и ваш любимый питомец в одном кадре.',
        'full_description': 'Ваш пушистый друг заслуживает быть рядом с вами даже в миниатюре. Учитываем окрас, размер и характер животного.',
        'badge': 'Новинка'
    },
    '3': {
        'id': '3',
        'name': 'Спортивная фигурка',
        'price': 4500,
        'image': 'https://via.placeholder.com/600x400?text=Sports',
        'description': 'Для спортсменов. Любой вид спорта.',
        'full_description': 'Запечатлите свою спортивную форму и достижения. Любой вид спорта на ваш выбор.',
        'badge': ''
    },
    '4': {
        'id': '4',
        'name': 'Премиум фигурка',
        'price': 6500,
        'image': 'https://via.placeholder.com/600x400?text=Premium',
        'description': 'Максимальная детализация, полная покраска.',
        'full_description': 'Премиум-класс: фигурка большего размера, максимальная проработка. Упаковка с магнитным замком.',
        'badge': 'Премиум'
    },
    '5': {
        'id': '5',
        'name': 'Брелок-фигурка',
        'price': 1500,
        'image': 'https://via.placeholder.com/600x400?text=Keychain',
        'description': 'Миниатюра, которую всегда можно носить с собой.',
        'full_description': 'Маленькая копия с креплением для ключей.',
        'badge': ''
    },
    '6': {
        'id': '6',
        'name': 'Фигурка семьи',
        'price': 5500,
        'image': 'https://via.placeholder.com/600x400?text=Family',
        'description': 'Вся семья в одной композиции. До 5 человек.',
        'full_description': 'Семейная композиция — память на всю жизнь. Общая подставка с именами.',
        'badge': ''
    }
}

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

@app.route('/')
def index():
    return render_template('index.html', products=PRODUCTS_LIST)

@app.route('/catalog')
def catalog():
    return render_template('catalog.html', products=PRODUCTS_LIST)

@app.route('/product/<product_id>', methods=['GET', 'POST'])
def product_page(product_id):
    product = PRODUCTS.get(product_id)
    if not product:
        return redirect(url_for('index'))
    
    reviews = load_reviews()
    product_reviews = reviews.get(product_id, [])
    
    if request.method == 'POST':
        # Добавление отзыва
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
