import sqlite3
import asyncio
import hashlib
import aiogram.contrib.fsm_storage.memory

from aiogram import Dispatcher, Bot, types, executor
from aiogram.types.message import ContentType
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, InputMedia
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.callback_data import CallbackData
from aiogram.types import InputTextMessageContent, InlineQueryResultArticle
from datetime import date

Token_bot = '5224662237:AAHinmeM1NgsnRAqHIS1Vk55PzOgSwS0i_M'
Token_pay = '401643678:TEST:2239fe30-8f39-430b-9c21-74b3e59b8a06'

loop = asyncio.get_event_loop()

bot = Bot(token=Token_bot)
dp = Dispatcher(bot, loop=loop, storage=MemoryStorage())

courier_delivery_in_Tashtagol = types.ShippingOption(
    id='delivery',
    title='Доставка курьером'
).add(types.LabeledPrice('Доставка курьером', 30000))

courier_delivery_in_Sheregesh = types.ShippingOption(
    id='delivery',
    title='Доставка курьером'
).add(types.LabeledPrice('Доставка курьером', 10000))

pickup = types.ShippingOption(id='pickup',
                              title='Самовывоз',
                              ).add(types.LabeledPrice(label='Самовывоз', amount=0))
number_position = 0

class Form(StatesGroup):
    Q1 = State()
    promo_code = State()

    Edit = State()
    name_product = State()
    id_product = State()
    cost = State()
    photo = State()
    description = State()

    Right_or_not = State()

    Action = State()

    Confirmation = State()

    message_mailing = State()

def add_in_basket(id_user, id_product):
    try:
        con = sqlite3.connect('Delivery.db')
        cur = con.cursor()

        availability = cur.execute('SELECT amount FROM basket WHERE id_user = (?) AND id_product = (?)', [id_user, id_product]).fetchall()

        if len(availability) == 0:
            cur.execute('INSERT INTO basket(id_user, id_product, amount) VALUES(?, ?, ?)', [id_user, id_product, 1])
        else:
            cur.execute('UPDATE basket SET amount = (?) WHERE id_user = (?) AND id_product = (?)', [availability[0][0]+1, id_user, id_product])

        con.commit()
    finally:
        cur.close()
        con.close()

def information_position(message):
    try:
        con = sqlite3.connect('Delivery.db')
        cur = con.cursor()

        all_id_product_in_basket = cur.execute('SELECT id_product FROM basket WHERE id_user = (?)', [message.from_user.id]).fetchall()
        all_information_position = []

        for id_position in all_id_product_in_basket:
            position_in_basket = cur.execute('SELECT * FROM shop WHERE id_product = (?)', [id_position[0]]).fetchall()
            all_information_position.append(position_in_basket[0])
    finally:
        cur.close()
        con.close()

    return all_information_position

def finding_matches(id_product, message):
    try:
        con = sqlite3.connect('Delivery.db')
        cur = con.cursor()

        amount = cur.execute('SELECT amount FROM basket WHERE id_product = (?) AND id_user = (?)', [id_product, message.from_user.id]).fetchall()

        return amount[0][0]
    finally:
        cur.close()
        con.close()

def cost_promo_code(message, total_cost):
    meaning_discount = 0
    try:
        con = sqlite3.connect('Delivery.db')
        cur = con.cursor()

        name_promo_code = cur.execute('SELECT promo_code FROM active_promo_code WHERE id_user = (?)', [message.from_user.id]).fetchall()

        if len(name_promo_code) != 0:
            meaning_discount = cur.execute('SELECT meaning FROM promo_code WHERE promo_code = (?)', [name_promo_code[0][0]]).fetchall()[0][0]
    finally:
        cur.close()
        con.close()

    discount = total_cost-(total_cost * float(meaning_discount))

    return discount

