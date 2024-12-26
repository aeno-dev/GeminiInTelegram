# main.py
import io
import asyncio
import logging
import os
import re
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
from PIL import Image
from gemini_api import Gemini, GeminiThinking
from db import Database
import aiofiles
import aiofiles.os


load_dotenv()

TELEGRAM_API_KEY = os.getenv("TELEGRAM_TOKEN")

# Настройка логирования
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "bot.log")
os.makedirs(LOG_DIR, exist_ok=True)

# Настройка базового логгера
logger = logging.getLogger("bot")
logger.setLevel(logging.DEBUG)  # Устанавливаем общий уровень логирования DEBUG

# Создание обработчика для записи в файл
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setLevel(logging.DEBUG) # Все пишем в файл
file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Создание обработчика для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO) # Только INFO и выше в консоль
console_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)


bot = Bot(token=TELEGRAM_API_KEY)
dp = Dispatcher()

# ---  setup ---
db = Database()
gemini = Gemini()
gemini_thinking = GeminiThinking() # Создаем экземпляр GeminiThinking

PHOTOS_DIR = "photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)

# Функция для очистки текста от лишних символов и форматирования
def clean_text(text):
    if text is None:
        return ""
    # Заменяем множественные пробелы на один, но сохраняем \n для абзацев
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text) # Убираем более 2-х переносов
    text = text.strip()

    # Заменяем markdown на html
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    text = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', text, flags=re.DOTALL) # Моноширинный
    text = re.sub(r'~(.*?)~', r'<strike>\1</strike>', text) # Зачеркнутый
    
    # Корректно закрываем теги
    text = re.sub(r'<b>(.*?)</b>', r'<b>\1</b>', text)
    text = re.sub(r'<i>(.*?)</i>', r'<i>\1</i>', text)

    # Удаляем пробелы перед точками и другими знаками
    text = re.sub(r'\s*([.,?!])', r'\1', text)
    
    # Экранирование HTML спецсимволов
    text = text.replace("&", "&")
    text = text.replace("<", "<")
    text = text.replace(">", ">")
    text = text.replace('"', "'")
    
    return text

def truncate_text(text, max_length, end_chars = ".!?"):
     if len(text) <= max_length:
          return text
     
     for char in end_chars:
        last_end_index = text.rfind(char, 0, max_length)
        if last_end_index != -1:
           return text[:last_end_index + 1]
        
     return text[:max_length] + "..."

async def send_message_with_retry(bot: Bot, chat_id: int, text: str, retries=3, delay=2):
    """Отправляет сообщение, разделяя его на части и пробует несколько раз при ошибке."""
    
    max_message_length = 4096
    
    if len(text) <= max_message_length:
        for attempt in range(retries):
            try:
                 await bot.send_message(chat_id, text, parse_mode = "HTML")
                 return
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения(попытка {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
        logger.error(f"Не удалось отправить сообщение после {retries} попыток.")
        return

    # Разделение на части
    parts = [text[i:i + max_message_length] for i in range(0, len(text), max_message_length)]
    
    for part in parts:
        for attempt in range(retries):
             try:
                await bot.send_message(chat_id, part, parse_mode = "HTML")
                break
             except Exception as e:
                  logger.error(f"Ошибка отправки сообщения(попытка {attempt+1}/{retries}): {e}")
                  if attempt < retries - 1:
                     await asyncio.sleep(delay)
        else:
           logger.error(f"Не удалось отправить часть сообщения после {retries} попыток.")

async def save_image_to_disk(file_id, file_bytes):
    """Сохраняет изображение на диск."""
    file_path = os.path.join(PHOTOS_DIR, f"{file_id}.jpg")
    try:
        async with aiofiles.open(file_path, "wb") as f:
             await f.write(file_bytes)
        logger.debug(f"Saved image to disk: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error saving image to disk: {e}")
        return None

async def load_image_from_disk(file_path):
    """Загружает изображение с диска."""
    try:
         async with aiofiles.open(file_path, "rb") as f:
            image_bytes = await f.read()
            image = Image.open(io.BytesIO(image_bytes))
            return image
    except Exception as e:
          logger.error(f"Error loading image from disk: {e}")
          return None

async def clear_photos_dir():
     """Удаляет все файлы из папки с фотографиями"""
     try:
        for file_name in os.listdir(PHOTOS_DIR):
           file_path = os.path.join(PHOTOS_DIR, file_name)
           if os.path.isfile(file_path):
                await aiofiles.os.remove(file_path)
        logger.info("Photos directory cleaned")
     except Exception as e:
         logger.error(f"Error cleaning photos directory: {e}")
            
@dp.message(CommandStart())
async def start_handler(message: Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="/clear"),
                KeyboardButton(text="/model")
            ],
        ],
         resize_keyboard=True,
        
    )
    logger.info(f'{message.from_user.id},{message.from_user.full_name} used /start')
    await message.answer("Привет! Я бот, основанный на базе Gemini, семейства моделей от Google\nALFA, model can make some mistakes", reply_markup=keyboard)

