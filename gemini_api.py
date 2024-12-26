from google import genai
from google.genai.types import Tool, GoogleSearch, GenerateContentConfig, Content, Part
import os
import io
from dotenv import load_dotenv
from PIL import Image
from typing import List
import logging

load_dotenv()

API = os.getenv("GEMINI_KEY")
system_instruction = """Ты - многофункциональный ассистент, способный адаптироваться к различным задачам.

Для общения в диалоговом режиме: Поддерживай дружелюбный и эмпатичный тон. Отвечай развернуто, стараясь понять чувства пользователя. Используй разговорный стиль, как если бы ты общался с другом. Добавляй смайлики (но не перебарщивай), чтобы сделать общение более живым и эмоциональным. Не стесняйся задавать уточняющие вопросы для лучшего понимания запроса. Добавляй немного юмора и непринужденности в свои ответы.
Для задач, требующих формального подхода (например, написание сочинений, решение задач, предоставление информации): Переходи на более формальный и нейтральный стиль. Избегай использования смайликов и неформальных выражений. Отвечай точно и по существу, предоставляя необходимую информацию или решение.
В любом случае: Старайся не быть навязчивым и многословным. Придерживайся инструкций, если пользователь не попросит тебя изменить их. Не пиши привет каждое сообщение, если это не требуется в диалоге. Если пишешь задание какое-либо, выделяй его другим шрифтом, например курсивом. НИКОГДА НЕ ИСПОЛЬЗУЙ ЖИРНЫЙ КУРСИВ"""

# Настройка логгера
logger = logging.getLogger("gemini_api")
logger.setLevel(logging.DEBUG)
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
file_handler = logging.FileHandler(os.path.join(LOG_DIR, "gemini_api.log"), encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class Gemini:
    def __init__(self):
        self.client = genai.Client(api_key=API)
        self.model_id = 'gemini-2.0-flash-exp'
        self.google_search_tool = Tool(google_search=GoogleSearch())
        logger.debug("Gemini model initialized")

    async def generate_content(self, query: str, files: List[Image.Image] = None) -> str:
        parts = []
        parts.append(Part(text=query))

        if files:
            for image in files:
                image_bytes = io.BytesIO()
                image.save(image_bytes, format="JPEG")
                image_bytes = image_bytes.getvalue()
                parts.append(Part(inline_data={"mime_type": "image/jpeg", "data": image_bytes}))
        
        logger.debug(f"Gemini model generating with query: {query}, images: {bool(files)}")

        contents = [Content(parts=parts)]

        response = self.client.models.generate_content(
            model=self.model_id,
            contents=contents,           
            config=GenerateContentConfig(
                tools=[self.google_search_tool],
                response_modalities=['TEXT'],
                system_instruction=system_instruction
            )
        )
        if response.text:
           logger.debug(f"Gemini model answer is TEXT")
           return response.text
        elif response.candidates:
             logger.debug(f"Gemini model answer is CANDIDATES")
             return response.candidates[0].content.parts[0].text
        else:
          logger.warning(f"Gemini model answer is NO RESPONSE")
          return "No response from Gemini"

class GeminiThinking:
    def __init__(self):
        self.client = genai.Client(api_key=API)
        self.model_id = 'gemini-2.0-flash-thinking-exp-1219'
        logger.debug("GeminiThinking model initialized")

    async def generate_content(self, query: str, files: List[Image.Image] = None) -> str:
        parts = []
        parts.append(Part(text=query))

        if files:
            for image in files:
                image_bytes = io.BytesIO()
                image.save(image_bytes, format="JPEG")
                image_bytes = image_bytes.getvalue()
                parts.append(Part(inline_data={"mime_type": "image/jpeg", "data": image_bytes}))

        logger.debug(f"GeminiThinking model generating with query: {query}, images: {bool(files)}")

        contents = [Content(parts=parts)]

        response = self.client.models.generate_content(
            model=self.model_id,
            contents=contents,           
            config=GenerateContentConfig(
                response_modalities=['TEXT'],
                system_instruction=system_instruction
            )
        )

        if response.candidates:
            logger.debug(f"GeminiThinking model answer is CANDIDATES")
            return response.candidates[0].content.parts[0].text
        else:
          logger.warning(f"GeminiThinking model answer is NO RESPONSE")
          return "No response from Gemini"