def change_quantity(quantit, len):
    markup = InlineKeyboardMarkup(row_width=3)
    minus = InlineKeyboardButton('-', callback_data='minus')
    amount = InlineKeyboardButton(f'{quantit} шт.', callback_data=' ')
    position = InlineKeyboardButton(f'{number_position+1}\{len}', callback_data=' ')
    plus = InlineKeyboardButton('+', callback_data='plus')
    markup.add(minus, amount, plus)
    markup.row_width = 3
    next = InlineKeyboardButton('След. позиция', callback_data='next_position')
    back = InlineKeyboardButton('Пред. позиция', callback_data='back_position')
    buy = InlineKeyboardButton('Перейти к оплате', callback_data='buy')
    menu = InlineKeyboardButton('Перейти в меню', callback_data='menu')
    markup.add(back, position, next, buy, menu)
    markup.row_width = 1
    main_menu = InlineKeyboardButton("Главное меню", callback_data='main_menu')
    markup.add(main_menu)

    return markup

def not_main_menu(message):
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    menu = KeyboardButton('Каталог продукции')
    basket = KeyboardButton('Перейти в корзину')
    per = KeyboardButton('Ваши заказы')
    promo_code = KeyboardButton('Активировать промокод')
    markup.add(menu, basket, per, promo_code)

    if message.from_user.id == 520794257:
        markup.row_width = 1
        nothing = KeyboardButton('Рассылка сообщения')
        markup.add(nothing)
        markup.row_width = 2
        add = KeyboardButton('Добавить позицию')
        delete = KeyboardButton('Удалить позицию')
        markup.add(delete, add)

    return markup

def description_active_promo_code(message):
    try:
        con = sqlite3.connect('Delivery.db')
        cur = con.cursor()

        name_promo_code = cur.execute('SELECT promo_code FROM active_promo_code WHERE id_user = (?)', [message.from_user.id]).fetchall()
    finally:
        cur.close()
        con.close()

    try:
        con = sqlite3.connect('Delivery.db')
        cur = con.cursor()

        description = cur.execute('SELECT description FROM promo_code WHERE promo_code = (?)', [name_promo_code[0][0]]).fetchall()

        return description[0][0]
    finally:
        cur.close()
        con.close()

def total_cost_basket(position_in_basket, number_of_goods, message):
    total_cost = 0

    for cost in position_in_basket:
        total_cost += cost[3] * finding_matches(cost[2], message)

    return total_cost

def cancel():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    cancel = KeyboardButton('Отмена')
    markup.add(cancel)

    return markup
@dp.message_handler(state=Form.message_mailing)
async def mailing(message: types.Message, state: FSMContext):
    answer = message.text
    await state.finish()

    try:
        con = sqlite3.connect('Delivery.db')
        cur = con.cursor()

        cur.execute("SELECT id_user FROM id_user")
        all_id = cur.fetchall()

        for i in all_id:
            await bot.send_message(i[0], answer)
    finally:
        cur.close()
        con.close()

    await bot.send_message(520794257, 'Рассылка произведена', reply_markup=not_main_menu(message))
    await Form.Q1.set()

@dp.message_handler(state=Form.name_product)
async def name_product(message: types.Message, state: FSMContext):
    if message.text == 'Отмена':
        await bot.send_message(message.chat.id, 'Добавление товара отменено', reply_markup=not_main_menu(message))
        await Form.Q1.set()
    else:
        await state.update_data(name_product=message.text)
        await bot.send_message(message.chat.id, 'Айди позиции', reply_markup=cancel())
        await Form.id_product.set()

@dp.message_handler(state=Form.id_product)
async def id_product(message: types.Message, state: FSMContext):
    if message.text == 'Отмена':
        await bot.send_message(message.chat.id, 'Добавление товара отменено', reply_markup=not_main_menu(message))
        await Form.Q1.set()
    else:
        await state.update_data(id_product=message.text)
        await bot.send_message(message.chat.id, 'Укажите стоимость позиции', reply_markup=cancel())
        await Form.cost.set()

@dp.message_handler(state=Form.cost)
async def cost(message: types.Message, state: FSMContext):
    if message.text == 'Отмена':
        await bot.send_message(message.chat.id, 'Добавление товара отменено', reply_markup=not_main_menu(message))
        await Form.Q1.set()
    else:
        await state.update_data(cost=message.text)
        await bot.send_message(message.chat.id, 'Отправьте URL фотографии', reply_markup=cancel())
        await Form.photo.set()