@dp.message(Command('clear'))
async def clear_history(message: Message):
    logger.info(f'{message.from_user.id}, {message.from_user.full_name} cleared history and photos')
    db.clear_history(message.from_user.id)
    await clear_photos_dir()
    await message.answer("История запросов для модели и все изображения очищены!")

@dp.message(Command('model'))
async def model_handler(message: Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Gemini 2.0 Flash"),
                KeyboardButton(text="Gemini 2.0 Flash Thinking")
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        """Выберите модель:\n
<b>Gemini 2.0 Flash</b> - Молниеносные ответы и всегда свежие новости. Анализирует изображения и обрабатывает информацию как целую библиотеку книг. Идеально для скорости и точности.\n
<b>Gemini 2.0 Flash Thinking</b> - Глубокий анализ и развернутые ответы, анализирует изображения. Может погрузиться в детали, как в несколько книг, опираясь на знания, полученные в процессе обучения. Подходит для сложных задач и экспертного мнения.""",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.message(lambda message: message.text in ["Gemini 2.0 Flash", "Gemini 2.0 Flash Thinking"])
async def set_model_handler(message: Message):
    model_type = message.text
    db.set_model(message.from_user.id, model_type)
    logger.info(f'{message.from_user.id}, {message.from_user.full_name} selected model - {model_type}')
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="/clear"),
                KeyboardButton(text="/model")
            ],
        ],
        resize_keyboard=True
    )
    
    await message.answer(f"Выбрана модель: {model_type}", reply_markup = keyboard)

@dp.message(Command('agreement'))
async def send_agreement(message: Message):
    agreement_text = os.getenv("AGREEMENT")
    await message.answer(agreement_text, parse_mode='HTML')  # Разметка Markdown для жирного текста

# Кэш для альбомов и текстовых сообщений
album_cache = {}
text_cache = {}


async def process_album(bot, user_id, user_name, query, album_id, message):
        
    if album_id not in album_cache:
            album_cache[album_id] = {
                    "messages": [],
                    "timer": None
                }
            
    album_cache[album_id]["messages"].append(message)

    if album_cache[album_id]["timer"]:
         album_cache[album_id]["timer"].cancel()

    async def send_cached_album():
        messages = album_cache.get(album_id,{}).get("messages")
        if messages:
            await process_messages(bot, user_id, user_name, query, messages)
            del album_cache[album_id]

    # Запуск таймера
    album_cache[album_id]["timer"] = asyncio.create_task(asyncio.sleep(10), name = "album_timer")
    try:
       await album_cache[album_id]["timer"]
       await send_cached_album()

    except asyncio.CancelledError:
        pass # Таймер отменен

async def process_text_message(bot, user_id, user_name, query, message):
    if user_id not in text_cache:
            text_cache[user_id] = {
                    "messages": [],
                    "timer": None
                }
            
    text_cache[user_id]["messages"].append(message)

    if text_cache[user_id]["timer"]:
        text_cache[user_id]["timer"].cancel()

    async def send_cached_text():
        messages = text_cache.get(user_id,{}).get("messages")
        if messages:
            await process_messages(bot, user_id, user_name, query, messages)
            del text_cache[user_id]

    # Запуск таймера
    text_cache[user_id]["timer"] = asyncio.create_task(asyncio.sleep(3), name = "text_timer") # 3 секунды таймер
    try:
       await text_cache[user_id]["timer"]
       await send_cached_text()

    except asyncio.CancelledError:
        pass # Таймер отменен

           
