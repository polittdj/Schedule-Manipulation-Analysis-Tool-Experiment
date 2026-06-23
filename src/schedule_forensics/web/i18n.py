"""Internationalisation (i18n) — multi-language UI + AI output (ADR-0099, extended ADR-0102).

Two layers, so a language switch covers *everything* shown:

* a hand-built **catalog** of the app's own fixed terms (nav, page titles, buttons, metric names,
  statuses, common labels) — high-quality and offline, the source of truth for forensic vocabulary;
* an **AI fallback** (``/api/translate`` in :mod:`schedule_forensics.web.app`) for everything the
  catalog does not cover — imported task/WBS/resource names and computed/AI prose — translated by
  the configured local model and cached, falling back to the source text when no model is reachable.

The client (``static/translate.js``) walks the rendered DOM's text nodes AND a fixed set of
attributes (placeholder/title/aria-label/alt) and ``<option>`` labels, applies catalog hits
instantly, and sends text-node misses to the AI fallback — so server-rendered pages, AJAX-loaded
grids, and AI answers are all covered by one mechanism. English is the source language, so a missing
entry simply shows the original text (never a broken UI), and translation is non-destructive (the
original English is remembered per node) so the user can switch languages back and forth freely.

Catalog terms live in :data:`_TERMS` as ``english source → {lang: translation}`` so every language
stays aligned to one key set; :data:`CATALOG` is derived per language. Adding a language = adding
its column to each term (and its endonym to :data:`LANGUAGES`). Languages: EN/ES/FR/DE/PT.
"""

from __future__ import annotations

#: Supported languages: code → endonym (shown in the selector).
LANGUAGES: dict[str, str] = {
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "pt": "Português",
}

DEFAULT_LANGUAGE = "en"