@dp.message_handler(state=Form.photo)
async def photo(message: types.Message, state: FSMContext):
    if message.text == 'Отмена':
        await bot.send_message(message.chat.id, 'Добавление товара отменено', reply_markup=not_main_menu(message))
        await Form.Q1.set()
    else:
        await state.update_data(photo=message.text)
        await bot.send_message(message.chat.id, 'Придумайте описание позиции', reply_markup=cancel())
        await Form.description.set()

@dp.message_handler(state=Form.description)
async def description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)

    user_data = await state.get_data()

    await bot.send_message(message.chat.id, 'Позиция в меню будет выглядеть так:')

    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    Right = KeyboardButton('Верно!')
    Not_Properly = KeyboardButton('Изменить позицию')
    markup.add(Right, Not_Properly)

    text = f'''{user_data.get('name_product')} \n\n{user_data.get('description')} \n\nЦена: {user_data.get('cost')} р.'''

    await bot.send_photo(message.chat.id, caption=text, photo=user_data.get('photo'), reply_markup=markup)
    await Form.Right_or_not.set()

@dp.message_handler(state=Form.Right_or_not)
async def Right_or_not(message: types.Message, state: FSMContext):
    answer = message.text

    user_data = await state.get_data()
    await state.finish()

    if answer == 'Верно!':
        try:
            con = sqlite3.connect('Delivery.db')
            cur = con.cursor()

            cur.execute('INSERT INTO shop(name_product, id_product, cost, photo, description) VALUES (?, ?, ?, ?, ?)',
                        [user_data.get('name_product'), user_data.get('id_product'), user_data.get('cost'),
                         user_data.get('photo'), user_data.get('description')])
            con.commit()
        finally:
            cur.close()
            con.close()

        await bot.send_message(message.chat.id, 'Позиция добавлена в меню!', reply_markup=not_main_menu(message))
        await Form.Q1.set()
    elif answer == 'Изменить позицию':
        await bot.send_message(message.chat.id, 'Введите название продукта', reply_markup=cancel())
        await Form.name_product.set()

@dp.message_handler(state=Form.Confirmation)
async def confirmation(message: types.Message, state: FSMContext):
    answer = message.text
    user_data = await state.get_data()
    await state.finish()

    if answer == 'Да':
        try:
            con = sqlite3.connect('Delivery.db')
            cur = con.cursor()

            cur.execute('DELETE from shop WHERE id_product = (?)', [user_data.get('id_product')])

            con.commit()
        finally:
            cur.close()
            con.close()

        await bot.send_message(message.chat.id, 'Товар удалён из меню!', reply_markup=not_main_menu(message))
        await Form.Q1.set()
    elif answer == 'Нет':
        await bot.send_message(message.chat.id, 'Товар не удалён', reply_markup=not_main_menu(message))
        await Form.Q1.set()
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    checklist = []
    try:
        con = sqlite3.connect('Delivery.db')
        cur = con.cursor()
        id_user = message.from_user.id

        all_id_user = cur.execute('SELECT id_user FROM id_user').fetchall()

        for i in all_id_user:
            checklist.append(int(i[0]))

        if id_user not in checklist:
            cur.execute('INSERT INTO id_user(id_user) VALUES (?)', [id_user])
            con.commit()
    finally:
        cur.close()
        con.close()

    await Form.Edit.set()
    await bot.send_message(message.chat.id, 'Рады приветствовать вас в нашем боте по доставке еды. Название нашего кафе: "Кристалл".', reply_markup=not_main_menu(message))

    await Form.Q1.set()