async def prepare_prompt(bot,user_id, query, files, media):
    """Подготавливает промпт для Gemini."""
    history = db.get_history(user_id)
    prompt_parts = []
    processed_image_ids = set()
    model_type = db.get_current_model(user_id)
  
    if history:
         prompt_parts.append("История запросов:")
         for record in history:
            if record['image_ids']:
              for file_id in record['image_ids'].split(','):
                  if file_id and file_id not in processed_image_ids:
                      try:
                          file_path = os.path.join(PHOTOS_DIR, f"{file_id}.jpg")
                          if os.path.exists(file_path):
                               image = await load_image_from_disk(file_path)
                               if image:
                                   files.append(image)
                                   prompt_parts.append(f"Image : {file_id}")
                                   processed_image_ids.add(file_id)
                               else:
                                    prompt_parts.append(f"Image : {file_id} - Error loading")
                          else:
                                prompt_parts.append(f"Image : {file_id} - File not found")
                      except Exception as e:
                          logger.error(f"Error loading image from disk or saving: {e}")
            
            
            prompt_parts.append(f"User: {record['query']}")
            prompt_parts.append(f"Bot: {record['response']}")
            
            if record['image_ids']:
               for file_id in record['image_ids'].split(','):
                     if file_id:
                        prompt_parts.append(f"Image file_id: {file_id} -  this is a description")
         
    prompt_parts.append("---")
    prompt_parts.append(f"Current User Message: {query if query else 'Фотографии'}")
    if media:
        for i, caption in enumerate(media):
             if caption:
                prompt_parts.append(f"Caption {i+1} : {caption}")
             else:
                 prompt_parts.append(f"Image {i+1}: No caption")
    
    
    prompt_text = "\n".join(prompt_parts)
    logger.debug(f"Prompt for Gemini {user_id}:\n{prompt_text}")
    return prompt_text, model_type

async def generate_response(bot, message, prompt_text, model_type, files, user_id, query):
    """Генерирует ответ от Gemini и отправляет пользователю."""
    generation_message = await bot.send_message(message.chat.id, 'Готовлю подходящий ответ...')
    try:
        if model_type == 'gemini-2.0-flash-exp':
            response_text = await gemini.generate_content(prompt_text, files)
        elif model_type == 'gemini-2.0-flash-thinking-exp-1219':
             response_text = await gemini_thinking.generate_content(prompt_text, files)
        else:
            response_text = await gemini.generate_content(prompt_text, files)
            
        cleaned_response = clean_text(response_text)
        truncated_response = truncate_text(cleaned_response, 4000)
        
        # Устраняем нумерацию в конце
        truncated_response = re.sub(r'\s+\d+\s*$', '', truncated_response)  # Удаляет цифры в конце
        
        db.add_record(user_id, query if query else 'Файлы', cleaned_response, [], model_type)
        logger.info(f"Gemini({model_type}) answered to {user_id}")
        await bot.delete_message(message.chat.id, generation_message.message_id)
        await send_message_with_retry(bot, message.chat.id, truncated_response)
            
    except Exception as e:
            logger.exception(f"ERROR! {user_id} {message.from_user.full_name} : {query}")
            await bot.delete_message(message.chat.id, generation_message.message_id)
            await bot.send_message(message.chat.id, "Произошла ошибка при обработке запроса. Попробуйте еще раз.")

async def process_messages(bot, user_id, user_name, query, messages):
    files = []
    media = []
    image_ids = []
    log_message = ""
    message_type = "unknown"

    for item in messages:
            if item.photo:
                message_type = "photo"
                photo = item.photo[-1]
                file_id = photo.file_id
                file_info = await bot.get_file(file_id)
                file_bytes = await bot.download_file(file_info.file_path)
                
                file_path = await save_image_to_disk(file_id, file_bytes.read())
                if file_path:
                    image = await load_image_from_disk(file_path)
                    if image:
                        files.append(image)
                        image_ids.append(file_id)
                else:
                   logger.error(f"Failed to save file {file_id}")

                
                if item.caption:
                  media.append(item.caption)
                else:
                    media.append(None)

                if item.caption:
                    log_message = f"Photo + Caption: {item.caption}"
                else:
                    log_message = "Photo"
            

    if not messages[0].text:
        logger.info(f'User {user_id}, {user_name} sent {message_type} - {log_message}')
    else:
         message_type = "text"
         logger.info(f'User {user_id}, {user_name} sent {message_type} - {messages[0].text}')
    
    prompt_text, model_type = await prepare_prompt(bot,user_id, query, files, media)
    await generate_response(bot, messages[0], prompt_text, model_type, files, user_id, query)
    
    db.add_record(user_id, query if query else "photo", response = ' ', image_ids=image_ids, model_type = model_type)

@dp.message()
async def message_handler(message: Message, bot: Bot):
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    query = message.text
    files = []  # Объявляем переменную здесь
    
    if message.media_group_id:
         await process_album(bot, user_id, user_name, query, message.media_group_id, message)
    elif message.photo:
         await process_messages(bot, user_id, user_name, query, [message])
    elif message.text:
        await process_text_message(bot, user_id, user_name, query, message)

async def main():
    logger.info("Бот начал запуск...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())