# Adaptador para Twilio WhatsApp
import os
import logging
import base64
import httpx
from fastapi import Request
from agent.providers.base import ProveedorWhatsApp, MensajeEntrante

logger = logging.getLogger("agentkit")


class ProveedorTwilio(ProveedorWhatsApp):
    """Proveedor de WhatsApp usando Twilio."""

    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.phone_number = os.getenv("TWILIO_PHONE_NUMBER")

    async def parsear_webhook(self, request: Request) -> list[MensajeEntrante]:
        """Parsea el payload form-encoded de Twilio, incluyendo mensajes de audio."""
        form = await request.form()
        texto = form.get("Body", "")
        telefono = form.get("From", "").replace("whatsapp:", "")
        mensaje_id = form.get("MessageSid", "")
        num_media = int(form.get("NumMedia", "0"))

        audio_base64 = None
        audio_media_type = None

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
                            timeout=15.0
                        )
                        if r.status_code == 200:
                            audio_base64 = base64.b64encode(r.content).decode()
                            audio_media_type = media_type
                            logger.info(f"Audio descargado: {media_type}, {len(r.content)} bytes")
                except Exception as e:
                    logger.error(f"Error descargando audio: {e}")

        if not texto and not audio_base64:
            return []

        return [MensajeEntrante(
            telefono=telefono,
            texto=texto or "",
            mensaje_id=mensaje_id,
            es_propio=False,
            audio_base64=audio_base64,
            audio_media_type=audio_media_type,
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