#: English source term → per-language translation. Keyed on the exact rendered text (trimmed).
_TERMS: dict[str, dict[str, str]] = {
    # — navigation: group labels —
    "Overview": {"es": "Resumen general", "fr": "Aperçu", "de": "Überblick", "pt": "Visão geral"},
    "Assessment": {"es": "Evaluación", "fr": "Évaluation", "de": "Bewertung", "pt": "Avaliação"},
    "Control": {"es": "Control", "fr": "Contrôle", "de": "Steuerung", "pt": "Controlo"},
    "Risks": {"es": "Riesgos", "fr": "Risques", "de": "Risiken", "pt": "Riscos"},
    "Reporting": {"es": "Informes", "fr": "Rapports", "de": "Berichte", "pt": "Relatórios"},
    "Setup": {
        "es": "Configuración",
        "fr": "Configuration",
        "de": "Einrichtung",
        "pt": "Configuração",
    },
    # — navigation: links —
    "Dashboard": {"es": "Panel", "fr": "Tableau de bord", "de": "Übersicht", "pt": "Painel"},
    "Mission Control": {
        "es": "Centro de control",
        "fr": "Centre de contrôle",
        "de": "Leitstand",
        "pt": "Centro de controlo",
    },
    "Diagnostic Brief": {
        "es": "Informe diagnóstico",
        "fr": "Bilan diagnostique",
        "de": "Diagnosebericht",
        "pt": "Resumo diagnóstico",
    },
    "Path Analysis": {
        "es": "Análisis de ruta",
        "fr": "Analyse de chemin",
        "de": "Pfadanalyse",
        "pt": "Análise de caminho",
    },
    "Trend": {"es": "Tendencia", "fr": "Tendance", "de": "Trend", "pt": "Tendência"},
    "Bow Wave / CEI": {
        "es": "Ola de proa / CEI",
        "fr": "Vague d'étrave / CEI",
        "de": "Bugwelle / CEI",
        "pt": "Onda de proa / CEI",
    },
    "Finish & Slippage": {
        "es": "Fin y desviación",
        "fr": "Fin et dérive",
        "de": "Ende & Verzug",
        "pt": "Fim e atraso",
    },
    "Finish &amp; Slippage": {
        "es": "Fin y desviación",
        "fr": "Fin et dérive",
        "de": "Ende & Verzug",
        "pt": "Fim e atraso",
    },
    "S-Curve": {"es": "Curva S", "fr": "Courbe en S", "de": "S-Kurve", "pt": "Curva S"},
    "Year Phases": {
        "es": "Fases anuales",
        "fr": "Phases annuelles",
        "de": "Jahresphasen",
        "pt": "Fases anuais",
    },
    "Quality Ribbon": {
        "es": "Cinta de calidad",
        "fr": "Ruban qualité",
        "de": "Qualitätsband",
        "pt": "Faixa de qualidade",
    },
    "Critical-Path Evolution": {
        "es": "Evolución de la ruta crítica",
        "fr": "Évolution du chemin critique",
        "de": "Entwicklung des kritischen Pfads",
        "pt": "Evolução do caminho crítico",
    },
    "Driving Path": {
        "es": "Ruta determinante",
        "fr": "Chemin déterminant",
        "de": "Treibender Pfad",
        "pt": "Caminho determinante",
    },
    "Risks & Opportunities": {
        "es": "Riesgos y oportunidades",
        "fr": "Risques et opportunités",
        "de": "Risiken & Chancen",
        "pt": "Riscos e oportunidades",
    },
    "Risks &amp; Opportunities": {
        "es": "Riesgos y oportunidades",
        "fr": "Risques et opportunités",
        "de": "Risiken & Chancen",
        "pt": "Riscos e oportunidades",
    },
    "Risk Analysis": {
        "es": "Análisis de riesgos",
        "fr": "Analyse des risques",
        "de": "Risikoanalyse",
        "pt": "Análise de riscos",
    },
    "Groups & Filters": {
        "es": "Grupos y filtros",
        "fr": "Groupes et filtres",
        "de": "Gruppen & Filter",
        "pt": "Grupos e filtros",
    },
    "Groups &amp; Filters": {
        "es": "Grupos y filtros",
        "fr": "Groupes et filtres",
        "de": "Gruppen & Filter",
        "pt": "Grupos e filtros",
    },
    "Forecast": {"es": "Pronóstico", "fr": "Prévision", "de": "Prognose", "pt": "Previsão"},
    "Executive Briefing": {
        "es": "Resumen ejecutivo",
        "fr": "Synthèse exécutive",
        "de": "Management-Briefing",
        "pt": "Resumo executivo",
    },
    "AI Settings": {
        "es": "Ajustes de IA",
        "fr": "Paramètres IA",
        "de": "KI-Einstellungen",
        "pt": "Definições de IA",
    },
    "Metric Dictionary": {
        "es": "Diccionario de métricas",
        "fr": "Dictionnaire des métriques",
        "de": "Metrik-Wörterbuch",
        "pt": "Dicionário de métricas",
    },
    "manage": {"es": "gestionar", "fr": "gérer", "de": "verwalten", "pt": "gerir"},
    "clear filter": {
        "es": "limpiar filtro",
        "fr": "effacer le filtre",
        "de": "Filter löschen",
        "pt": "limpar filtro",
    },
    "Open report": {
        "es": "Abrir informe",
        "fr": "Ouvrir le rapport",
        "de": "Bericht öffnen",
        "pt": "Abrir relatório",
    },
    "Card": {"es": "Ficha", "fr": "Fiche", "de": "Karte", "pt": "Cartão"},
    "Save .json": {
        "es": "Guardar .json",
        "fr": "Enregistrer .json",
        "de": ".json speichern",
        "pt": "Guardar .json",
    },
    "Wipe Session": {
        "es": "Borrar sesión",
        "fr": "Effacer la session",
        "de": "Sitzung löschen",
        "pt": "Limpar sessão",
    },
    "Quit": {"es": "Salir", "fr": "Quitter", "de": "Beenden", "pt": "Sair"},
    "Theme": {"es": "Tema", "fr": "Thème", "de": "Design", "pt": "Tema"},
    "Language": {"es": "Idioma", "fr": "Langue", "de": "Sprache", "pt": "Idioma"},
    "Set": {"es": "Fijar", "fr": "Définir", "de": "Setzen", "pt": "Definir"},
    "Target UID": {"es": "UID objetivo", "fr": "UID cible", "de": "Ziel-UID", "pt": "UID alvo"},
    # — common buttons / controls —
    "Apply": {"es": "Aplicar", "fr": "Appliquer", "de": "Anwenden", "pt": "Aplicar"},
    "clear": {"es": "limpiar", "fr": "effacer", "de": "löschen", "pt": "limpar"},
    "Clear": {"es": "Limpiar", "fr": "Effacer", "de": "Löschen", "pt": "Limpar"},
    "Trace": {"es": "Trazar", "fr": "Tracer", "de": "Verfolgen", "pt": "Traçar"},
    "Focus": {"es": "Enfocar", "fr": "Cibler", "de": "Fokus", "pt": "Focar"},
    "Prev": {"es": "Anterior", "fr": "Précédent", "de": "Zurück", "pt": "Anterior"},
    "Next": {"es": "Siguiente", "fr": "Suivant", "de": "Weiter", "pt": "Seguinte"},
    "Auto-play": {
        "es": "Reproducir",
        "fr": "Lecture auto",
        "de": "Autoplay",
        "pt": "Reprodução auto",
    },
    "Pause": {"es": "Pausar", "fr": "Pause", "de": "Pause", "pt": "Pausar"},
    "Zoom": {"es": "Zoom", "fr": "Zoom", "de": "Zoom", "pt": "Zoom"},
    "Columns:": {"es": "Columnas:", "fr": "Colonnes :", "de": "Spalten:", "pt": "Colunas:"},
    "search…": {"es": "buscar…", "fr": "rechercher…", "de": "suchen…", "pt": "procurar…"},
    "All": {"es": "Todos", "fr": "Tout", "de": "Alle", "pt": "Todos"},
    "None": {"es": "Ninguno", "fr": "Aucun", "de": "Keine", "pt": "Nenhum"},
    "Load example": {
        "es": "Cargar ejemplo",
        "fr": "Charger l'exemple",
        "de": "Beispiel laden",
        "pt": "Carregar exemplo",
    },
    "Ask": {"es": "Preguntar", "fr": "Demander", "de": "Fragen", "pt": "Perguntar"},
    "Ask the AI": {
        "es": "Preguntar a la IA",
        "fr": "Demander à l'IA",
        "de": "KI fragen",
        "pt": "Perguntar à IA",
    },
    "Run simulation": {
        "es": "Ejecutar simulación",
        "fr": "Lancer la simulation",
        "de": "Simulation starten",
        "pt": "Executar simulação",
    },
    "Iterations": {
        "es": "Iteraciones",
        "fr": "Itérations",
        "de": "Iterationen",
        "pt": "Iterações",
    },
    "Distribution": {
        "es": "Distribución",
        "fr": "Distribution",
        "de": "Verteilung",
        "pt": "Distribuição",
    },
    "Time scale": {
        "es": "Escala de tiempo",
        "fr": "Échelle de temps",
        "de": "Zeitskala",
        "pt": "Escala de tempo",
    },
    "Risk inputs": {
        "es": "Entradas de riesgo",
        "fr": "Paramètres de risque",
        "de": "Risikoeingaben",
        "pt": "Entradas de risco",
    },
    "Export": {"es": "Exportar", "fr": "Exporter", "de": "Exportieren", "pt": "Exportar"},
    "Settings": {"es": "Ajustes", "fr": "Paramètres", "de": "Einstellungen", "pt": "Definições"},
    "Help": {"es": "Ayuda", "fr": "Aide", "de": "Hilfe", "pt": "Ajuda"},
    "Filter": {"es": "Filtro", "fr": "Filtre", "de": "Filter", "pt": "Filtro"},
    # — frequent labels / headings —
    "Schedule health": {
        "es": "Salud del cronograma",
        "fr": "Santé du planning",
        "de": "Terminplan-Zustand",
        "pt": "Saúde do cronograma",
    },
    "Scope": {"es": "Alcance", "fr": "Périmètre", "de": "Umfang", "pt": "Âmbito"},
    "Version": {"es": "Versión", "fr": "Version", "de": "Version", "pt": "Versão"},
    "Versions": {"es": "Versiones", "fr": "Versions", "de": "Versionen", "pt": "Versões"},
    "Activities": {"es": "Actividades", "fr": "Activités", "de": "Vorgänge", "pt": "Atividades"},
    "Activity": {"es": "Actividad", "fr": "Activité", "de": "Vorgang", "pt": "Atividade"},
    "Name": {"es": "Nombre", "fr": "Nom", "de": "Name", "pt": "Nome"},
    "Start": {"es": "Inicio", "fr": "Début", "de": "Start", "pt": "Início"},
    "Finish": {"es": "Fin", "fr": "Fin", "de": "Ende", "pt": "Fim"},
    "Status": {"es": "Estado", "fr": "Statut", "de": "Status", "pt": "Estado"},
    "Status Date": {
        "es": "Fecha de estado",
        "fr": "Date d'état",
        "de": "Statusdatum",
        "pt": "Data de estado",
    },
    "Data date": {
        "es": "Fecha de datos",
        "fr": "Date des données",
        "de": "Datenstichtag",
        "pt": "Data dos dados",
    },
    "Duration": {"es": "Duración", "fr": "Durée", "de": "Dauer", "pt": "Duração"},
    "Resources": {"es": "Recursos", "fr": "Ressources", "de": "Ressourcen", "pt": "Recursos"},
    "Resource": {"es": "Recurso", "fr": "Ressource", "de": "Ressource", "pt": "Recurso"},
    "Critical": {"es": "Crítico", "fr": "Critique", "de": "Kritisch", "pt": "Crítico"},
    "Milestone": {"es": "Hito", "fr": "Jalon", "de": "Meilenstein", "pt": "Marco"},
    "Milestones": {"es": "Hitos", "fr": "Jalons", "de": "Meilensteine", "pt": "Marcos"},
    "Summary": {"es": "Resumen", "fr": "Récapitulatif", "de": "Sammelvorgang", "pt": "Resumo"},
    "Normal": {"es": "Normal", "fr": "Normal", "de": "Normal", "pt": "Normal"},
    "Complete": {"es": "Completado", "fr": "Terminé", "de": "Abgeschlossen", "pt": "Concluído"},
    "Completed": {"es": "Completado", "fr": "Terminé", "de": "Abgeschlossen", "pt": "Concluído"},
    "In progress": {"es": "En progreso", "fr": "En cours", "de": "In Arbeit", "pt": "Em curso"},
    "In Progress": {"es": "En progreso", "fr": "En cours", "de": "In Arbeit", "pt": "Em curso"},
    "Planned": {"es": "Planificado", "fr": "Planifié", "de": "Geplant", "pt": "Planeado"},
    "Not Started": {
        "es": "No iniciado",
        "fr": "Non commencé",
        "de": "Nicht begonnen",
        "pt": "Não iniciado",
    },
    "% complete": {"es": "% completado", "fr": "% achevé", "de": "% fertig", "pt": "% concluído"},
    "% Complete": {"es": "% completado", "fr": "% achevé", "de": "% fertig", "pt": "% concluído"},
    "Tier": {"es": "Nivel", "fr": "Niveau", "de": "Stufe", "pt": "Nível"},
    "WBS": {"es": "EDT", "fr": "OTP", "de": "PSP", "pt": "EAP"},
    "Constraint Type": {
        "es": "Tipo de restricción",
        "fr": "Type de contrainte",
        "de": "Einschränkungstyp",
        "pt": "Tipo de restrição",
    },
    "Activity Type": {
        "es": "Tipo de actividad",
        "fr": "Type d'activité",
        "de": "Vorgangstyp",
        "pt": "Tipo de atividade",
    },
    "Value": {"es": "Valor", "fr": "Valeur", "de": "Wert", "pt": "Valor"},
    "Check": {"es": "Comprobación", "fr": "Contrôle", "de": "Prüfung", "pt": "Verificação"},
    "Total float": {
        "es": "Holgura total",
        "fr": "Marge totale",
        "de": "Gesamtpuffer",
        "pt": "Folga total",
    },
    "Free float": {
        "es": "Holgura libre",
        "fr": "Marge libre",
        "de": "Freier Puffer",
        "pt": "Folga livre",
    },
    "Float Ratio": {
        "es": "Ratio de holgura",
        "fr": "Ratio de marge",
        "de": "Puffer-Verhältnis",
        "pt": "Rácio de folga",
    },
    "Project finish": {
        "es": "Fin del proyecto",
        "fr": "Fin du projet",
        "de": "Projektende",
        "pt": "Fim do projeto",
    },
    "Computed finish": {
        "es": "Fin calculado",
        "fr": "Fin calculée",
        "de": "Berechnetes Ende",
        "pt": "Fim calculado",
    },
    "Earliest start": {
        "es": "Inicio más temprano",
        "fr": "Début au plus tôt",
        "de": "Frühester Start",
        "pt": "Início mais cedo",
    },
    "Metric scorecard for this scope": {
        "es": "Tarjeta de métricas para este alcance",
        "fr": "Tableau des métriques pour ce périmètre",
        "de": "Kennzahlen-Übersicht für diesen Umfang",
        "pt": "Cartão de métricas para este âmbito",
    },
    "Break down by:": {
        "es": "Desglosar por:",
        "fr": "Ventiler par :",
        "de": "Aufschlüsseln nach:",
        "pt": "Desagregar por:",
    },
    "Corridor over time": {
        "es": "Corredor a lo largo del tiempo",
        "fr": "Couloir au fil du temps",
        "de": "Korridor im Zeitverlauf",
        "pt": "Corredor ao longo do tempo",
    },
    "no logic route A → B": {
        "es": "sin ruta lógica A → B",
        "fr": "aucun chemin logique A → B",
        "de": "keine Logikverbindung A → B",
        "pt": "sem rota lógica A → B",
    },
    # — statuses / verdicts —
    "PASS": {
        "es": "APROBADO",
        "fr": "RÉUSSI",
        "de": "BESTANDEN",
        "pt": "APROVADO",
    },  # nosec B105  # verdict, not a secret
    "FAIL": {"es": "FALLA", "fr": "ÉCHEC", "de": "FEHLER", "pt": "FALHA"},
    "NA": {"es": "N/D", "fr": "N/D", "de": "N/V", "pt": "N/D"},
    "Yes": {"es": "Sí", "fr": "Oui", "de": "Ja", "pt": "Sim"},
    "No": {"es": "No", "fr": "Non", "de": "Nein", "pt": "Não"},
    # — empty / prompt states —
    "Load a schedule to scope the metrics by a field value.": {
        "es": "Cargue un cronograma para acotar las métricas por el valor de un campo.",
        "fr": "Chargez un planning pour restreindre les métriques par la valeur d'un champ.",
        "de": "Laden Sie einen Terminplan, um die Kennzahlen nach einem Feldwert einzugrenzen.",
        "pt": "Carregue um cronograma para delimitar as métricas pelo valor de um campo.",
    },
    "Load a schedule to trace the driving path between two activities.": {
        "es": "Cargue un cronograma para trazar la ruta determinante entre dos actividades.",
        "fr": "Chargez un planning pour tracer le chemin déterminant entre deux activités.",
        "de": "Laden Sie einen Terminplan, um den treibenden Pfad zwischen zwei Vorgängen zu "
        "verfolgen.",
        "pt": "Carregue um cronograma para traçar o caminho determinante entre duas atividades.",
    },
    "Load at least two analyzable versions to watch the critical path evolve.": {
        "es": "Cargue al menos dos versiones analizables para ver evolucionar la ruta crítica.",
        "fr": "Chargez au moins deux versions analysables pour voir évoluer le chemin critique.",
        "de": "Laden Sie mindestens zwei auswertbare Versionen, um die Entwicklung des kritischen "
        "Pfads zu sehen.",
        "pt": "Carregue pelo menos duas versões analisáveis para ver o caminho crítico evoluir.",
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
