# Adaptador para Twilio WhatsApp
import os
import io
import logging
import base64
import httpx
from fastapi import Request
from agent.providers.base import ProveedorWhatsApp, MensajeEntrante

logger = logging.getLogger("agentkit")


async def transcribir_audio(audio_bytes: bytes, media_type: str) -> str | None:
    """Transcribe audio usando OpenAI Whisper."""
    try:
        from openai import AsyncOpenAI
        openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Determinar extensión según el tipo de audio
        extension = "ogg"
        if "mpeg" in media_type or "mp3" in media_type:
            extension = "mp3"
        elif "mp4" in media_type or "m4a" in media_type:
            extension = "m4a"
        elif "wav" in media_type:
            extension = "wav"

        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = f"audio.{extension}"

        transcripcion = await openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="es",
        )
        texto = transcripcion.text.strip()
        logger.info(f"Transcripción Whisper: {texto}")
        return texto if texto else None
    except Exception as e:
        logger.error(f"Error Whisper: {e}")
        return None


class ProveedorTwilio(ProveedorWhatsApp):
    """Proveedor de WhatsApp usando Twilio."""

    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.phone_number = os.getenv("TWILIO_PHONE_NUMBER")

    async def parsear_webhook(self, request: Request) -> list[MensajeEntrante]:
        """Parsea el payload form-encoded de Twilio, transcribiendo audios con Whisper."""
        form = await request.form()
        texto = form.get("Body", "")
        telefono = form.get("From", "").replace("whatsapp:", "")
        mensaje_id = form.get("MessageSid", "")
        num_media = int(form.get("NumMedia", "0"))

        if num_media > 0:
            media_url = form.get("MediaUrl0", "")
            media_type = form.get("MediaContentType0", "")
            if media_url and media_type.startswith("audio/"):
                try:
                    auth = base64.b64encode(
                        f"{self.account_sid}:{self.auth_token}".encode()
                    ).decode()
                    async with httpx.AsyncClient() as client:
                        r = await client.get(
                            media_url,
                            headers={"Authorization": f"Basic {auth}"},
                            follow_redirects=True,
                            timeout=20.0
                        )
                        if r.status_code == 200:
                            logger.info(f"Audio descargado: {media_type}, {len(r.content)} bytes")
                            transcripcion = await transcribir_audio(r.content, media_type)
                            if transcripcion:
                                texto = transcripcion
                            else:
                                texto = "__audio_no_transcrito__"
                except Exception as e:
                    logger.error(f"Error procesando audio: {e}")
                    texto = "__audio_no_transcrito__"

        if not texto:
            return []

        return [MensajeEntrante(
            telefono=telefono,
            texto=texto,
            mensaje_id=mensaje_id,
            es_propio=False,
        )]

    async def enviar_mensaje(self, telefono: str, mensaje: str) -> bool:
        """Envía mensaje via Twilio API."""
        if not all([self.account_sid, self.auth_token, self.phone_number]):
            logger.warning("Variables de Twilio no configuradas")
            return False
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        auth = base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode()).decode()
        headers = {"Authorization": f"Basic {auth}"}
        data = {
            "From": f"whatsapp:{self.phone_number}",
            "To": f"whatsapp:{telefono}",
            "Body": mensaje,
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(url, data=data, headers=headers)
            if r.status_code != 201:
                logger.error(f"Error Twilio: {r.status_code} — {r.text}")
            return r.status_code == 201
