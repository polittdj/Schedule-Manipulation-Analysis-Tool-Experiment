"""Grounded Q&A tests — cited fact sheet, relevance, and the no-invented-numbers gate."""

from __future__ import annotations

from schedule_forensics.ai.citations import assert_all_cited
from schedule_forensics.ai.null import NullBackend
from schedule_forensics.ai.qa import (
    answer_question,
    build_fact_sheet,
    model_evidence,
    relevant_facts,
)
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.dcma_audit import audit_schedule
from schedule_forensics.engine.forecast import compute_finish_forecasts
from schedule_forensics.engine.metrics import (
    compute_completion_performance,
    compute_float_bands,
)
from schedule_forensics.engine.recommendations import recommend
from schedule_forensics.model.schedule import Schedule


class _Model:
    """A fake local model whose reply is configurable."""

    name = "ollama"
    is_local = True

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    def is_available(self) -> bool:
        return True

    def list_models(self) -> tuple[str, ...]:
        return ("fake",)

    def pull_model(self, model: str) -> None: ...

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.reply


def _facts(schedule: Schedule):  # type: ignore[no-untyped-def]
    cpm = compute_cpm(schedule)
    return build_fact_sheet(
        schedule,
        cpm,
        audit_schedule(schedule, cpm),
        recommend(schedule, current_cpm=cpm),
        compute_float_bands(schedule, cpm),
        compute_completion_performance(schedule),
        compute_finish_forecasts(schedule, cpm),
    )


def test_fact_sheet_is_fully_cited_and_covers_the_families(golden_project5: Schedule) -> None:
    facts = _facts(golden_project5)
    assert len(facts) > 10
    assert_all_cited(facts)  # §6 — every fact carries file + UID + task
    text = " ".join(f.text for f in facts)
    for token in ("Schedule frame", "Finish forecast", "DCMA", "Float band", "Finding"):
        assert token in text


def test_fact_sheet_includes_cited_derived_metrics(golden_project5: Schedule) -> None:
    """Layer A: the engine-computed derived figures (DCMA pass rate, finish-driving share) appear
    as cited facts, so the analyst (and a live model) gets them already computed and sourced."""
    facts = _facts(golden_project5)
    derived = [f for f in facts if f.text.startswith("Derived —")]
    assert_all_cited(derived)  # derived facts carry citations like any other
    blob = " ".join(f.text for f in derived)
    assert "DCMA 14-point assessment" in blob and "pass rate" in blob
    assert "finish-driving concentration" in blob and "% of the network" in blob


def test_relevant_facts_match_question_terms(golden_project5: Schedule) -> None:
    facts = _facts(golden_project5)
    chosen = relevant_facts(facts, "what does the finish forecast say?")
    assert chosen[0] is facts[0]  # the frame fact always leads
    assert any("forecast" in f.text.lower() for f in chosen[1:4])
    # a vague question still returns a bounded, non-empty selection
    assert 1 <= len(relevant_facts(facts, "??")) <= 12


def test_relevant_facts_vary_by_question_not_one_size_fits_all(golden_project5: Schedule) -> None:
    """Regression: the offline (Null-backend) answer must change with the question — the
    old padding filled every result back up to the cap with the same leading facts, so the
    panel 'gave the same results no matter what you asked'."""
    facts = _facts(golden_project5)
    constraints = relevant_facts(facts, "how many hard constraints are there?")
    forecast = relevant_facts(facts, "what is the finish forecast?")
    assert any("Hard Constraints" in f.text for f in constraints)
    assert any("Finish forecast" in f.text for f in forecast)
    cset, fset = {f.text for f in constraints}, {f.text for f in forecast}
    assert cset != fset  # different questions -> different selections
    assert cset & fset == {facts[0].text}  # they share only the always-leading frame fact
    assert len(constraints) < len(facts)  # focused, not the padded full sheet