@dp.message_handler(state=Form.Q1)
async def menu(message: types.Message, state: FSMContext):
    answer = message.text

    await state.finish()

    if answer == 'Каталог продукции':
        try:
            con = sqlite3.connect('Delivery.db')
            cur = con.cursor()

            list_product = cur.execute('SELECT * FROM shop').fetchall()
        finally:
            cur.close()
            con.close()

        await bot.send_message(message.chat.id, 'В нашем меню представлены лучше блюда мира!', reply_markup=ReplyKeyboardRemove())

        for card in range(len(list_product)):
            markup = InlineKeyboardMarkup(row_width=2, resize_keyboard=True)
            menu = InlineKeyboardButton('Добавить в корзину', callback_data=f'add_in_basket|{list_product[card][2]}')
            basket = InlineKeyboardButton('Перейти в корзину', callback_data='go_in_basket')
            markup.add(menu, basket)
            markup.row_width = 1
            main_menu = InlineKeyboardButton("Главное меню", callback_data='main_menu')
            markup.add(main_menu)

            text = f'{list_product[card][1]} \n\n{list_product[card][5]} \n\nЦена: {list_product[card][3]} р.'

            await bot.send_photo(message.chat.id, caption=text, photo=list_product[card][4], reply_markup=markup)

    elif answer == 'Перейти в корзину':
        number_position = 0
        position_in_basket = information_position(message)

        if len(position_in_basket) == 0:
            await bot.send_message(message.chat.id, 'Корзина пуста! Ознакомьтесь с нашим меню.')

            await Form.Q1.set()
        else:
            number_of_goods = finding_matches(position_in_basket[number_position][2], message)
            total_cost = total_cost_basket(position_in_basket, number_of_goods, message)

            await bot.send_message(message.chat.id, 'Здесь находятся самый вкусные блюда выбранные Вами из нашего меню!', reply_markup=ReplyKeyboardRemove())

            if len(position_in_basket) == 1:
                markup = InlineKeyboardMarkup(row_width=3)
                minus = InlineKeyboardButton('-', callback_data='minus')
                amount = InlineKeyboardButton(f'{number_of_goods} шт.', callback_data=' ')
                plus = InlineKeyboardButton('+', callback_data='plus')
                markup.add(minus, amount, plus)
                markup.row_width = 1
                buy = InlineKeyboardButton('Перейти к оплате', callback_data='buy')
                markup.add(buy)
            else:
                markup = change_quantity(number_of_goods, len(position_in_basket))

            text = f'''{position_in_basket[number_position][1]} \n
Цена за еденицу: {position_in_basket[number_position][3]} \n
{position_in_basket[number_position][5]}
\nКоличество товара в корзине: {number_of_goods}\n
Цена без скидки:{total_cost}
Цена со скидкой: {cost_promo_code(message, total_cost)}'''

            await bot.send_photo(message.chat.id, photo=position_in_basket[number_position][4], caption=text, reply_markup=markup)

    elif answer == 'Ваши заказы':
        try:
            con = sqlite3.connect('Delivery.db')
            cur = con.cursor()

            all_history = cur.execute('SELECT * FROM history WHERE id_user = (?)', [message.chat.id]).fetchall()

            if len(all_history) == 0:
                await bot.send_message(message.chat.id, 'История заказов отсутвтует')
            else:
                for order in all_history:
                    await bot.send_message(message.chat.id, f'''Дата заказа: {order[2]};
Состав заказа: {order[3]};
Адрес доставки: {order[4]};
Итоговая стоимсть: {order[6]}''')
        finally:
            cur.close()
            con.close()

        await Form.Q1.set()

    elif answer == 'Активировать промокод':
        await bot.send_message(message.chat.id, 'Введите промокод', reply_markup=ReplyKeyboardRemove())

        await Form.promo_code.set()

    elif answer == 'Добавить позицию':
        await bot.send_message(message.chat.id, 'Введите название продукта', reply_markup=cancel())

        await Form.name_product.set()
    elif answer == 'Удалить позицию':
        try:
            con = sqlite3.connect('Delivery.db')
            cur = con.cursor()

            list_product = cur.execute('SELECT * FROM shop').fetchall()
        finally:
            cur.close()
            con.close()

        await bot.send_message(message.chat.id, 'Какую позицию вы хотите удалить', reply_markup=ReplyKeyboardRemove())

        for card in range(len(list_product)):
            markup = InlineKeyboardMarkup(row_width=2, resize_keyboard=True)
            Change = InlineKeyboardButton('Удалить позицию', callback_data=f'Delete|{list_product[card][2]}')
            main_menu = InlineKeyboardButton("Главное меню", callback_data='main_menu')
            markup.add(Change, main_menu)

            text = f'{list_product[card][1]} \n\n{list_product[card][5]} \n\nЦена: {list_product[card][3]} р.'

            await bot.send_message(message.chat.id, text, reply_markup=markup)
    elif answer == 'Рассылка сообщения':
        await bot.send_message(520794257, "Введите текст рассылки.", reply_markup=ReplyKeyboardRemove())

        await Form.message_mailing.set()
    else:
        await bot.send_message(message.chat.id, 'Вы выбрали другое')
        await Form.Q1.set()

