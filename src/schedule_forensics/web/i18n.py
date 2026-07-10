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
    # — HUD layer: explainers, guidance, compliance, telemetry (ADR-0146) —
    "What am I looking at — and how do I use it?": {
        "es": "¿Qué estoy viendo y cómo lo uso?",
        "fr": "Qu'est-ce que je regarde — et comment l'utiliser ?",
        "de": "Was sehe ich hier — und wie nutze ich es?",
        "pt": "O que estou a ver — e como o utilizo?",
    },
    "What this shows": {
        "es": "Qué muestra",
        "fr": "Ce que cela montre",
        "de": "Was hier gezeigt wird",
        "pt": "O que isto mostra",
    },
    "How to read it": {
        "es": "Cómo leerlo",
        "fr": "Comment le lire",
        "de": "So liest man es",
        "pt": "Como ler",
    },
    "Decisions it informs": {
        "es": "Decisiones que respalda",
        "fr": "Décisions qu'il éclaire",
        "de": "Entscheidungen, die es stützt",
        "pt": "Decisões que apoia",
    },
    "Tip:": {"es": "Consejo:", "fr": "Astuce :", "de": "Tipp:", "pt": "Dica:"},
    "Handling & export-control notice — click to review (CUI / ITAR / EAR)": {
        "es": "Aviso de manejo y control de exportaciones — clic para revisar (CUI / ITAR / EAR)",
        "fr": (
            "Avis de manipulation et de contrôle des exportations — cliquer pour consulter"
            " (CUI / ITAR / EAR)"
        ),
        "de": "Hinweis zu Handhabung und Exportkontrolle — zum Lesen klicken (CUI / ITAR / EAR)",
        "pt": (
            "Aviso de manuseamento e controlo de exportação — clique para rever (CUI / ITAR / EAR)"
        ),
    },
    "Controlled Unclassified Information (CUI)": {
        "es": "Información no clasificada controlada (CUI)",
        "fr": "Informations non classifiées contrôlées (CUI)",
        "de": "Kontrollierte nicht klassifizierte Informationen (CUI)",
        "pt": "Informação não classificada controlada (CUI)",
    },
    "Export control (ITAR / EAR)": {
        "es": "Control de exportaciones (ITAR / EAR)",
        "fr": "Contrôle des exportations (ITAR / EAR)",
        "de": "Exportkontrolle (ITAR / EAR)",
        "pt": "Controlo de exportação (ITAR / EAR)",
    },
    "Your responsibility": {
        "es": "Su responsabilidad",
        "fr": "Votre responsabilité",
        "de": "Ihre Verantwortung",
        "pt": "A sua responsabilidade",
    },
    "Dark mode": {
        "es": "Modo oscuro",
        "fr": "Mode sombre",
        "de": "Dunkler Modus",
        "pt": "Modo escuro",
    },
    "Light mode": {
        "es": "Modo claro",
        "fr": "Mode clair",
        "de": "Heller Modus",
        "pt": "Modo claro",
    },
    "JARVIS mode": {
        "es": "Modo JARVIS",
        "fr": "Mode JARVIS",
        "de": "JARVIS-Modus",
        "pt": "Modo JARVIS",
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
    # — page chrome / common labels (operator: translate the whole UI, not just the nav) —
    "About": {"es": "Acerca de", "fr": "À propos", "de": "Über", "pt": "Sobre"},
    "Language:": {"es": "Idioma:", "fr": "Langue :", "de": "Sprache:", "pt": "Idioma:"},
    "Size": {"es": "Tamaño", "fr": "Taille", "de": "Größe", "pt": "Tamanho"},
    "Scale": {"es": "Escala", "fr": "Échelle", "de": "Skala", "pt": "Escala"},
    "Source": {"es": "Fuente", "fr": "Source", "de": "Quelle", "pt": "Fonte"},
    "Citation": {"es": "Cita", "fr": "Référence", "de": "Beleg", "pt": "Citação"},
    "Count": {"es": "Recuento", "fr": "Nombre", "de": "Anzahl", "pt": "Contagem"},
    "Metric": {"es": "Métrica", "fr": "Métrique", "de": "Kennzahl", "pt": "Métrica"},
    "Dimension": {"es": "Dimensión", "fr": "Dimension", "de": "Dimension", "pt": "Dimensão"},
    "Severity": {"es": "Gravedad", "fr": "Gravité", "de": "Schweregrad", "pt": "Gravidade"},
    "Schedule": {"es": "Cronograma", "fr": "Planning", "de": "Terminplan", "pt": "Cronograma"},
    "Target UID:": {
        "es": "UID objetivo:",
        "fr": "UID cible :",
        "de": "Ziel-UID:",
        "pt": "UID alvo:",
    },
    "to UID": {"es": "a UID", "fr": "vers UID", "de": "zu UID", "pt": "para UID"},
    "Show driving path": {
        "es": "Mostrar ruta determinante",
        "fr": "Afficher le chemin déterminant",
        "de": "Treibenden Pfad anzeigen",
        "pt": "Mostrar caminho determinante",
    },
    "full report": {
        "es": "informe completo",
        "fr": "rapport complet",
        "de": "vollständiger Bericht",
        "pt": "relatório completo",
    },
    "Apply to all pages": {
        "es": "Aplicar a todas las páginas",
        "fr": "Appliquer à toutes les pages",
        "de": "Auf alle Seiten anwenden",
        "pt": "Aplicar a todas as páginas",
    },
    "This version:": {
        "es": "Esta versión:",
        "fr": "Cette version :",
        "de": "Diese Version:",
        "pt": "Esta versão:",
    },
    "Bin by": {
        "es": "Agrupar por",
        "fr": "Regrouper par",
        "de": "Gruppieren nach",
        "pt": "Agrupar por",
    },
    "Years": {"es": "Años", "fr": "Années", "de": "Jahre", "pt": "Anos"},
    "remaining": {"es": "restante", "fr": "restant", "de": "verbleibend", "pt": "restante"},
    "Open ↗": {"es": "Abrir ↗", "fr": "Ouvrir ↗", "de": "Öffnen ↗", "pt": "Abrir ↗"},
    "✓ clear": {"es": "✓ limpiar", "fr": "✓ effacer", "de": "✓ löschen", "pt": "✓ limpar"},
    "▦ Data": {"es": "▦ Datos", "fr": "▦ Données", "de": "▦ Daten", "pt": "▦ Dados"},
    "⭲ Enlarge": {"es": "⭲ Ampliar", "fr": "⭲ Agrandir", "de": "⭲ Vergrößern", "pt": "⭲ Ampliar"},
    "% Comp": {"es": "% Compl.", "fr": "% Achevé", "de": "% Fertig", "pt": "% Concl."},
    "% of tasks": {
        "es": "% de tareas",
        "fr": "% des tâches",
        "de": "% der Vorgänge",
        "pt": "% de tarefas",
    },
    "% of activities": {
        "es": "% de actividades",
        "fr": "% des activités",
        "de": "% der Vorgänge",
        "pt": "% de atividades",
    },
    # — banners / standing notices —
    "Controlled Unclassified Information • CUI": {
        "es": "Información Clasificada Controlada • CUI",
        "fr": "Informations Non Classifiées Contrôlées • CUI",
        "de": "Kontrollierte nicht klassifizierte Informationen • CUI",
        "pt": "Informação Não Classificada Controlada • CUI",
    },
    "Local-only — no data leaves this machine.": {
        "es": "Solo local: ningún dato sale de esta máquina.",
        "fr": "Local uniquement — aucune donnée ne quitte cet ordinateur.",
        "de": "Nur lokal — keine Daten verlassen diesen Rechner.",
        "pt": "Apenas local — nenhum dado sai desta máquina.",
    },
    "AI can err — verify against citations.": {
        "es": "La IA puede equivocarse: verifique con las citas.",
        "fr": "L'IA peut se tromper — vérifiez avec les références.",
        "de": "Die KI kann irren — prüfen Sie anhand der Belege.",
        "pt": "A IA pode errar — verifique com as citações.",
    },
    # — DCMA / help labels —
    "Why it matters:": {
        "es": "Por qué importa:",
        "fr": "Pourquoi c'est important :",
        "de": "Warum es zählt:",
        "pt": "Porque importa:",
    },
    "Threshold:": {"es": "Umbral:", "fr": "Seuil :", "de": "Schwellenwert:", "pt": "Limiar:"},
    "Pass example:": {
        "es": "Ejemplo de aprobado:",
        "fr": "Exemple réussi :",
        "de": "Bestanden-Beispiel:",
        "pt": "Exemplo aprovado:",
    },
    "Fail example:": {
        "es": "Ejemplo de fallo:",
        "fr": "Exemple échoué :",
        "de": "Fehler-Beispiel:",
        "pt": "Exemplo reprovado:",
    },
    "Indicates:": {"es": "Indica:", "fr": "Indique :", "de": "Zeigt an:", "pt": "Indica:"},
    "Recommended action:": {
        "es": "Acción recomendada:",
        "fr": "Action recommandée :",
        "de": "Empfohlene Maßnahme:",
        "pt": "Ação recomendada:",
    },
    "Likelihood:": {
        "es": "Probabilidad:",
        "fr": "Probabilité :",
        "de": "Wahrscheinlichkeit:",
        "pt": "Probabilidade:",
    },
    "Availability:": {
        "es": "Disponibilidad:",
        "fr": "Disponibilité :",
        "de": "Verfügbarkeit:",
        "pt": "Disponibilidade:",
    },
    # — metric names (operator: translate the domain terms too) —
    "Hard Constraints": {
        "es": "Restricciones rígidas",
        "fr": "Contraintes strictes",
        "de": "Harte Einschränkungen",
        "pt": "Restrições rígidas",
    },
    "Negative Float": {
        "es": "Holgura negativa",
        "fr": "Marge négative",
        "de": "Negativer Puffer",
        "pt": "Folga negativa",
    },
    "High Duration": {
        "es": "Duración alta",
        "fr": "Durée élevée",
        "de": "Hohe Dauer",
        "pt": "Duração elevada",
    },
    "High Float": {
        "es": "Holgura alta",
        "fr": "Marge élevée",
        "de": "Hoher Puffer",
        "pt": "Folga elevada",
    },
    "Missing Logic": {
        "es": "Lógica faltante",
        "fr": "Logique manquante",
        "de": "Fehlende Logik",
        "pt": "Lógica em falta",
    },
    "Missed Activities": {
        "es": "Actividades incumplidas",
        "fr": "Activités manquées",
        "de": "Verpasste Vorgänge",
        "pt": "Atividades falhadas",
    },
    "Invalid Dates": {
        "es": "Fechas no válidas",
        "fr": "Dates invalides",
        "de": "Ungültige Daten",
        "pt": "Datas inválidas",
    },
    "Merge Hotspot": {
        "es": "Punto de convergencia",
        "fr": "Point de convergence",
        "de": "Zusammenführungs-Hotspot",
        "pt": "Ponto de convergência",
    },
    "Number of Lags": {
        "es": "Número de retardos",
        "fr": "Nombre de décalages",
        "de": "Anzahl Verzögerungen",
        "pt": "Número de atrasos",
    },
    "Number of Leads": {
        "es": "Número de adelantos",
        "fr": "Nombre d'avances",
        "de": "Anzahl Vorlaufzeiten",
        "pt": "Número de avanços",
    },
    "Lags": {"es": "Retardos", "fr": "Décalages", "de": "Verzögerungen", "pt": "Atrasos"},
    "Leads": {"es": "Adelantos", "fr": "Avances", "de": "Vorläufe", "pt": "Avanços"},
    "FS Relationships": {
        "es": "Relaciones FS",
        "fr": "Liens FS",
        "de": "FS-Beziehungen",
        "pt": "Relações FS",
    },
    "SF Relationships": {
        "es": "Relaciones SF",
        "fr": "Liens SF",
        "de": "SF-Beziehungen",
        "pt": "Relações SF",
    },
    "Critical Path Test": {
        "es": "Prueba de ruta crítica",
        "fr": "Test du chemin critique",
        "de": "Kritischer-Pfad-Test",
        "pt": "Teste do caminho crítico",
    },
    "Logic": {"es": "Lógica", "fr": "Logique", "de": "Logik", "pt": "Lógica"},
    "Baseline Finish": {
        "es": "Fin de línea base",
        "fr": "Fin de référence",
        "de": "Basisplan-Ende",
        "pt": "Fim da linha de base",
    },
    "Baseline finish": {
        "es": "Fin de línea base",
        "fr": "Fin de référence",
        "de": "Basisplan-Ende",
        "pt": "Fim da linha de base",
    },
    "Forecast finish": {
        "es": "Fin previsto",
        "fr": "Fin prévue",
        "de": "Prognostiziertes Ende",
        "pt": "Fim previsto",
    },
    "To-go activities": {
        "es": "Actividades pendientes",
        "fr": "Activités restantes",
        "de": "Verbleibende Vorgänge",
        "pt": "Atividades pendentes",
    },
    "Completion performance": {
        "es": "Rendimiento de finalización",
        "fr": "Performance d'achèvement",
        "de": "Fertigstellungsleistung",
        "pt": "Desempenho de conclusão",
    },
    "Completed on schedule": {
        "es": "Completado a tiempo",
        "fr": "Terminé dans les délais",
        "de": "Planmäßig abgeschlossen",
        "pt": "Concluído no prazo",
    },
    "total float": {
        "es": "holgura total",
        "fr": "marge totale",
        "de": "Gesamtpuffer",
        "pt": "folga total",
    },
    # — Acumen-Fuse quality dimensions / SRA labels —
    "Realism": {"es": "Realismo", "fr": "Réalisme", "de": "Realismus", "pt": "Realismo"},
    "Affordability": {
        "es": "Asequibilidad",
        "fr": "Accessibilité financière",
        "de": "Bezahlbarkeit",
        "pt": "Acessibilidade",
    },
    "Comprehensiveness": {
        "es": "Exhaustividad",
        "fr": "Exhaustivité",
        "de": "Vollständigkeit",
        "pt": "Abrangência",
    },
    # — severity / verdict / likelihood words —
    "HIGH": {"es": "ALTA", "fr": "ÉLEVÉ", "de": "HOCH", "pt": "ALTA"},
    "MEDIUM": {"es": "MEDIA", "fr": "MOYEN", "de": "MITTEL", "pt": "MÉDIA"},
    "LOW": {"es": "BAJA", "fr": "FAIBLE", "de": "NIEDRIG", "pt": "BAIXA"},
    "CONCERN": {
        "es": "PREOCUPACIÓN",
        "fr": "PRÉOCCUPATION",
        "de": "BEDENKEN",
        "pt": "PREOCUPAÇÃO",
    },
    "Moderate": {"es": "Moderado", "fr": "Modéré", "de": "Mäßig", "pt": "Moderado"},
    "Major": {"es": "Mayor", "fr": "Majeur", "de": "Erheblich", "pt": "Maior"},
    "Likely": {"es": "Probable", "fr": "Probable", "de": "Wahrscheinlich", "pt": "Provável"},
    "Possible": {"es": "Posible", "fr": "Possible", "de": "Möglich", "pt": "Possível"},
    "green": {"es": "verde", "fr": "vert", "de": "grün", "pt": "verde"},
    "red": {"es": "rojo", "fr": "rouge", "de": "rot", "pt": "vermelho"},
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