def test_relevant_facts_resolve_plurals_and_intent_synonyms(golden_project5: Schedule) -> None:
    """Stemming + forensic-intent aliases: a question reaches the facts that carry the
    answer even when it phrases the idea differently than the engine's fact text."""
    facts = _facts(golden_project5)
    # "findings" (plural) reaches the Finding facts via stemming, not only DCMA rows
    findings = relevant_facts(facts, "what problems or findings exist?")
    assert any(f.text.startswith("Finding [") for f in findings[1:])
    # analyst vocabulary: "slipping / late" reaches the behind/variance/forecast facts
    slipping = relevant_facts(facts, "is the schedule slipping or running late?")
    blob = " ".join(f.text.lower() for f in slipping[1:])
    assert "forecast" in blob or "behind" in blob or "variance" in blob


def test_null_backend_returns_facts_not_prose(golden_project5: Schedule) -> None:
    answer, used = answer_question(NullBackend(), _facts(golden_project5), "how many critical?")
    assert answer is None and used  # no model -> no generated prose, only cited facts


def test_grounded_answer_survives_and_invented_numbers_are_discarded(
    golden_project5: Schedule,
) -> None:
    facts = _facts(golden_project5)
    # an answer quoting only fact figures survives
    grounded = _Model(f"Per the facts: {facts[0].text}")
    answer, _ = answer_question(grounded, facts, "what is the schedule frame?")
    assert answer is not None and "Schedule frame" in answer
    # one invented figure discards the whole answer (strict mode)
    fabricator = _Model("The project will finish in 99999 days.")
    answer2, used2 = answer_question(fabricator, facts, "when will it finish?")
    assert answer2 is None and used2

    # a dying model degrades to the facts, never an error
    class _Boom(_Model):
        def generate(self, prompt: str) -> str:
            raise RuntimeError("gone")

    answer3, used3 = answer_question(_Boom(""), facts, "anything?")
    assert answer3 is None and used3


def test_interpretive_mode_keeps_derived_figures_but_still_grounds(
    golden_project5: Schedule,
) -> None:
    """M18 "AI at full power": the model may COMPUTE from the facts (a derived figure no
    longer discards the answer) — the cited facts still ride along, and the Null/failed
    paths stay fail-closed."""
    facts = _facts(golden_project5)
    deriver = _Model("The slip works out to 42 working days beyond the baseline.")
    answer, used = answer_question(deriver, facts, "how bad is it?", mode="interpretive")
    assert answer is not None and "42" in answer  # derived figure survives
    assert used  # the cited facts always accompany the answer
    assert "compute" in deriver.prompts[-1]  # the interpretive prompt was used
    # the same reply in strict mode is discarded wholesale
    answer2, _ = answer_question(
        _Model("The slip works out to 42 working days beyond the baseline."),
        facts,
        "how bad is it?",
        mode="strict",
    )
    assert answer2 is None
    # Null backend and failures stay fail-closed in interpretive mode too
    answer3, used3 = answer_question(NullBackend(), facts, "anything?", mode="interpretive")
    assert answer3 is None and used3


def test_annotate_mode_keeps_the_answer_but_flags_unsourced_figures(
    golden_project5: Schedule,
) -> None:
    """ADR-0129 annotate (the default): a derived figure is NOT discarded (unlike strict) but is
    flagged in an AI-derived footer (unlike interpretive, which passes it silently)."""
    facts = _facts(golden_project5)
    # 31415 is a figure no engine fact contains
    model = _Model("The answer derives to 31415 days.")
    answer, used = answer_question(model, facts, "how long?", mode="annotate")
    assert answer is not None and answer.startswith("The answer derives to 31415 days.")
    assert "AI-derived" in answer and "31415" in answer  # flagged, not silently passed
    assert used  # the cited facts still ride along
    assert "compute" in model.prompts[-1]  # annotate uses the rich (interpretive) prompt
    # an answer with no figures to flag is returned unchanged (no footer)
    plain = _Model("The schedule is broadly healthy with no major concerns.")
    a2, _ = answer_question(plain, facts, "how is it?", mode="annotate")
    assert a2 is not None and "AI-derived" not in a2
    # Null backend / failures stay fail-closed in annotate mode too
    a3, used3 = answer_question(NullBackend(), facts, "anything?", mode="annotate")
    assert a3 is None and used3