@dp.message_handler(state=Form.promo_code)
async def promo_code(message: types.Message, state: FSMContext):
    answer = message.text

    await state.finish()

    try:
        con = sqlite3.connect('Delivery.db')
        cur = con.cursor()

        all_promo_code_DB = cur.execute('SELECT promo_code FROM promo_code').fetchall()
        all_promo_code = [promo_code[0] for promo_code in all_promo_code_DB]
    finally:
        cur.close()
        con.close()

    try:
        con = sqlite3.connect('Delivery.db')
        cur = con.cursor()

        if answer in all_promo_code:
            active_promo_code = cur.execute('SELECT promo_code FROM active_promo_code WHERE id_user = (?)', [message.chat.id]).fetchall()

            if len(active_promo_code) == 0:
                used = cur.execute('SELECT id_user FROM used_promo_codes WHERE used = (?)', [answer]).fetchall()

                if len(used) == 0:
                    cur.execute('INSERT INTO used_promo_codes(id_user, used) VALUES (?, ?)', [message.from_user.id, answer])
                    cur.execute('INSERT INTO active_promo_code(id_user, promo_code) VALUES (?, ?)' , [message.from_user.id, answer])

                    con.commit()

                    await bot.send_message(message.chat.id, 'Промокод успешно активирован!', reply_markup=not_main_menu(message))

                else:
                    await bot.send_message(message.chat.id, 'Вы уже использовали данный промокод', reply_markup=not_main_menu(message))
            else:
                description = description_active_promo_code(message)

                await bot.send_message(message.chat.id, f'Вы уже активировали промокод:\n\n{description}\n\nДля применения просто оформите заказ в нашем ресторане!', reply_markup=not_main_menu(message))
        else:
            await bot.send_message(message.chat.id, 'Такого промокода нет!', reply_markup=not_main_menu(message))

    finally:
        cur.close()
        con.close()

    await Form.first()

