# Cerebro del agente: conexión con Claude API
import os
import yaml
import logging
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("agentkit")

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def cargar_config_prompts() -> dict:
    """Lee la configuración desde config/prompts.yaml."""
    try:
        with open("config/prompts.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.error("config/prompts.yaml no encontrado")
        return {}


def cargar_system_prompt() -> str:
    config = cargar_config_prompts()
    return config.get("system_prompt", "Eres un asistente útil. Responde en español.")


def obtener_mensaje_error() -> str:
    config = cargar_config_prompts()
    return config.get("error_message", "Lo siento, estoy teniendo problemas técnicos. Por favor intenta de nuevo en unos minutos.")


def obtener_mensaje_fallback() -> str:
    config = cargar_config_prompts()
    return config.get("fallback_message", "Perdona, no he entendido bien tu mensaje. ¿Me lo puedes contar de otra manera?")


async def generar_respuesta(
    mensaje: str,
    historial: list[dict],
    audio_base64: str | None = None,
    audio_media_type: str | None = None,
) -> str:
    """Genera una respuesta usando Claude API. Soporta texto y audio."""
    if not mensaje and not audio_base64:
        return obtener_mensaje_fallback()

    system_prompt = cargar_system_prompt()
    mensajes = [{"role": m["role"], "content": m["content"]} for m in historial]

    if audio_base64 and audio_media_type:
        # Mensaje con audio — Claude lo escucha y responde
        contenido_usuario: list = [
            {
                "type": "text",
                "text": "El cliente ha enviado un mensaje de voz. Escúchalo y responde como Claudia, en español, de forma natural y cercana."
            },
            {
                "type": "audio",
                "source": {
                    "type": "base64",
                    "media_type": audio_media_type,
                    "data": audio_base64,
                }
            }
        ]
        if mensaje:
            contenido_usuario.insert(0, {"type": "text", "text": mensaje})
        mensajes.append({"role": "user", "content": contenido_usuario})
    else:
        if len(mensaje.strip()) < 2:
            return obtener_mensaje_fallback()
        mensajes.append({"role": "user", "content": mensaje})

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            messages=mensajes
        )
        respuesta = response.content[0].text
        logger.info(f"Respuesta generada ({response.usage.input_tokens} in / {response.usage.output_tokens} out)")
        return respuesta
    except Exception as e:
        logger.error(f"Error Claude API: {e}")
        if audio_base64:
            return "¡Hola! He recibido tu nota de voz pero tengo un pequeño problema para escucharla ahora mismo. ¿Me puedes escribir lo que necesitas? 😊"
        return obtener_mensaje_error()