def test_fact_sheet_reports_the_finish_driving_count(golden_project5: Schedule) -> None:
    """The cited sheet now states how many activities drive the computed finish — the
    'critical path' question has a fact to stand on."""
    facts = _facts(golden_project5)
    driving = [f for f in facts if f.text.startswith("Finish-driving activities:")]
    assert len(driving) == 1
    assert driving[0].citations  # §6 — cited to the finish-driving activities


def test_model_evidence_is_the_full_picture_relevance_ordered(golden_project5: Schedule) -> None:
    """A live model is handed the WHOLE cited sheet (frame first, then relevance-ordered),
    not the trimmed slice the analyst is shown."""
    facts = _facts(golden_project5)
    ev = model_evidence(facts, "what is the finish forecast?")
    assert ev[0] is facts[0]  # frame always leads
    assert len(ev) == len(facts)  # the whole sheet (well under the model cap)
    assert any("forecast" in f.text.lower() for f in ev[1:4])  # relevant facts float up


def test_interpretive_feeds_the_model_more_than_it_shows_the_analyst(
    golden_project5: Schedule,
) -> None:
    """Free-analysis fix: on a narrow question the analyst is shown only the matching facts,
    but the model's prompt carries the full schedule picture so it can reason holistically."""
    facts = _facts(golden_project5)
    question = "how many hard constraints are there?"
    shown = relevant_facts(facts, question)
    model = _Model("Here is a thorough analysis.")
    answer, used = answer_question(model, facts, question, mode="interpretive")
    assert answer is not None
    assert used == shown  # the analyst still sees the question-relevant selection
    prompt = model.prompts[-1]
    # the prompt holds more facts than are shown — e.g. forecast facts the question did not match
    assert "Finish forecast" in prompt
    assert not any("Finish forecast" in f.text for f in shown)
    facts_block = prompt.split("FACTS:\n", 1)[1].split("\n\nQUESTION:", 1)[0]
    n_prompt_facts = facts_block.count("\n- ") + 1  # the first fact has no leading newline
    assert n_prompt_facts == len(model_evidence(facts, question))
    assert n_prompt_facts > len(shown)  # full evidence > shown slice


def test_figure_agreement_is_deterministic_and_names_the_disagreement() -> None:
    from schedule_forensics.ai.qa import figure_agreement

    same = figure_agreement("Finish slips 12 days (SPI 0.47).", "SPI 0.47 means 12 days late.")
    assert "identical figures" in same
    differ = figure_agreement("The slip is 12 days.", "The slip is 15 days.")
    assert "DIFFER" in differ and "12" in differ and "15" in differ
    assert "verify against the cited facts" in differ
    # figure-free prose counts as agreement (nothing to contradict)
    assert "identical" in figure_agreement("It is slipping.", "The schedule is late.")


def test_workbook_fact_sheet_spans_versions_and_is_cited(
    golden_project2: Schedule, golden_project5: Schedule
) -> None:
    from schedule_forensics.ai.qa import build_workbook_fact_sheet

    schedules = [golden_project2, golden_project5]
    cpms = [compute_cpm(s) for s in schedules]
    facts = build_workbook_fact_sheet(schedules, cpms)
    assert_all_cited(facts)  # §6 — every fact carries file + UID + task
    text = " ".join(f.text for f in facts)
    assert "In one sentence:" in text  # the briefing bottom-line frame
    assert "Project2" in text and "Project5" in text  # both versions referenced
    assert "Latest-version finish forecast" in text
    assert "Manipulation signal" in text  # the latest-pair manipulation facts


