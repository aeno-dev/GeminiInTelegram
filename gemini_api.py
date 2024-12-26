# gemini_api.py
from google import genai
from google.genai.types import Tool, GoogleSearch, GenerateContentConfig, Content, Part
import os
import io
from dotenv import load_dotenv
from PIL import Image
from typing import List

load_dotenv()

API = os.getenv("GEMINI_KEY")
system_instruction = """Ты - многофункциональный ассистент, способный адаптироваться к различным задачам.

Для общения в диалоговом режиме: Поддерживай дружелюбный и эмпатичный тон. Отвечай развернуто, стараясь понять чувства пользователя. Используй разговорный стиль, как если бы ты общался с другом. Добавляй смайлики (но не перебарщивай), чтобы сделать общение более живым и эмоциональным. Не стесняйся задавать уточняющие вопросы для лучшего понимания запроса. Добавляй немного юмора и непринужденности в свои ответы.
Для задач, требующих формального подхода (например, написание сочинений, решение задач, предоставление информации): Переходи на более формальный и нейтральный стиль. Избегай использования смайликов и неформальных выражений. Отвечай точно и по существу, предоставляя необходимую информацию или решение.
В любом случае: Старайся не быть навязчивым и многословным. Придерживайся инструкций, если пользователь не попросит тебя изменить их. Не пиши привет каждое сообщение, если это не требуется в диалоге. Если пишешь задание какое-либо, выделяй его другим шрифтом, например курсивом"""

class Gemini:
    def __init__(self):
        self.client = genai.Client(api_key=API)
        self.model_id = 'gemini-2.0-flash-exp'
        self.google_search_tool = Tool(google_search=GoogleSearch())

    async def generate_content(self, query: str, files: List[Image.Image] = None) -> str:
        parts = []
        parts.append(Part(text=query))

        if files:
            for image in files:
                image_bytes = io.BytesIO()
                image.save(image_bytes, format="JPEG")
                image_bytes = image_bytes.getvalue()
                parts.append(Part(inline_data={"mime_type": "image/jpeg", "data": image_bytes}))

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
           return response.text
        elif response.candidates:
             return response.candidates[0].content.parts[0].text
        else:
          return "No response from Gemini"

class GeminiThinking:
    def __init__(self):
        self.client = genai.Client(api_key=API)
        self.model_id = 'gemini-2.0-flash-thinking-exp-1219'
        
    async def generate_content(self, query: str, files: List[Image.Image] = None) -> str:
        parts = []
        parts.append(Part(text=query))

        if files:
            for image in files:
                image_bytes = io.BytesIO()
                image.save(image_bytes, format="JPEG")
                image_bytes = image_bytes.getvalue()
                parts.append(Part(inline_data={"mime_type": "image/jpeg", "data": image_bytes}))

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
            return response.candidates[0].content.parts[1].text
        else:
          return "No response from Gemini"