@dp.callback_query_handler(lambda call: True)
async def call_back(call: CallbackQuery, state: FSMContext):
    global number_position

    if call.data.startswith('add_in_basket'):
        add_in_basket(call.from_user.id, call.data.split('|')[1])

        await bot.send_message(call.message.chat.id, 'Товар добавлен в корзину')

    elif call.data.startswith('Delete'):
        try:
            con = sqlite3.connect('Delivery.db')
            cur = con.cursor()

            removeable_name_product = cur.execute('SELECT name_product FROM shop WHERE id_product = (?)', [call.data.split('|')[1]]).fetchall()

            markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            yes = KeyboardButton('Да')
            no = KeyboardButton('Нет')
            markup.add(yes, no)
            await bot.send_message(call.message.chat.id, f'Вы действительно хотите удалить {removeable_name_product}?', reply_markup=markup)

            await state.update_data(id_product=call.data.split('|')[1])

            await Form.Confirmation.set()
        finally:
            cur.close()
            con.close()

    elif call.data == 'menu':
        try:
            con = sqlite3.connect('Delivery.db')
            cur = con.cursor()

            list_product = cur.execute('SELECT * FROM shop').fetchall()
        finally:
            cur.close()
            con.close()

        for card in range(len(list_product)):
            markup = InlineKeyboardMarkup(row_width=2, resize_keyboard=True)
            menu = InlineKeyboardButton('Добавить в корзину', callback_data=f'add_in_basket|{list_product[card][2]}')
            basket = InlineKeyboardButton('Перейти в корзину', callback_data='go_in_basket')
            markup.add(menu, basket)
            markup.row_width = 1
            main_menu = InlineKeyboardButton("Главное меню", callback_data='main_menu')
            markup.add(main_menu)

            text = f'{list_product[card][1]} \n\n{list_product[card][5]} \n\nЦена: {list_product[card][3]} р.'

            await bot.send_photo(call.message.chat.id, caption=text, photo=list_product[card][4], reply_markup=markup)

    elif call.data == 'go_in_basket':
        number_position = 0
        position_in_basket = information_position(call)

        if len(position_in_basket) == 0:
            await bot.send_message(call.message.chat.id, 'Корзина пуста! Ознакомьтесь с нашим меню.')
        else:
            number_of_goods = finding_matches(position_in_basket[number_position][2], call)
            total_cost = total_cost_basket(position_in_basket, number_of_goods, call)

            if len(position_in_basket) == 1:
                markup = InlineKeyboardMarkup(row_width=3)
                minus = InlineKeyboardButton('-', callback_data='minus')
                amount = InlineKeyboardButton(f'{number_of_goods} шт.', callback_data=' ')
                plus = InlineKeyboardButton('+', callback_data='plus')
                markup.add(minus, amount, plus)
                markup.row_width = 1
                buy = InlineKeyboardButton('Перейти к оплате', callback_data='buy')
                markup.add(buy)
            else:
                markup = change_quantity(number_of_goods, len(position_in_basket))

            text = f'''{position_in_basket[number_position][1]} \n
Цена за еденицу: {position_in_basket[number_position][3]} \n
{position_in_basket[number_position][5]} \n
Количество товара в корзине: {number_of_goods} \n
Цена без скидки:{total_cost}
Цена со скидкой: {cost_promo_code(call, total_cost)}'''

            await bot.send_photo(call.message.chat.id, photo=position_in_basket[number_position][4], caption=text, reply_markup=markup)

    elif call.data == 'next_position':
        position_in_basket = information_position(call)

        number_position += 1

        if number_position == len(position_in_basket):
            number_position = 0

        number_of_goods = finding_matches(position_in_basket[number_position][2], call)
        total_cost = total_cost_basket(position_in_basket, number_of_goods, call)

        markup = change_quantity(number_of_goods, len(position_in_basket))

        text = f'''{position_in_basket[number_position][1]} \n
Цена за еденицу: {position_in_basket[number_position][3]} \n
{position_in_basket[number_position][5]}
\nКоличество товара в корзине: {number_of_goods}\n
Цена без скидки:{total_cost}
Цена со скидкой: {cost_promo_code(call, total_cost)}'''

        file = InputMedia(media=position_in_basket[number_position][4], caption=text)

        await call.message.edit_media(file, reply_markup=markup)

    elif call.data == 'back_position':
        position_in_basket = information_position(call)

        number_position -= 1

        if number_position == -1:
            number_position = len(position_in_basket) - 1

        number_of_goods = finding_matches(position_in_basket[number_position][2], call)
        total_cost = total_cost_basket(position_in_basket, number_of_goods, call)

        markup = change_quantity(number_of_goods, len(position_in_basket))

        text = f'''{position_in_basket[number_position][1]} \n
Цена за еденицу: {position_in_basket[number_position][3]} \n
{position_in_basket[number_position][5]}
\nКоличество товара в корзине: {number_of_goods}\n
Цена без скидки:{total_cost}
Цена со скидкой: {cost_promo_code(call, total_cost)}'''

        file = InputMedia(media=position_in_basket[number_position][4], caption=text)

        await call.message.edit_media(file, reply_markup=markup)

    elif call.data == 'minus':
        try:
            position_in_basket = information_position(call)
            number_of_goods = finding_matches(position_in_basket[number_position][2], call)

            con = sqlite3.connect('Delivery.db')
            cur = con.cursor()

            if number_of_goods == 1:
                cur.execute('DELETE from basket WHERE id_user = (?) AND id_product = (?)',[call.from_user.id, position_in_basket[number_position][2]])

                con.commit()

                position_in_basket = information_position(call)

                number_position -= 1

                if number_position == -1:
                    number_position = len(position_in_basket) - 1

            else:
                cur.execute('UPDATE basket SET amount = (?) WHERE id_user = (?) AND id_product = (?)', [number_of_goods - 1, call.from_user.id, position_in_basket[number_position][2]])
                con.commit()
        finally:
            cur.close()
            con.close()

        position_in_basket = information_position(call)

        if len(position_in_basket) != 0:
            number_of_goods = finding_matches(position_in_basket[number_position][2], call)
            total_cost = total_cost_basket(position_in_basket, number_of_goods, call)

            text = f'''{position_in_basket[number_position][1]} \n
Цена за еденицу: {position_in_basket[number_position][3]} \n
{position_in_basket[number_position][5]}
\nКоличество товара в корзине: {number_of_goods}\n
Цена без скидки:{total_cost}
Цена со скидкой: {cost_promo_code(call, total_cost)}'''

            file = InputMedia(media=position_in_basket[number_position][4], caption=text)

            if len(position_in_basket) == 1:
                markup = InlineKeyboardMarkup(row_width=3)
                minus = InlineKeyboardButton('-', callback_data='minus')
                amount = InlineKeyboardButton(f'{number_of_goods} шт.', callback_data=' ')
                plus = InlineKeyboardButton('+', callback_data='plus')
                markup.add(minus, amount, plus)
                markup.row_width = 1
                buy = InlineKeyboardButton('Перейти к оплате', callback_data='buy')
                markup.add(buy)

            else:
                markup = change_quantity(number_of_goods, len(position_in_basket))

            await call.message.edit_media(file, reply_markup=markup)

        else:
            await bot.delete_message(call.message.chat.id, call.message.message_id)

            await bot.send_message(call.message.chat.id, 'Корзина пуста! \n\nОзнакомьтесь с нашим великолепным меню!', reply_markup=not_main_menu(call))
            await Form.Q1.set()

    elif call.data == 'plus':
        try:
            position_in_basket = information_position(call)
            number_of_goods = finding_matches(position_in_basket[number_position][2], call)

            con = sqlite3.connect('Delivery.db')
            cur = con.cursor()

            cur.execute('UPDATE basket SET amount = (?) WHERE id_user = (?) AND id_product = (?)', [number_of_goods + 1, call.from_user.id, position_in_basket[number_position][2]])
            con.commit()
        finally:
            cur.close()
            con.close()

        position_in_basket = information_position(call)
        number_of_goods = finding_matches(position_in_basket[number_position][2], call)
        total_cost = total_cost_basket(position_in_basket, number_of_goods, call)

        if len(position_in_basket) == 1:
            markup = InlineKeyboardMarkup(row_width=3)
            minus = InlineKeyboardButton('-', callback_data='minus')
            amount = InlineKeyboardButton(f'{number_of_goods} шт.', callback_data=' ')
            plus = InlineKeyboardButton('+', callback_data='plus')
            markup.add(minus, amount, plus)
            markup.row_width = 1
            buy = InlineKeyboardButton('Перейти к оплате', callback_data='buy')
            markup.add(buy)
        else:
            markup = change_quantity(number_of_goods, len(position_in_basket))

        text = f'''{position_in_basket[number_position][1]} \n
Цена за еденицу: {position_in_basket[number_position][3]} \n
{position_in_basket[number_position][5]}
\nКоличество товара в корзине: {number_of_goods}\n
Цена без скидки:{total_cost}
Цена со скидкой: {cost_promo_code(call, total_cost)}'''

        file = InputMedia(media=position_in_basket[number_position][4], caption=text)

        await call.message.edit_media(file, reply_markup=markup)

    elif call.data == 'buy':
        position_in_basket = information_position(call)
        price = []
        try:
            con = sqlite3.connect('Delivery.db')
            cur = con.cursor()

            name_promo_code = cur.execute('SELECT promo_code FROM active_promo_code WHERE id_user = (?)', [call.from_user.id]).fetchall()

            if len(name_promo_code) != 0:
                discount = cur.execute('SELECT meaning FROM promo_code WHERE promo_code = (?)', [name_promo_code[0][0]]).fetchall()[0][0]
        finally:
            cur.close()
            con.close()

        for label_and_cost in position_in_basket:
            cost_product = label_and_cost[3]
            amount = finding_matches(label_and_cost[2], call)
            total_cost = (int(cost_product) * int(amount)) * 100

            if len(name_promo_code) != 0:
                total_cost_discount = total_cost - int(total_cost * float(discount))

                price.append(types.LabeledPrice(label=f'{label_and_cost[1]}; {amount} шт.', amount=total_cost_discount))
            else:
                price.append(types.LabeledPrice(label=f'{label_and_cost[1]}; {amount} шт.', amount=total_cost))

        number_of_goods = finding_matches(position_in_basket[number_position][2], call)
        total_cost = total_cost_basket(position_in_basket, number_of_goods, call)

        if total_cost < 500:
            await bot.answer_callback_query(callback_query_id=call.id, text="Минмальная суммая заказа 500 рублей.",
                                            show_alert=True)
        else:
            await bot.send_invoice(call.message.chat.id,
                                   title='Кристалл',
                                   description='Доставка еды',
                                   provider_token=Token_pay,
                                   currency='rub',
                                   photo_url='https://s82079.cdn.ngenix.net/330x0/6dkshniqjjc9ci82o610qn485ykw',
                                   photo_height=512,
                                   photo_width=521,
                                   photo_size=512,
                                   is_flexible=True,
                                   need_phone_number=True,
                                   prices=price,
                                   start_parameter='start_parametrs',
                                   payload='payload',
                                   )

    elif call.data == 'main_menu':
        await bot.send_message(call.message.chat.id, 'Главное меню', reply_markup=not_main_menu(call))

        await Form.Q1.set()