def test_strict_gate_is_role_aware_discards_reused_identifier_f11() -> None:
    """Audit F-11 (now role-aware, ADR-0137): the strict/annotate gate distinguishes a figure that
    appears as a real engine VALUE from one that appears ONLY as an activity name/UID. A digit that
    matches only such an identifier is one the model re-used in another role: strict DISCARDS it and
    annotate FLAGS it. A digit that is also a genuine value is untouched (collision-safe)."""
    from schedule_forensics.ai import qa as qa_module
    from schedule_forensics.ai.citations import Citation, CitedStatement

    cite = Citation("P.xml", 6077, "Milestone 2099")
    facts = (
        CitedStatement(
            "Finding: 5 activities drive the path to 'Milestone 2099' (UID 6077).", (cite,)
        ),
    )
    # the model re-roles the name-digit 2099 as a finish YEAR. 2099 appears in the facts only inside
    # the activity NAME, never as an engine value — STRICT now discards the whole answer.
    answer, _ = answer_question(
        _Model("The project finishes in 2099."), facts, "when does the path finish?", mode="strict"
    )
    assert answer is None  # role-aware: a name-digit re-used as a value is discarded

    # a genuinely-invented number (in no fact, name, or value) is still discarded wholesale
    invented, _ = answer_question(
        _Model("The project finishes in 2031."), facts, "when does the path finish?", mode="strict"
    )
    assert invented is None

    # a real engine VALUE (5 — the count) survives strict; it is a cited value, not an identifier
    kept, _ = answer_question(
        _Model("5 activities drive the path."), facts, "how many drive the path?", mode="strict"
    )
    assert kept == "5 activities drive the path."

    # annotate KEEPS the re-roled answer but flags the identifier for role confirmation
    annotated, _ = answer_question(
        _Model("The project finishes in 2099."),
        facts,
        "when does the path finish?",
        mode="annotate",
    )
    assert annotated is not None
    assert "The project finishes in 2099." in annotated
    assert "2099" in annotated
    assert "activity name or ID" in annotated  # the _ROLE_NOTE role flag

    # the role-aware gate is documented in the module docstring
    assert qa_module.__doc__ is not None
    assert "Role-aware figure gate" in qa_module.__doc__


def test_annotate_shows_verified_derivation_and_flags_unverified_layer_b() -> None:
    """Layer B (ADR-0135): in annotate, a figure reconstructed from the cited figures by a standard
    operation is shown as a VERIFIED derivation (with its arithmetic); a non-reconstructible figure
    is still flagged AI-derived."""
    from schedule_forensics.ai.citations import Citation, CitedStatement

    cite = Citation("P.xml", 1, "T1")
    facts = (CitedStatement("DCMA Missing Logic: 10 of 200 activities lack logic.", (cite,)),)
    ans, _ = answer_question(
        _Model("That is 5% of the network, with 999 unrelated."),
        facts,
        "how much missing logic?",
        mode="annotate",
    )
    assert ans is not None
    assert "Derived figures" in ans and "10 / 200 * 100 = 5" in ans  # verified reconstruction shown
    assert "AI-derived" in ans and "999" in ans  # the invented figure still flagged


def test_strict_accepts_ratio_derivation_but_discards_additive_and_invented_layer_b() -> None:
    """Layer B (ADR-0135): strict accepts a figure that is a RATIO-class reconstruction of sourced
    figures (showing the arithmetic), but discards an additive-only reconstruction (coincidence
    prone) and an invented number."""
    from schedule_forensics.ai.citations import Citation, CitedStatement

    cite = Citation("P.xml", 1, "T1")
    facts = (CitedStatement("DCMA Missing Logic: 10 of 200 activities lack logic.", (cite,)),)

    ok, _ = answer_question(
        _Model("Missing logic affects 5% of activities."), facts, "how much?", mode="strict"
    )
    assert ok is not None
    assert ok.startswith("Missing logic affects 5% of activities.")
    assert "Derived figures" in ok and "10 / 200 * 100 = 5" in ok

    # 210 = 10 + 200 is only an ADDITIVE reconstruction -> strict does not trust it
    additive, _ = answer_question(
        _Model("There are 210 things."), facts, "how many?", mode="strict"
    )
    assert additive is None

    # a genuinely invented number -> discarded
    invented, _ = answer_question(
        _Model("There are 999 things."), facts, "how many?", mode="strict"
    )
    assert invented is None


