from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import logging
import asyncio
from datetime import datetime, timedelta

# Вставьте сюда токен вашего бота
TOKEN = ''

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальные переменные для хранения состояния пользователя
user_selections = {}
user_last_interaction = {}
INACTIVITY_LIMIT = timedelta(minutes=5)

# Получатели сообщений для разных категорий
recipients = {
    '1': '397369287',  # ID чата для брошей, чокеров и бус
    '2': '2079786968',  # ID чата для жгутов и браслетов
    '3': '397369287',  # ID чата для кружек и изделий из полимерной глины
}

# Описание вариантов выбора
option_descriptions = {
    '1': "Понравилось из представленного",
    '2': "Хочу предложить свое"
}

# Функция для обработки команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Выбрать заказ", callback_data='show_buttons')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Если Вы хотите приступить к заказу, нажмите на кнопку ниже:",
                                    reply_markup=reply_markup)

    # Обновляем время последнего взаимодействия
    user_id = update.effective_user.id
    user_last_interaction[user_id] = datetime.now()

# Функция для обработки нажатий на кнопки
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Получаем информацию о пользователе, который нажал кнопку
    user = update.effective_user
    user_name = user.first_name
    user_id = user.id

    # Обновляем время последнего взаимодействия
    user_last_interaction[user_id] = datetime.now()

    try:
        if query.data == 'show_buttons':
            keyboard = [
                [InlineKeyboardButton("Брошь, чокер, бусы", callback_data='item_1')],
                [InlineKeyboardButton("Жгут, браслет", callback_data='item_2')],
                [InlineKeyboardButton("Кружку, изделие из полимерной глины", callback_data='item_3')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Что Вы хотите заказать?", reply_markup=reply_markup)

        elif query.data.startswith('item_'):
            item_id = query.data.split('_')[1]
            user_selections[user_id] = {'item_id': item_id}

            item_map = {
                '1': "брошь, чокер или бусы",
                '2': "жгут или браслет",
                '3': "кружку или изделие из полимерной глины"
            }

            item_name = item_map.get(item_id, 'неизвестный товар')

            keyboard = [
                [InlineKeyboardButton("Мне понравилось из представленного", callback_data=f'confirm_{item_id}_1')],
                [InlineKeyboardButton("Хочу предложить свое", callback_data=f'confirm_{item_id}_2')],
                [InlineKeyboardButton("Назад", callback_data='show_buttons')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=f"Отлично! Вы выбрали {item_name}. Выберите одно из следующих действий:", reply_markup=reply_markup)

        elif query.data.startswith('confirm_'):
            item_id, number = query.data.split('_')[1], query.data.split('_')[2]
            if user_id in user_selections:
                user_selections[user_id]['number'] = number

            item_map = {
                '1': "брошь, чокер или бусы",
                '2': "жгут или браслет",
                '3': "кружку или изделие из полимерной глины"
            }

            item_name = item_map.get(user_selections[user_id]['item_id'], 'неизвестный товар')
            option_description = option_descriptions.get(number, 'неизвестный вариант')
            recipient_id = recipients.get(user_selections[user_id]['item_id'], 'default_recipient_id')

            if recipient_id == 'default_recipient_id':
                await query.edit_message_text(text="Произошла ошибка, попробуйте снова.")
                return

            final_message = f"{user_name} хочет заказать {item_name}. Выбранный вариант: {option_description}. Связаться с пользователем: https://t.me/{user.username}"

            # Отправка полного сообщения
            try:
                await context.bot.send_message(chat_id=recipient_id, text=final_message)
            except Exception as e:
                logger.error(f"Failed to send message: {e}")

            await query.edit_message_text(text="Ваш заказ отправлен! Мы свяжемся с вами.")

            # Очистка выбора пользователя
            user_selections.pop(user_id, None)

        elif query.data == 'back_to_main':
            await start(update, context)

    except Exception as e:
        logger.error(f"Error processing callback: {e}")

# Функция для обработки текстовых сообщений
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Обновляем время последнего взаимодействия
    user_last_interaction[user_id] = datetime.now()

    if user_id not in user_selections:
        # Активируем пользователя при первом сообщении
        await update.message.reply_text("Добро пожаловать! Выберите опцию ниже.")
        await start(update, context)
    else:
        # Обработка текстовых сообщений в зависимости от состояния пользователя
        await update.message.reply_text("Пожалуйста, выберите действие через кнопки.")

# Функция для проверки бездействия пользователей
async def check_inactivity(context: ContextTypes.DEFAULT_TYPE):
    while True:
        now = datetime.now()
        to_remove = []
        for user_id, last_interaction in user_last_interaction.items():
            if now - last_interaction > INACTIVITY_LIMIT:
                try:
                    await context.bot.send_message(chat_id=user_id, text="Вы не активны уже 5 минут. Бот завершает работу. Спасибо за использование!")
                except Exception as e:
                    logger.error(f"Failed to send inactivity message: {e}")
                to_remove.append(user_id)

        for user_id in to_remove:
            user_last_interaction.pop(user_id, None)

        await asyncio.sleep(60)  # Проверяем каждые 60 секунд

# Основная функция для запуска бота
def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    # Запускаем задачу проверки бездействия
    application.job_queue.run_repeating(check_inactivity, interval=60, first=0)

    application.run_polling()

if __name__ == '__main__':
    main()
