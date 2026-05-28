# Herramientas específicas de Gema&Toni - Fotografía emocional
import os
import yaml
import logging
from datetime import datetime

logger = logging.getLogger("agentkit")


def cargar_info_negocio() -> dict:
    try:
        with open("config/business.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config/business.yaml no encontrado")
        return {}


def obtener_horario() -> dict:
    info = cargar_info_negocio()
    return {
        "horario": info.get("negocio", {}).get("horario", "Lunes a Viernes de 9:30 a 18:00"),
        "claudia_disponible": "24 horas",
    }


def obtener_tipos_sesion() -> list[dict]:
    info = cargar_info_negocio()
    return info.get("sesiones", [])


def buscar_en_knowledge(consulta: str) -> str:
    """Busca información relevante en los archivos de /knowledge."""
    resultados = []
    knowledge_dir = "knowledge"

    if not os.path.exists(knowledge_dir):
        return "No hay archivos de conocimiento disponibles."

    for archivo in os.listdir(knowledge_dir):
        ruta = os.path.join(knowledge_dir, archivo)
        if archivo.startswith(".") or not os.path.isfile(ruta):
            continue
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
                if consulta.lower() in contenido.lower():
                    resultados.append(f"[{archivo}]: {contenido[:500]}")
        except (UnicodeDecodeError, IOError):
            continue

    if resultados:
        return "\n---\n".join(resultados)
    return "No encontré información específica sobre eso en mis archivos."


def registrar_consulta_catalogo(telefono: str, tipo_sesion: str) -> str:
    """
    Registra que un cliente quiere el catálogo de una sesión concreta.
    Retorna un mensaje para notificar a Gema y Toni.
    """
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    return f"[{timestamp}] Cliente {telefono} solicitó catálogo de: {tipo_sesion}"