def test_strict_rejects_invented_figures_no_date_fragment_laundering_qc_d1() -> None:
    """QC audit D1 (ADR-0138): date-heavy facts must not launder an invented figure through the
    Layer-B gate. The ISO dates tokenize whole, so their month/day fragments never become
    'engine value' operands, and an integer target needs an EXACT reconstruction."""
    from schedule_forensics.ai.citations import Citation, CitedStatement
    from schedule_forensics.ai.qa import _figure_roles

    cite = Citation("P.xml", 7, "Kickoff")
    facts = (
        CitedStatement(
            "Schedule frame: project start 2026-03-02, data date 2026-08-27, computed CPM "
            "finish 2028-01-25. 27 activities: 0.8% complete.",
            (cite,),
        ),
    )
    value_figs, _id_figs, _names, _units = _figure_roles(facts)
    assert not any(tok.startswith("-0") for tok in value_figs)  # no month/day fragments
    assert "2026-03-02" in value_figs  # the date itself is a (whole) citable value
    invented, _ = answer_question(
        _Model("There are exactly 3 activities in serious trouble."),
        facts,
        "how many in trouble?",
        mode="strict",
    )
    assert invented is None  # 0.8/27*100 = 2.963 no longer 'verifies' an invented 3


def test_strict_identifier_checked_before_derivation_no_uid_laundering_qc_d4() -> None:
    """QC audit D4 (ADR-0138): a re-roled UID must not launder through a coincidental
    reconstruction. UID 50 == 12/24*100 exactly, and strict must STILL discard it."""
    from schedule_forensics.ai.citations import Citation, CitedStatement

    cite = Citation("plan.mpp", 50, "Install switchgear")
    facts = (CitedStatement("24 activities: 12 complete, 12 not started.", (cite,)),)
    answer, _ = answer_question(
        _Model("50 activities are behind schedule."), facts, "how many behind?", mode="strict"
    )
    assert answer is None
    annotated, _ = answer_question(
        _Model("50 activities are behind schedule."), facts, "how many behind?", mode="annotate"
    )
    assert annotated is not None and "activity name or ID" in annotated  # role-flagged, not shown
    assert "12 / 24 * 100" not in annotated  # never presented as a verified derivation


def test_empty_and_digit_task_names_cannot_shred_the_value_set_qc_d6() -> None:
    """QC audit D6 (ADR-0138): identifier extraction is span-based. An empty citation name must
    not space-split the fact text, and a task literally named '5' must not swallow the 5 inside
    45/95 — the engine's own figures stay citable values."""
    from schedule_forensics.ai.citations import Citation, CitedStatement
    from schedule_forensics.ai.qa import _figure_roles

    empty = (
        CitedStatement(
            "Float band Total Float 0 Days: 12 of 126 incomplete activities (9.5%).",
            (Citation("P.json", 7, ""),),
        ),
    )
    value_figs, _ids, _names, _units = _figure_roles(empty)
    assert {"12", "126", "9.5"} <= value_figs
    kept, _ = answer_question(
        _Model("12 of 126 activities (9.5%) sit at zero float."), empty, "float?", mode="strict"
    )
    assert kept == "12 of 126 activities (9.5%) sit at zero float."  # engine figures never shredded

    digit_named = (
        CitedStatement("Task '5' has 45 of 95 activities (47.4%).", (Citation("P.xml", 9, "5"),)),
    )
    value_figs, id_figs, _names, _units = _figure_roles(digit_named)
    assert {"45", "95", "47.4"} <= value_figs  # boundary-guarded: '5' matches only standalone
    assert "5" in id_figs


