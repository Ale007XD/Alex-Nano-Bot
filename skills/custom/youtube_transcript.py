"""
Скилл: получение транскрипта YouTube-видео
Использование: отправь боту ссылку на YouTube-видео
"""
import re
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

def extract_video_id(url: str) -> str | None:
    patterns = [
        r'(?:v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})',
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None

async def run(context: dict) -> str:
    text = context.get("message_text", "")
    video_id = extract_video_id(text)

    if not video_id:
        return "Не найден ID видео. Отправь ссылку вида https://youtu.be/xxx или https://youtube.com/watch?v=xxx"

    try:
        api = YouTubeTranscriptApi()
        # Пробуем русский, потом английский
        try:
            snippets = api.fetch(video_id, languages=['ru'])
        except Exception:
            snippets = api.fetch(video_id, languages=['en'])

        clean = ' '.join(s.text.strip() for s in snippets)

        # Обрезаем если слишком длинно
        if len(clean) > 3000:
            clean = clean[:3000] + '...\n[транскрипт обрезан]'

        return f"📄 Транскрипт [{video_id}]:\n\n{clean}"

    except TranscriptsDisabled:
        return "❌ Субтитры отключены для этого видео."
    except NoTranscriptFound:
        return "❌ Транскрипт не найден (нет субтитров на ru/en)."
    except Exception as e:
        return f"❌ Ошибка: {e}"