@dp.shipping_query_handler(lambda query: True)
async def process_shipping_query(shipping_query:types.ShippingQuery):
    shipping_options = []

    if shipping_query.shipping_address.city == 'Таштагол':
        shipping_options.append(courier_delivery_in_Tashtagol)
        shipping_options.append(pickup)

    elif shipping_query.shipping_address.city == 'Шерегеш':
        shipping_options.append(courier_delivery_in_Sheregesh)
        shipping_options.append(pickup)
    else:
        return await bot.answer_shipping_query(
            shipping_query.id,
            ok=False,
            error_message='Доставка возможна только в другие города')

    await bot.answer_shipping_query(shipping_query.id,
                                    ok=True,
                                    shipping_options=shipping_options)

@dp.pre_checkout_query_handler(lambda query: True)
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message_handler(content_types=ContentType.SUCCESSFUL_PAYMENT)
async def process_successful_payment(message: types.Message):
    position_in_basket = information_position(message)
    number_of_goods = finding_matches(position_in_basket[number_position][2], message)

    position_in_order = []
    address = []

    for position in position_in_basket:
        position_in_order.append(position[1])
        position_in_order.append(f' {number_of_goods}шт.; ')

    position_in_order_str = ''.join(position_in_order)

    pmnt = message.successful_payment.to_python()

    phone_number = pmnt.get('order_info').get('phone_number')

    address.append(f'''{pmnt.get('order_info').get('shipping_address').get('city')} ;''')
    address.append(pmnt.get('order_info').get('shipping_address').get('street_line1'))

    address_str = ''.join(address)

    total_cost = str(int(pmnt.get('total_amount')) /100)

    shipping_option_id = pmnt.get('shipping_option_id')

    if shipping_option_id == 'delivery':
        delivery_merhod = 'Доставка курьером'
    else:
        delivery_merhod = 'Самовывоз'

    try:
        con = sqlite3.connect('Delivery.db')
        cur = con.cursor()

        cur.execute('INSERT INTO history(id_user, order_date, order_items, address, phone_number, total_cost, delivery_method) VALUES(?, ?, ?, ?, ?, ?, ?)', [message.from_user.id, date.today(), position_in_order_str, address_str, phone_number, total_cost, delivery_merhod])

        cur.execute('DELETE FROM basket WHERE id_user = (?) ', [message.from_user.id])

        cur.execute('DELETE from active_promo_code WHERE id_user = (?)', [message.from_user.id])

        name_promo_code = cur.execute('SELECT promo_code FROM active_promo_code WHERE id_user = (?)', [message.from_user.id]).fetchall()
        if len(name_promo_code) != 0:
            cur.execute('INSERT INTO used_promo_codes(id_user, used) VALUES (?, ?)', [message.from_user.id, name_promo_code[0][0]])

        con.commit()

    finally:
        cur.close()
        con.close()

    await bot.send_message(message.chat.id, 'Спасибо за приобретение товара', reply_markup=not_main_menu(message))
    await Form.Q1.set()

    await bot.send_message(520794257, f'''Поступил заказ: {position_in_order_str}\n
{delivery_merhod}
Адрес: {address_str}
Номер телефона: {phone_number}
Итоговая цена: {total_cost}''')

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)