def test_strict_allows_identifier_written_as_identifier_qc_d15() -> None:
    """QC audit D15 (ADR-0138): 'UID 143' in an answer is correct identifier-role usage when 143
    is cited — a faithful driving-path answer survives strict. A bare re-roled 143, or an
    invented 'UID 999', is still discarded."""
    from schedule_forensics.ai.citations import Citation, CitedStatement

    cite = Citation("plan.mpp", 143, "Erect steel")
    facts = (
        CitedStatement(
            "The driving path to 'Erect steel' (UID 143) comprises 7 activities with 0 days "
            "of driving slack.",
            (cite,),
        ),
    )
    faithful, _ = answer_question(
        _Model("7 activities drive the path to UID 143 with 0 days of driving slack."),
        facts,
        "driving path?",
        mode="strict",
    )
    assert faithful is not None
    named, _ = answer_question(
        _Model("7 activities drive the path to 'Erect steel' (UID 143)."),
        facts,
        "driving path?",
        mode="strict",
    )
    assert named is not None  # quoting the cited activity name is identifier-role usage
    invented_ref, _ = answer_question(
        _Model("The path runs through UID 999."), facts, "driving path?", mode="strict"
    )
    assert invented_ref is None  # an invented UID reference stays discarded
    re_roled, _ = answer_question(
        _Model("143 activities are late."), facts, "how many late?", mode="strict"
    )
    assert re_roled is None  # bare identifier-as-value stays discarded


def test_cross_check_compares_model_prose_not_gate_footers_qc_d16() -> None:
    """QC audit D16 (ADR-0138): the dual-model cross-check strips the tool-appended footers, so
    two agreeing answers are reported as agreeing even when one carries derivation arithmetic."""
    from schedule_forensics.ai.qa import figure_agreement

    primary = (
        "Half are complete: 50% (12 of 24).\n\n"
        "[Derived figures — recomputed by the tool from the cited facts via a standard "
        "operation (confirm each relationship is meaningful): 12 / 24 * 100 = 50]"
    )
    second = "50% (12 of 24) are complete."
    assert "identical" in figure_agreement(primary, second)
    # genuine disagreement is still reported
    assert "DIFFER" in figure_agreement(primary, "60% (12 of 20) are complete.")


def test_unit_role_gate_blocks_explicit_unit_contradictions_adr0145() -> None:
    """ADR-0145 (the F-11 semantic half's unit step): a value token written with an EXPLICIT unit
    that contradicts every unit the facts state it with is discarded (strict) / flagged
    (annotate). Both sides must be explicit and disjoint — bare usage, bare facts, and
    multi-role tokens are never flagged (collision-safe)."""
    from schedule_forensics.ai.citations import Citation, CitedStatement

    cite = Citation("P.xml", 1, "T1")
    facts = (
        CitedStatement(
            "DCMA Missing Logic: FAIL — 10 of 200 activities (5%). "
            "Float band: 12 days of float on the driving path.",
            (cite,),
        ),
    )
    # a "5%"-only figure re-written as days is a re-roled unit -> strict discards
    a, _ = answer_question(_Model("The margin is 5 days."), facts, "q", mode="strict")
    assert a is None
    # a plain-days figure re-written as a percentage -> strict discards
    a, _ = answer_question(_Model("Float is 12%."), facts, "q", mode="strict")
    assert a is None
    # matching units pass
    a, _ = answer_question(
        _Model("5% of activities lack logic; 12 days of float remain."), facts, "q", mode="strict"
    )
    assert a is not None
    # a bare usage carries no unit claim -> never flagged (conservative by design)
    a, _ = answer_question(_Model("The figure to watch is 5."), facts, "q", mode="strict")
    assert a is not None
    # annotate keeps the answer and flags the unit contradiction
    a, _ = answer_question(_Model("The margin is 5 days."), facts, "q", mode="annotate")
    assert a is not None and "different unit" in a
    # collision safety: a token the facts state in BOTH unit contexts is never flagged
    both = (CitedStatement("5 activities fail (5%).", (cite,)),)
    a, _ = answer_question(_Model("The answer is 5 days behind."), both, "q", mode="strict")
    assert a is not None
