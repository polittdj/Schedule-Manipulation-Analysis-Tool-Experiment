"""Internationalisation (i18n) — multi-language UI + AI output (ADR-0099, extended ADR-0102).

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

Catalog terms live in :data:`_TERMS` as ``english source → {lang: translation}`` so every language
stays aligned to one key set; :data:`CATALOG` is derived per language. Adding a language = adding
its column to each term (and its endonym to :data:`LANGUAGES`).
"""

from __future__ import annotations

#: Supported languages: code → endonym (shown in the selector).
LANGUAGES: dict[str, str] = {
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
}

DEFAULT_LANGUAGE = "en"

#: English source term → per-language translation. Keyed on the exact rendered text (trimmed).
_TERMS: dict[str, dict[str, str]] = {
    # — navigation —
    "Dashboard": {"es": "Panel", "fr": "Tableau de bord", "de": "Übersicht"},
    "Diagnostic Brief": {
        "es": "Informe diagnóstico",
        "fr": "Bilan diagnostique",
        "de": "Diagnosebericht",
    },
    "Path Analysis": {"es": "Análisis de ruta", "fr": "Analyse de chemin", "de": "Pfadanalyse"},
    "Trend": {"es": "Tendencia", "fr": "Tendance", "de": "Trend"},
    "Bow Wave / CEI": {
        "es": "Ola de proa / CEI",
        "fr": "Vague d'étrave / CEI",
        "de": "Bugwelle / CEI",
    },
    "Finish & Slippage": {"es": "Fin y desviación", "fr": "Fin et dérive", "de": "Ende & Verzug"},
    "Finish &amp; Slippage": {
        "es": "Fin y desviación",
        "fr": "Fin et dérive",
        "de": "Ende & Verzug",
    },
    "S-Curve": {"es": "Curva S", "fr": "Courbe en S", "de": "S-Kurve"},
    "Quality Ribbon": {"es": "Cinta de calidad", "fr": "Ruban qualité", "de": "Qualitätsband"},
    "Critical-Path Evolution": {
        "es": "Evolución de la ruta crítica",
        "fr": "Évolution du chemin critique",
        "de": "Entwicklung des kritischen Pfads",
    },
    "Driving Path": {
        "es": "Ruta determinante",
        "fr": "Chemin déterminant",
        "de": "Treibender Pfad",
    },
    "Groups & Filters": {
        "es": "Grupos y filtros",
        "fr": "Groupes et filtres",
        "de": "Gruppen & Filter",
    },
    "Groups &amp; Filters": {
        "es": "Grupos y filtros",
        "fr": "Groupes et filtres",
        "de": "Gruppen & Filter",
    },
    "Forecast": {"es": "Pronóstico", "fr": "Prévision", "de": "Prognose"},
    "Executive Briefing": {
        "es": "Resumen ejecutivo",
        "fr": "Synthèse exécutive",
        "de": "Management-Briefing",
    },
    "AI Settings": {"es": "Ajustes de IA", "fr": "Paramètres IA", "de": "KI-Einstellungen"},
    "Metric Dictionary": {
        "es": "Diccionario de métricas",
        "fr": "Dictionnaire des métriques",
        "de": "Metrik-Wörterbuch",
    },
    "Wipe Session": {"es": "Borrar sesión", "fr": "Effacer la session", "de": "Sitzung löschen"},
    "Quit": {"es": "Salir", "fr": "Quitter", "de": "Beenden"},
    "Theme": {"es": "Tema", "fr": "Thème", "de": "Design"},
    "Language": {"es": "Idioma", "fr": "Langue", "de": "Sprache"},
    "Set": {"es": "Fijar", "fr": "Définir", "de": "Setzen"},
    "Target UID": {"es": "UID objetivo", "fr": "UID cible", "de": "Ziel-UID"},
    # — common buttons / controls —
    "Apply": {"es": "Aplicar", "fr": "Appliquer", "de": "Anwenden"},
    "clear": {"es": "limpiar", "fr": "effacer", "de": "löschen"},
    "Clear": {"es": "Limpiar", "fr": "Effacer", "de": "Löschen"},
    "Trace": {"es": "Trazar", "fr": "Tracer", "de": "Verfolgen"},
    "Focus": {"es": "Enfocar", "fr": "Cibler", "de": "Fokus"},
    "Prev": {"es": "Anterior", "fr": "Précédent", "de": "Zurück"},
    "Next": {"es": "Siguiente", "fr": "Suivant", "de": "Weiter"},
    "Auto-play": {"es": "Reproducir", "fr": "Lecture auto", "de": "Autoplay"},
    "Pause": {"es": "Pausar", "fr": "Pause", "de": "Pause"},
    "Zoom": {"es": "Zoom", "fr": "Zoom", "de": "Zoom"},
    "Columns:": {"es": "Columnas:", "fr": "Colonnes :", "de": "Spalten:"},
    "search…": {"es": "buscar…", "fr": "rechercher…", "de": "suchen…"},
    "All": {"es": "Todos", "fr": "Tout", "de": "Alle"},
    "None": {"es": "Ninguno", "fr": "Aucun", "de": "Keine"},
    "Load example": {"es": "Cargar ejemplo", "fr": "Charger l'exemple", "de": "Beispiel laden"},
    "Ask": {"es": "Preguntar", "fr": "Demander", "de": "Fragen"},
    "Export": {"es": "Exportar", "fr": "Exporter", "de": "Exportieren"},
    "Settings": {"es": "Ajustes", "fr": "Paramètres", "de": "Einstellungen"},
    "Help": {"es": "Ayuda", "fr": "Aide", "de": "Hilfe"},
    "Filter": {"es": "Filtro", "fr": "Filtre", "de": "Filter"},
    # — frequent labels / headings —
    "Schedule health": {
        "es": "Salud del cronograma",
        "fr": "Santé du planning",
        "de": "Terminplan-Zustand",
    },
    "Scope": {"es": "Alcance", "fr": "Périmètre", "de": "Umfang"},
    "Version": {"es": "Versión", "fr": "Version", "de": "Version"},
    "Versions": {"es": "Versiones", "fr": "Versions", "de": "Versionen"},
    "Activities": {"es": "Actividades", "fr": "Activités", "de": "Vorgänge"},
    "Activity": {"es": "Actividad", "fr": "Activité", "de": "Vorgang"},
    "Name": {"es": "Nombre", "fr": "Nom", "de": "Name"},
    "Start": {"es": "Inicio", "fr": "Début", "de": "Start"},
    "Finish": {"es": "Fin", "fr": "Fin", "de": "Ende"},
    "Status": {"es": "Estado", "fr": "Statut", "de": "Status"},
    "Status Date": {"es": "Fecha de estado", "fr": "Date d'état", "de": "Statusdatum"},
    "Data date": {"es": "Fecha de datos", "fr": "Date des données", "de": "Datenstichtag"},
    "Duration": {"es": "Duración", "fr": "Durée", "de": "Dauer"},
    "Resources": {"es": "Recursos", "fr": "Ressources", "de": "Ressourcen"},
    "Resource": {"es": "Recurso", "fr": "Ressource", "de": "Ressource"},
    "Critical": {"es": "Crítico", "fr": "Critique", "de": "Kritisch"},
    "Milestone": {"es": "Hito", "fr": "Jalon", "de": "Meilenstein"},
    "Milestones": {"es": "Hitos", "fr": "Jalons", "de": "Meilensteine"},
    "Summary": {"es": "Resumen", "fr": "Récapitulatif", "de": "Sammelvorgang"},
    "Normal": {"es": "Normal", "fr": "Normal", "de": "Normal"},
    "Complete": {"es": "Completado", "fr": "Terminé", "de": "Abgeschlossen"},
    "Completed": {"es": "Completado", "fr": "Terminé", "de": "Abgeschlossen"},
    "In progress": {"es": "En progreso", "fr": "En cours", "de": "In Arbeit"},
    "In Progress": {"es": "En progreso", "fr": "En cours", "de": "In Arbeit"},
    "Planned": {"es": "Planificado", "fr": "Planifié", "de": "Geplant"},
    "Not Started": {"es": "No iniciado", "fr": "Non commencé", "de": "Nicht begonnen"},
    "% complete": {"es": "% completado", "fr": "% achevé", "de": "% fertig"},
    "% Complete": {"es": "% completado", "fr": "% achevé", "de": "% fertig"},
    "Tier": {"es": "Nivel", "fr": "Niveau", "de": "Stufe"},
    "WBS": {"es": "EDT", "fr": "OTP", "de": "PSP"},
    "Constraint Type": {
        "es": "Tipo de restricción",
        "fr": "Type de contrainte",
        "de": "Einschränkungstyp",
    },
    "Activity Type": {"es": "Tipo de actividad", "fr": "Type d'activité", "de": "Vorgangstyp"},
    "Value": {"es": "Valor", "fr": "Valeur", "de": "Wert"},
    "Check": {"es": "Comprobación", "fr": "Contrôle", "de": "Prüfung"},
    "Total float": {"es": "Holgura total", "fr": "Marge totale", "de": "Gesamtpuffer"},
    "Free float": {"es": "Holgura libre", "fr": "Marge libre", "de": "Freier Puffer"},
    "Project finish": {"es": "Fin del proyecto", "fr": "Fin du projet", "de": "Projektende"},
    "Computed finish": {"es": "Fin calculado", "fr": "Fin calculée", "de": "Berechnetes Ende"},
    "Earliest start": {
        "es": "Inicio más temprano",
        "fr": "Début au plus tôt",
        "de": "Frühester Start",
    },
    "Metric scorecard for this scope": {
        "es": "Tarjeta de métricas para este alcance",
        "fr": "Tableau des métriques pour ce périmètre",
        "de": "Kennzahlen-Übersicht für diesen Umfang",
    },
    "Break down by:": {"es": "Desglosar por:", "fr": "Ventiler par :", "de": "Aufschlüsseln nach:"},
    "Corridor over time": {
        "es": "Corredor a lo largo del tiempo",
        "fr": "Couloir au fil du temps",
        "de": "Korridor im Zeitverlauf",
    },
    "no logic route A → B": {
        "es": "sin ruta lógica A → B",
        "fr": "aucun chemin logique A → B",
        "de": "keine Logikverbindung A → B",
    },
    # — statuses / verdicts —
    "PASS": {"es": "APROBADO", "fr": "RÉUSSI", "de": "BESTANDEN"},  # nosec B105  # verdict, not a secret
    "FAIL": {"es": "FALLA", "fr": "ÉCHEC", "de": "FEHLER"},
    "NA": {"es": "N/D", "fr": "N/D", "de": "N/V"},
    "Yes": {"es": "Sí", "fr": "Oui", "de": "Ja"},
    "No": {"es": "No", "fr": "Non", "de": "Nein"},
    # — empty / prompt states —
    "Load a schedule to scope the metrics by a field value.": {
        "es": "Cargue un cronograma para acotar las métricas por el valor de un campo.",
        "fr": "Chargez un planning pour restreindre les métriques par la valeur d'un champ.",
        "de": "Laden Sie einen Terminplan, um die Kennzahlen nach einem Feldwert einzugrenzen.",
    },
    "Load a schedule to trace the driving path between two activities.": {
        "es": "Cargue un cronograma para trazar la ruta determinante entre dos actividades.",
        "fr": "Chargez un planning pour tracer le chemin déterminant entre deux activités.",
        "de": "Laden Sie einen Terminplan, um den treibenden Pfad zwischen zwei Vorgängen zu "
        "verfolgen.",
    },
    "Load at least two analyzable versions to watch the critical path evolve.": {
        "es": "Cargue al menos dos versiones analizables para ver evolucionar la ruta crítica.",
        "fr": "Chargez au moins deux versions analysables pour voir évoluer le chemin critique.",
        "de": "Laden Sie mindestens zwei auswertbare Versionen, um die Entwicklung des kritischen "
        "Pfads zu sehen.",
    },
}

#: Per-language catalog: language code → {english source: translation}, derived from :data:`_TERMS`.
CATALOG: dict[str, dict[str, str]] = {
    lang: {src: tr[lang] for src, tr in _TERMS.items() if lang in tr}
    for lang in LANGUAGES
    if lang != DEFAULT_LANGUAGE
}


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
