"""Internationalisation (i18n) — English ⇄ Spanish for the whole UI and the AI output (ADR-0099).

Two layers, so a language switch covers *everything* shown:

* a hand-built **catalog** of the app's own fixed terms (nav, page titles, buttons, metric names,
  statuses, common labels) — high-quality and offline, the source of truth for forensic vocabulary;
* an **AI fallback** (``/api/translate`` in :mod:`schedule_forensics.web.app`) for everything the
  catalog does not cover — imported task/WBS/resource names and computed/AI prose — translated by
  the configured local model and cached, falling back to the source text when no model is reachable.

The client (``static/translate.js``) walks the rendered DOM's text nodes, applies catalog hits
instantly, and sends the misses to the AI fallback — so server-rendered pages, AJAX-loaded grids,
and AI answers are all covered by one mechanism. English is the source language, so a missing entry
simply shows the original text (never a broken UI).
"""

from __future__ import annotations

#: Supported languages: code → endonym (shown in the selector).
LANGUAGES: dict[str, str] = {"en": "English", "es": "Español"}

DEFAULT_LANGUAGE = "en"

#: English source term → Spanish. Keyed on the exact rendered text (trimmed). Covers the app's own
#: fixed vocabulary; dynamic content (task names, AI prose) goes through the AI fallback.
_ES: dict[str, str] = {
    # — navigation —
    "Dashboard": "Panel",
    "Diagnostic Brief": "Informe diagnóstico",
    "Path Analysis": "Análisis de ruta",
    "Trend": "Tendencia",
    "Bow Wave / CEI": "Ola de proa / CEI",
    "Finish & Slippage": "Fin y desviación",
    "Finish &amp; Slippage": "Fin y desviación",
    "S-Curve": "Curva S",
    "Quality Ribbon": "Cinta de calidad",
    "Critical-Path Evolution": "Evolución de la ruta crítica",
    "Driving Path": "Ruta determinante",
    "Groups & Filters": "Grupos y filtros",
    "Groups &amp; Filters": "Grupos y filtros",
    "Forecast": "Pronóstico",
    "Executive Briefing": "Resumen ejecutivo",
    "AI Settings": "Ajustes de IA",
    "Metric Dictionary": "Diccionario de métricas",
    "Wipe Session": "Borrar sesión",
    "Quit": "Salir",
    "Theme": "Tema",
    "Language": "Idioma",
    "Set": "Fijar",
    "Target UID": "UID objetivo",
    # — common buttons / controls —
    "Apply": "Aplicar",
    "clear": "limpiar",
    "Clear": "Limpiar",
    "Trace": "Trazar",
    "Focus": "Enfocar",
    "Prev": "Anterior",
    "Next": "Siguiente",
    "Auto-play": "Reproducir",
    "Pause": "Pausar",
    "Zoom": "Zoom",
    "Columns:": "Columnas:",
    "search…": "buscar…",
    "All": "Todos",
    "None": "Ninguno",
    "Load example": "Cargar ejemplo",
    "Ask": "Preguntar",
    # — frequent labels / headings —
    "Schedule health": "Salud del cronograma",
    "Scope": "Alcance",
    "Version": "Versión",
    "Versions": "Versiones",
    "Activities": "Actividades",
    "Activity": "Actividad",
    "Name": "Nombre",
    "Start": "Inicio",
    "Finish": "Fin",
    "Status": "Estado",
    "Status Date": "Fecha de estado",
    "Data date": "Fecha de datos",
    "Duration": "Duración",
    "Resources": "Recursos",
    "Resource": "Recurso",
    "Critical": "Crítico",
    "Milestone": "Hito",
    "Milestones": "Hitos",
    "Summary": "Resumen",
    "Normal": "Normal",
    "Complete": "Completado",
    "Completed": "Completado",
    "In progress": "En progreso",
    "In Progress": "En progreso",
    "Planned": "Planificado",
    "Not Started": "No iniciado",
    "% complete": "% completado",
    "% Complete": "% completado",
    "Tier": "Nivel",
    "WBS": "EDT",
    "Constraint Type": "Tipo de restricción",
    "Activity Type": "Tipo de actividad",
    "Value": "Valor",
    "Check": "Comprobación",
    "Computed finish": "Fin calculado",
    "Earliest start": "Inicio más temprano",
    "Metric scorecard for this scope": "Tarjeta de métricas para este alcance",
    "Break down by:": "Desglosar por:",
    "Corridor over time": "Corredor a lo largo del tiempo",
    "no logic route A → B": "sin ruta lógica A → B",
    # — statuses / verdicts —
    "PASS": "APROBADO",
    "FAIL": "FALLA",
    "NA": "N/D",
    "Yes": "Sí",
    "No": "No",
    # — empty / prompt states —
    "Load a schedule to scope the metrics by a field value.": (
        "Cargue un cronograma para acotar las métricas por el valor de un campo."
    ),
    "Load a schedule to trace the driving path between two activities.": (
        "Cargue un cronograma para trazar la ruta determinante entre dos actividades."
    ),
    "Load at least two analyzable versions to watch the critical path evolve.": (
        "Cargue al menos dos versiones analizables para ver evolucionar la ruta crítica."
    ),
}

#: Per-language catalog: language code → {english source: translation}.
CATALOG: dict[str, dict[str, str]] = {"es": _ES}


def normalize(lang: str | None) -> str:
    """A supported language code, defaulting to English for anything unknown/blank."""
    return lang if lang in LANGUAGES else DEFAULT_LANGUAGE


def catalog_for(lang: str) -> dict[str, str]:
    """The fixed-term catalog for ``lang`` (empty for English / unknown)."""
    return CATALOG.get(normalize(lang), {})


def translate(text: str, lang: str) -> str:
    """A catalog translation of ``text`` for ``lang``, else the source text (graceful fallback)."""
    if normalize(lang) == DEFAULT_LANGUAGE:
        return text
    return CATALOG.get(lang, {}).get(text.strip(), text)
