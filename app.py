from flask import Flask, render_template

app = Flask(__name__)

PRODUCTS = {
    '1': {
        'id': '1',
        'name': 'Чиби-фигурка пары',
        'price': 3500,
        'description': 'Милые чиби-фигурки вас двоих. Высота 8-10 см.',
        'full_description': 'Персонализированные чиби-фигурки создаются по вашим фотографиям. Мы передаём причёску, цвет глаз, любимую одежду и даже мелкие детали. Ручная работа, акриловые краски, красивая упаковка. Срок 5-7 дней.',
        'badge': 'Хит'
    },
    '2': {
        'id': '2',
        'name': 'Фигурка с питомцем',
        'price': 4200,
        'description': 'Вы и ваш любимый питомец в одном кадре.',
        'full_description': 'Ваш пушистый друг заслуживает быть рядом с вами даже в миниатюре. Учитываем окрас, размер и характер животного.',
        'badge': 'Новинка'
    },
    '3': {
        'id': '3',
        'name': 'Спортивная фигурка',
        'price': 4500,
        'description': 'Для спортсменов. Любой вид спорта.',
        'full_description': 'Запечатлите свою спортивную форму и достижения. Любой вид спорта на ваш выбор.',
        'badge': ''
    },
    '4': {
        'id': '4',
        'name': 'Премиум фигурка',
        'price': 6500,
        'description': 'Максимальная детализация, полная покраска.',
        'full_description': 'Премиум-класс: фигурка большего размера, максимальная проработка. Упаковка с магнитным замком.',
        'badge': 'Премиум'
    },
    '5': {
        'id': '5',
        'name': 'Брелок-фигурка',
        'price': 1500,
        'description': 'Миниатюра, которую всегда можно носить с собой.',
        'full_description': 'Маленькая копия с креплением для ключей.',
        'badge': ''
    },
    '6': {
        'id': '6',
        'name': 'Фигурка семьи',
        'price': 5500,
        'description': 'Вся семья в одной композиции. До 5 человек.',
        'full_description': 'Семейная композиция — память на всю жизнь. Общая подставка с именами.',
        'badge': ''
    }
}

# Преобразуем в список для безопасного использования в шаблонах
PRODUCTS_LIST = list(PRODUCTS.values())

@app.route('/')
def index():
    return render_template('index.html', products=PRODUCTS_LIST)

@app.route('/catalog')
def catalog():
    return render_template('catalog.html', products=PRODUCTS_LIST)

@app.route('/product/<product_id>')
def product_page(product_id):
    product = PRODUCTS.get(product_id)
    if not product:
        return render_template('index.html', products=PRODUCTS_LIST)
    return render_template('product.html', product=product, product_id=product_id)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
