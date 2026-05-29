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


async def generar_respuesta(mensaje: str, historial: list[dict]) -> str:
    """Genera una respuesta usando Claude API."""
    if not mensaje or mensaje == "__audio_no_transcrito__":
        if mensaje == "__audio_no_transcrito__":
            return "¡Hola! He recibido tu nota de voz pero no he podido escucharla bien. ¿Me escribes lo que necesitas? 😊"
        return obtener_mensaje_fallback()

    if len(mensaje.strip()) < 2:
        return obtener_mensaje_fallback()

    system_prompt = cargar_system_prompt()
    mensajes = [{"role": m["role"], "content": m["content"]} for m in historial]
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
        return obtener_mensaje_error()
