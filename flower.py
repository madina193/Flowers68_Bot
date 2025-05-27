from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram import ReplyKeyboardMarkup, KeyboardButton
import sqlite3
import requests

from flower2 import TOKEN

FLOWERS = {
    "Розы": "https://rozmari05.ru/rozy/",
    "Тюльпаны": "https://rozmari05.ru/vesennie/tyulpany/",
    "Хризантемы": "https://rozmari05.ru/hrizantemy/",
}

class CartManager:
    def __init__(self):
        self.conn = sqlite3.connect("flowers.db", check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                user_id INTEGER,
                item TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS log (
                user_id INTEGER,
                username TEXT,
                action TEXT
            )
        """)
        self.conn.commit()

    def log_action(self, user_id: int, username: str, action: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO log (user_id, username, action) VALUES (?, ?, ?)",
            (user_id, username, action))
        self.conn.commit()

    def add_cart(self, user_id: int, item: str):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO cart VALUES (?, ?)", (user_id, item))
        self.conn.commit()

    def get_cart(self, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute("SELECT item FROM cart WHERE user_id = ?", (user_id,))
        return cursor.fetchall()

    def clear_cart(self, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()

cart_db = CartManager()

def flower_info(flower_name):
    try:
        url = f"https://api.inaturalist.org/v1/search?q={flower_name}&sources=taxa"
        response = requests.get(url)
        data = response.json()

        flower = data['results'][0]['record']

        nazvanie = flower.get('preferred_common_name', flower.get('name', 'Без названия'))
        description = flower.get('description', 'Нет описания')
        if len(description) > 300:
            description = description[:299] + "..."

        photo = flower.get('default_photo', {}).get('medium_url')

        text = f"🪻 Информация о цветке: {nazvanie}\n{description}"
        return text, photo

    except Exception as e:
        return "Не удалось найти информацию о цветке", None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("Добавить Розы")],
        [KeyboardButton("Добавить Тюльпаны")],
        [KeyboardButton("Добавить Хризантемы")],
        [KeyboardButton("Посмотреть корзину")],
        [KeyboardButton("Очистить корзину")],
        [KeyboardButton("Поиск по цветку")],
        [KeyboardButton("Наш каталог")],
        [KeyboardButton("О нас")],
        [KeyboardButton("Контакты")],
        [KeyboardButton("Оставить отзыв")]
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(" Здравствуйте! Чем могу помочь?",
        reply_markup=reply_markup)

    await update.message.reply_text("Добро пожаловать в наш цветочный магазин Rozmari.")
    await main_menu(update)

async def cart_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    items = cart_db.get_cart(user.id)
    if items:
        text = "Корзина:\n" + "\n".join(f"- {item[0]}" for item in items)
    else:
        text = "Корзина пуста"
    await update.message.reply_text(text)

async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cart_db.clear_cart(user.id)
    await update.message.reply_text("Корзина очищена.")

async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(name, url=url)] for name, url in FLOWERS.items()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Каталог букетов на сайте по ссылке: https://rozmari05.ru/buket-czvetov/", reply_markup=reply_markup)

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ("Мы Rozmari, цветочный магазин. Работаем в Махачкале с 2015 года.")
    await update.message.reply_text(text)

async def contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ("Наш адрес: г. Махачкала, пр. Имама-Шамиля, 4/1, тел: +7 (928) 555-55-55(контакт учебный)")
    await update.message.reply_text(text)

async def main_menu(update: Update):
    keyboard = [[InlineKeyboardButton(name, url=url)] for name, url in FLOWERS.items()]
    keyboard += [
        [InlineKeyboardButton("Посмотреть корзину", callback_data="view_cart")],
        [InlineKeyboardButton("Очистить корзину", callback_data="clear_cart")],
        [InlineKeyboardButton("Поиск по цветку", callback_data="help_name")],
        [InlineKeyboardButton("Наш каталог", callback_data="our_catalog")],
        [InlineKeyboardButton("О нас", callback_data="about")],
        [InlineKeyboardButton("Контакты", callback_data="contacts")],
        [InlineKeyboardButton("Оставить отзыв", callback_data="otziv")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите букет:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "view_cart":
        items = cart_db.get_cart(user_id)
        if items:
            cart_text = "\n".join(f"- {item[0]}" for item in items)
            await query.edit_message_text(f"Корзина:\n{cart_text}")
        else:
            await query.edit_message_text("Корзина пуста.")

    elif query.data == "clear_cart":
        cart_db.clear_cart(user_id)
        await query.edit_message_text("Корзина очищена.")

    elif query.data == "help_name":
        await query.edit_message_text("Введите название цветка, и я пришлю информацию о нём!")

    elif query.data == "our_catalog":
        await query.edit_message_text("Наш каталог на сайте по ссылке: https://rozmari05.ru/buket-czvetov/")

    elif query.data == "about":
        await query.edit_message_text("Мы Rozmari, цветочный магазин. Работаем в Махачкале с 2015 года.")

    elif query.data == "contacts":
        await query.edit_message_text(
            "Наш адрес: г. Махачкала, пр. Имама-Шамиля, 4/1, тел: +7 (928) 555-55-55(контакт учебный)")

    elif query.data == "otziv":
        await query.edit_message_text("Оставьте отзыв, мы его учтем!")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip().lower()

    if text == "добавить розы":
        cart_db.add_cart(user.id, "Розы")
        cart_db.log_action(user.id, user.username, "Добавил(а) розы в корзину")
        await update.message.reply_text("Розы добавлены в корзину")
        return

    elif text == "добавить тюльпаны":
        cart_db.add_cart(user.id, "Тюльпаны")
        cart_db.log_action(user.id, user.username, "Добавил(а) тюльпаны в корзину")
        await update.message.reply_text("Тюльпаны добавлены в корзину")
        return

    elif text == "добавить хризантемы":
        cart_db.add_cart(user.id, "Хризантемы")
        cart_db.log_action(user.id, user.username, "Добавил(а) хризантемы в корзину")
        await update.message.reply_text("Хризантемы добавлены в корзину")
        return

    if context.user_data.get("waiting_feedback"):
        context.user_data["waiting_feedback"] = False
        await update.message.reply_text("Спасибо за отзыв! Мы его учтём.")
        return

    if text == "очистить корзину":
        cart_db.log_action(
            user_id=user.id,
            username=user.username,
            action="Clear cart")
        cart_db.clear_cart(user.id)
        await update.message.reply_text("🛒 Корзина очищена")

    elif text == "посмотреть корзину":
        cart_db.log_action(
            user_id=user.id,
            username=user.username or "unknown",
            action="View cart")
        items = cart_db.get_cart(user.id)
        if items:
            cart_items = "\n".join([f"• {item[0]}" for item in items])
            response = f"🛍️ Корзина:\n{cart_items}"
        else:
            response = "Корзина пуста"
        await update.message.reply_text(response)

    elif text == "наш каталог":
        await catalog(update, context)
        return

    elif text == "о нас":
        await about(update, context)
        return

    elif text == "контакты":
        await contacts(update, context)
        return

    elif text == "поиск по цветку":
        context.user_data["search_flower"] = True
        await update.message.reply_text("Введите название цветка:")
        return

    if context.user_data.get("search_flower"):
        context.user_data["search_flower"] = False
        description, image = flower_info(text)
        if image:
            await update.message.reply_photo(photo=image, caption=description, parse_mode="Markdown")
        else:
            await update.message.reply_text(description)
        return

    await update.message.reply_text("Чтобы связаться с нашим флористом, обратитесь по номеру, указанному в наших контактах")

async def handle_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cart_db.clear_cart(user.id)
    await update.message.reply_text("Корзина успешно очищена")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    try:
        app.run_polling()
    finally:
        cart_db.close()

if __name__ == "__main__":
    main()