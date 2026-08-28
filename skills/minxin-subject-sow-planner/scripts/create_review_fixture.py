#!/usr/bin/env python3
"""Generate the three-course TEST_FIXTURE and the blank curriculum seed."""

from __future__ import annotations

import json
from pathlib import Path

from planner_core import compute_available_periods, event_policy, generate_weeks, parse_date, read_json, relevant_events_for_week


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent


COURSES = [
    {
        "course_id": "ENGLISH-G7-CORE-A", "subject_name": "English Language", "kla": "English Language Education",
        "curriculum_framework": "Hong Kong local curriculum", "key_stage": "Key Stage 3", "grade_level": "G7",
        "course_level": "Core", "class_id": "G7A", "output_language": "en-GB",
        "learner_context": "Mixed-readiness secondary learners developing evidence-based reading, interaction and process writing.",
        "required_content": "Reading, writing, speaking, listening, language in context and multimodal literacy.",
        "assessment_pattern": "Reading/writing/oral evidence; semester assessments; feedback and revision after each major task.",
        "resource_constraints": "School-developed materials, library texts and accessible digital publishing tools.",
        "mc_focus": "MC2;MC3, with MC1 where a real intercultural audience strengthens language learning.",
        "authority_title": "English Language Education Key Learning Area Curriculum Guide (Primary 1–Secondary 6)",
        "authority_version": "2017", "authority_section": "Secondary framework — exact chapter requires teacher confirmation",
        "authority_url": "https://www.edb.gov.hk/en/curriculum-development/kla/eng-edu/", "authority_accessed": "2026-08-28",
        "alignment_status": "INFORMED_BY", "owner": "TEST_FIXTURE owner", "status": "TEST_FIXTURE",
        "notes": "Forward-test sample only; not an approved MINXIN course.",
    },
    {
        "course_id": "MATHEMATICS-G8-CORE-B", "subject_name": "Mathematics", "kla": "Mathematics Education",
        "curriculum_framework": "Hong Kong local curriculum", "key_stage": "Key Stage 3", "grade_level": "G8",
        "course_level": "Core", "class_id": "G8B", "output_language": "en-GB",
        "learner_context": "Mixed-readiness learners who benefit from explicit representation, variation, retrieval and diagnostic feedback.",
        "required_content": "Number and algebra, linear relationships, geometry, probability/statistics, reasoning and problem solving.",
        "assessment_pattern": "Short diagnostic checks, worked reasoning, cumulative problem sets and semester assessments.",
        "resource_constraints": "School-developed examples, graph paper, manipulatives, dynamic geometry and calculators where justified.",
        "mc_focus": "MC2 through rigorous research-informed mathematics teaching; MC3 through perseverance and self-regulation.",
        "authority_title": "Mathematics Education Key Learning Area Curriculum Guide (Primary 1–Secondary 6)",
        "authority_version": "2017", "authority_section": "Key Stage 3 — exact chapter requires teacher confirmation",
        "authority_url": "https://www.edb.gov.hk/en/curriculum-development/kla/ma/", "authority_accessed": "2026-08-28",
        "alignment_status": "INFORMED_BY", "owner": "TEST_FIXTURE owner", "status": "TEST_FIXTURE",
        "notes": "No forced AI, project, group presentation or business-analysis component.",
    },
    {
        "course_id": "VISUAL-ARTS-G9-CORE-C", "subject_name": "Visual Arts", "kla": "Arts Education",
        "curriculum_framework": "Hong Kong local curriculum", "key_stage": "Key Stage 3", "grade_level": "G9",
        "course_level": "Core", "class_id": "G9C", "output_language": "en-GB",
        "learner_context": "Learners developing visual inquiry, technique, critique vocabulary, authorship and independent portfolio habits.",
        "required_content": "Appreciation, contextual research, media experimentation, making, critique, portfolio documentation and revision.",
        "assessment_pattern": "Process portfolio, technical studies, critique response, resolved work and individual artist statement.",
        "resource_constraints": "Drawing/painting media, recycled materials, cameras/tablets, safe cutting tools and display space.",
        "mc_focus": "MC2 through iterative studio practice; MC3 through identity, critique and leadership; selective MC1 global comparison.",
        "authority_title": "Arts Education Key Learning Area Curriculum Guide (Primary 1–Secondary 6)",
        "authority_version": "2017", "authority_section": "Visual Arts at Key Stage 3 — exact chapter requires teacher confirmation",
        "authority_url": "https://www.edb.gov.hk/en/curriculum-development/kla/arts-edu/", "authority_accessed": "2026-08-28",
        "alignment_status": "INFORMED_BY", "owner": "TEST_FIXTURE owner", "status": "TEST_FIXTURE",
        "notes": "Digital/AI media are considered only where authorship, rights and verification are teachable visual-arts concerns.",
    },
]


UNIT_DATA = {
    "ENGLISH-G7-CORE-A": [
        ("U1", "Reading Evidence and Voice", "TOPIC", "How does a writer position a reader?", "close reading and evidence-based interpretation", "annotated text and analytical paragraph", "MC2", "Students revise an interpretation after comparing cited evidence."),
        ("U2", "Writing for Real Readers", "TOPIC", "How do purpose and audience shape language choices?", "process writing and language choices in context", "revised feature article and writer's note", "MC1;MC3", "Students publish for a school audience and explain an intercultural language choice."),
        ("U3", "Speaking, Listening and Viewpoints", "TOPIC", "How can dialogue deepen rather than flatten disagreement?", "oral interaction, listening and source-informed response", "individual speaking record and listening reflection", "MC1;MC3", "Rotating facilitators support dialogue; each student submits individual evidence."),
        ("U4", "Comparative and Multimodal Texts", "TOPIC", "How do medium and culture change meaning?", "comparison, synthesis and multimodal composition", "comparative response and revised multimodal text", "MC1;MC2", "Students compare perspectives from more than one context and justify source use."),
        ("U5", "Assessment Response and Independent Transfer", "REVIEW", "How does feedback become a stronger independent performance?", "diagnosis, revision, transfer and self-regulation", "correction log, transfer task and learning reflection", "MC2;MC3", "Students use evidence from errors and feedback to set and test a personal target."),
        ("CAL", "Calendar and Assessment Windows", "ASSESSMENT", "", "", "", "", ""),
    ],
    "MATHEMATICS-G8-CORE-B": [
        ("U1", "Number Structure and Algebraic Generalisation", "TOPIC", "What structure stays invariant when representations change?", "representing, generalising and justifying", "worked reasoning and cumulative problem set", "MC2", "Students compare solution evidence and revise an invalid generalisation."),
        ("U2", "Linear Relationships", "TOPIC", "How do representations reveal rate and initial value?", "connecting tables, graphs, equations and contexts", "representation map and unfamiliar modelling problem", "MC2", "Students justify which representation exposes a relationship most clearly."),
        ("U3", "Geometry and Deductive Reasoning", "TOPIC", "When is a geometric claim necessarily true?", "conjecturing, constructing and deductive reasoning", "construction record and written justification", "MC2;MC3", "Students persevere through counterexamples and improve a proof using feedback."),
        ("U4", "Probability and Data Reasoning", "TOPIC", "How strong is the evidence for a claim about chance or data?", "sampling, representing, calculating and interpreting", "data critique and probability reasoning task", "MC1;MC2", "Students compare contextual data responsibly and state limits of inference."),
        ("U5", "Assessment Diagnosis and Transfer", "REVIEW", "Which error pattern matters, and how can it be repaired?", "error analysis, deliberate re-practice and transfer", "error taxonomy, corrected solution and transfer check", "MC2;MC3", "Students select an error pattern, plan re-practice and verify improvement."),
        ("CAL", "Calendar and Assessment Windows", "ASSESSMENT", "", "", "", "", ""),
    ],
    "VISUAL-ARTS-G9-CORE-C": [
        ("U1", "Observation, Material and Visual Language", "PRACTICAL", "How do material choices direct attention?", "observational inquiry, media control and visual analysis", "technical studies and annotated process pages", "MC2", "Students compare trials and revise a material decision using visual evidence."),
        ("U2", "Place, Identity and Visual Narrative", "PRACTICAL", "How can a visual narrative hold more than one perspective on place?", "contextual research, composition and visual storytelling", "resolved place narrative and artist note", "MC1;MC3", "Students represent local/global viewpoints responsibly and explain an individual choice."),
        ("U3", "Critique, Authorship and Digital Collage", "PRACTICAL", "How do selection, transformation and attribution shape authorship?", "source evaluation, digital composition, critique and revision", "source log, collage iterations and critique response", "MC1;MC2", "Students document rights/source decisions and revise after evidence-based critique."),
        ("U4", "Independent Body of Work", "PRACTICAL", "How does sustained inquiry become a coherent body of work?", "independent inquiry, technique, curation and reflection", "resolved work, process portfolio and artist statement", "MC2;MC3", "Students manage milestones, lead one studio handover and defend curatorial choices."),
        ("U5", "Portfolio Review and Transfer", "REVIEW", "What does the portfolio reveal about artistic growth?", "selection, evaluation, revision and transfer", "revised portfolio sequence and next-step study", "MC2;MC3", "Students cite portfolio evidence to evaluate progress and plan a new direction."),
        ("CAL", "Calendar and Assessment Windows", "ASSESSMENT", "", "", "", "", ""),
    ],
}


OBJECTIVE_TEXTS = {
    "ENGLISH-G7-CORE-A": {
        "U1": [
            "Students will distinguish explicit meaning from supported inference and identify how narrative voice positions a reader.",
            "Students will select, embed and explain concise textual evidence, linking language choices to a defensible interpretation.",
            "Students will compare interpretations, evaluate the sufficiency of evidence and compose a cohesive analytical response independently.",
        ],
        "U2": [
            "Students will identify how purpose, audience and feature-article conventions shape content, organisation and register.",
            "Students will control vocabulary, sentence structure and cohesion to develop a sourced idea for a specified school audience.",
            "Students will plan, draft, conference, revise and publish a feature article, explaining how feedback changed a deliberate language choice.",
        ],
        "U3": [
            "Students will identify claims, supporting reasons and interaction cues in spoken texts from more than one viewpoint.",
            "Students will ask purposeful questions, build on another speaker's idea and support an oral response with a relevant source.",
            "Students will deliver and refine a source-informed oral contribution, then evaluate listening, turn-taking and audience impact using criteria.",
        ],
        "U4": [
            "Students will explain how medium, mode and cultural context influence a text's selection and presentation of meaning.",
            "Students will synthesise evidence from two texts and compare how language and visual choices position different audiences.",
            "Students will design, test and revise a multimodal text for an authentic audience, justifying source, mode and accessibility choices.",
        ],
        "U5": [
            "Students will classify a reading, writing or oral error using evidence from an assessment or portfolio.",
            "Students will apply targeted feedback in a corrected performance and explain why the revision is more effective.",
            "Students will transfer the repaired strategy to an unfamiliar task and set a specific, evidence-based next target.",
        ],
    },
    "MATHEMATICS-G8-CORE-B": {
        "U1": [
            "Students will recognise number and algebraic structure across equivalent forms and test a generalisation with examples and counterexamples.",
            "Students will manipulate expressions and equations accurately while explaining inverse operations and invariant relationships.",
            "Students will form and justify an algebraic generalisation, then transfer it to an unfamiliar numerical or symbolic problem.",
        ],
        "U2": [
            "Students will identify rate of change and initial value in tables, graphs, equations and contextual descriptions.",
            "Students will translate consistently between representations of a linear relationship and justify the meaning of gradient and intercept.",
            "Students will select, construct and evaluate a linear model for an unfamiliar context, stating assumptions and representational limits.",
        ],
        "U3": [
            "Students will use constructions and precise definitions to form geometric conjectures and locate counterexamples.",
            "Students will build a deductive chain from accepted angle, congruence or shape properties and distinguish verification from proof.",
            "Students will write and critique a complete geometric justification, repairing a missing or invalid step before transfer.",
        ],
        "U4": [
            "Students will construct sample spaces and distinguish experimental from theoretical probability.",
            "Students will represent and compare data using appropriate measures and displays, identifying misleading choices or sampling limits.",
            "Students will evaluate a contextual chance or data claim, quantify relevant evidence and state what the data cannot justify.",
        ],
        "U5": [
            "Students will classify a mathematical error as conceptual, representational, procedural or interpretive using worked evidence.",
            "Students will complete targeted re-practice, annotate a corrected solution and explain the repaired reasoning.",
            "Students will verify improvement on a parallel transfer problem and select the next retrieval target from evidence.",
        ],
    },
    "VISUAL-ARTS-G9-CORE-C": {
        "U1": [
            "Students will analyse how line, value, colour, texture and composition direct attention in selected artworks and observations.",
            "Students will control and compare material techniques through annotated trials, linking visual effect to an intentional choice.",
            "Students will select, refine and resolve an observational study, using critique evidence to revise focal, spatial or material decisions.",
        ],
        "U2": [
            "Students will research visual references to place and identity, recording context, viewpoint and ethical source use.",
            "Students will develop symbols, sequence, perspective and material tests to communicate more than one viewpoint on place.",
            "Students will resolve a visual narrative and explain how contextual research, composition and critique shaped an individual artistic decision.",
        ],
        "U3": [
            "Students will evaluate image provenance, rights, attribution and authorship before selecting material for digital collage.",
            "Students will transform sources through layer, scale and juxtaposition, documenting manual or AI-assisted choices transparently.",
            "Students will use structured critique to revise a digital collage and defend its source, authorship and compositional decisions with process evidence.",
        ],
        "U4": [
            "Students will frame an independent inquiry question and select artist/context references relevant to a proposed body of work.",
            "Students will sustain material experimentation, manage milestones and refine technique in response to process and critique evidence.",
            "Students will curate resolved work and process evidence into a coherent body, articulating intention and growth in an artist statement.",
        ],
        "U5": [
            "Students will select portfolio evidence that demonstrates technical, conceptual and reflective growth against stated criteria.",
            "Students will revise a weak process or outcome page and explain how the change improves the portfolio's evidence.",
            "Students will sequence and evaluate the portfolio, then transfer one learning insight into a feasible next artistic investigation.",
        ],
    },
}


FOCI = {
    "ENGLISH-G7-CORE-A": [
        "Reading stance and annotation", "Explicit and implicit meaning", "Narrative voice", "Selecting concise textual evidence",
        "Explaining language effects", "Comparing interpretations", "Analytical paragraph cohesion", "Reading Festival text comparison",
        "Diagnostic reading transfer", "Audience and purpose", "Feature structure", "Vocabulary precision in context", "Sentence control for emphasis",
        "Drafting from a source set", "Peer conference and revision", "Publication and writer's note", "Semester synthesis and retrieval",
        "Winter break", "First-semester assessment", "First-semester assessment", "Post-assessment reading/writing diagnosis",
        "Cross-cultural narrative for Chinese Culture Day", "Lunar New Year holiday", "Lunar New Year holiday", "Listening for claim and support",
        "Questioning and turn-taking", "Comparing global viewpoints", "Source-informed speaking plan", "Rehearsal, feedback and refinement",
        "Individual speaking evidence", "Listening reflection and transfer", "Comparing print and visual rhetoric", "Synthesis across two texts",
        "English Culture Week: language and identity", "World Book Day multimodal adaptation", "Designing a multimodal text", "User testing and revision",
        "Comparative response under reduced scaffolding", "Portfolio selection and commentary", "Second-semester assessment preparation",
        "Second-semester assessment", "Second-semester assessment", "Post-assessment correction and re-practice", "Year-end transfer reflection",
    ],
    "MATHEMATICS-G8-CORE-B": [
        "Number properties and counterexamples", "Equivalent algebraic forms", "Substitution and structure", "Expanding and factorising as inverse operations",
        "Forming expressions from patterns", "Balancing equations", "Multi-step equation reasoning", "Cumulative algebra transfer", "Error analysis and consolidation",
        "Rate of change in tables", "Coordinates and graphing conventions", "Gradient as a ratio", "Intercept and initial value", "Linking table, graph and equation",
        "Comparing linear models", "Unfamiliar modelling problem", "Semester retrieval and mixed practice", "Winter break", "First-semester assessment",
        "First-semester assessment", "Post-assessment error taxonomy", "Targeted re-practice", "Lunar New Year holiday", "Lunar New Year holiday",
        "Angle relationships from constructions", "Triangle congruence conditions", "Conjecture and counterexample", "Building a deductive chain",
        "Dynamic geometry verification versus proof", "Written geometric justification", "Geometry transfer problem", "Experimental and theoretical probability",
        "Sample spaces and systematic counting", "Relative frequency and simulation", "Representing distributions", "Centre, spread and misleading displays",
        "Comparing contextual data sets", "Limits of inference", "Cumulative probability/data transfer", "Second-semester assessment preparation",
        "Second-semester assessment", "Second-semester assessment", "Post-assessment correction and transfer", "Year-end retrieval map",
    ],
    "VISUAL-ARTS-G9-CORE-C": [
        "Contour and proportion from observation", "Value structure and focal point", "Colour interaction", "Mark-making and surface",
        "Comparing material affordances", "Composition through cropping", "Technical study selection", "Resolved observational study", "Critique response and revision",
        "Researching place through primary images", "Visual symbols and cultural context", "Perspective and viewpoint", "Narrative sequence",
        "Material tests for atmosphere", "Compositional thumbnails", "Mid-process critique", "Resolved place narrative", "Winter break",
        "First-semester assessment", "First-semester assessment", "Portfolio diagnosis and correction", "Chinese Culture Day visual comparison",
        "Lunar New Year holiday", "Lunar New Year holiday", "Source provenance and image rights", "Selection and transformation in collage",
        "Layer, scale and juxtaposition", "Authorship and transparent tool use", "AI & STEAM Week: testing digital ideation with source verification",
        "Structured critique and revision", "Resolved digital collage and source log", "Independent inquiry question", "Artist/context research",
        "Media proposal and risk check", "Sustained studio experimentation", "Milestone critique", "Technique refinement", "Curatorial selection",
        "Artist statement drafting", "Second-semester assessment preparation", "Second-semester assessment", "Second-semester assessment",
        "Portfolio revision after assessment", "Year-end portfolio sequence and transfer",
    ],
}


def make_units_and_objectives():
    units, objectives = [], []
    for course in COURSES:
        course_id = course["course_id"]
        for sequence, data in enumerate(UNIT_DATA[course_id], 1):
            suffix, title, unit_type, question, practice, evidence, concerns, concern_evidence = data
            unit_id = f"{course_id}-{suffix}"
            units.append({
                "unit_id": unit_id, "course_id": course_id, "sequence_no": sequence, "title": title,
                "unit_type": unit_type, "essential_question": question, "disciplinary_practice": practice,
                "expected_evidence": evidence, "target_periods": "", "schedule_policy": "BEFORE_ASSESSMENT" if suffix in {"U1", "U2", "U4"} else "SEQUENTIAL",
                "major_concern_refs": concerns, "major_concern_evidence": concern_evidence, "source_ref": "TEST_FIXTURE design",
                "status": "TEST_FIXTURE",
            })
            if suffix == "CAL":
                continue
            for level in range(1, 4):
                objective_id = f"{course_id}-{suffix}-O{level}"
                objective_text = OBJECTIVE_TEXTS[course_id][suffix][level - 1]
                objectives.append({
                    "objective_id": objective_id, "course_id": course_id, "objective_text": objective_text,
                    "knowledge_type": "CONCEPTUAL_AND_PROCEDURAL", "progression_level": level,
                    "prerequisite_refs": f"{course_id}-{suffix}-O{level-1}" if level > 1 else "",
                    "success_evidence": f"Level {level} evidence within {evidence}.",
                    "standard_anchor": f"{course['authority_title']} ({course['authority_version']}), informed-by fixture",
                    "source_ref": "TEST_FIXTURE design", "alignment_status": "INFORMED_BY", "status": "TEST_FIXTURE",
                })
    return units, objectives


def unit_suffix_for_week(week: int) -> str:
    if week <= 8:
        return "U1"
    if week <= 16:
        return "U2"
    if week <= 24:
        return "U5"
    if week <= 31:
        return "U3"
    if week <= 39:
        return "U4"
    return "U5"


def activity(course_id: str, focus: str, phase: int) -> tuple[str, str, str, str]:
    if course_id.startswith("ENGLISH"):
        actions = [
            f"Teacher modelling and guided annotation establish {focus}; students cite one language choice in an individual exit analysis.",
            f"Students compare two examples of {focus}, use a structured discussion to test interpretations, then write an individual evidence-based response.",
            f"Students draft or rehearse {focus}, receive criteria-referenced peer/teacher feedback, and revise a named language choice for the intended audience.",
        ]
        evidence = f"Annotated or composed language evidence showing {focus} and an individual justification."
    elif course_id.startswith("MATHEMATICS"):
        actions = [
            f"Study a worked-example/non-example sequence for {focus}; complete carefully varied practice and explain the invariant structure.",
            f"Represent {focus} in two mathematical forms, compare solution paths, diagnose one error and correct it with a reason.",
            f"Solve an unfamiliar problem involving {focus}; write a complete justification, use diagnostic feedback and attempt a transfer item independently.",
        ]
        evidence = f"Correct mathematical representation and written reasoning for {focus}, including correction where needed."
    else:
        actions = [
            f"Analyse artist exemplars relevant to {focus}; make a focused technical trial and annotate the visual decision.",
            f"Experiment with material or composition choices for {focus}; compare trials against criteria and select a direction with visual evidence.",
            f"Develop {focus} into a resolved study, take part in evidence-based studio critique, and revise one documented artistic decision.",
        ]
        evidence = f"Individual process-page and visual outcome evidencing {focus}, with a documented revision decision."
    purposes = ["Assessment for learning: diagnostic observation and exit evidence.", "Assessment as learning: criteria-based self/peer check with individual accountability.", "Assessment of/for learning: evaluated performance plus next-step evidence."]
    feedback = f"Teacher/peer feedback identifies one strength and one next step in {focus}; the learner submits a visible correction or revision."
    return actions[phase], evidence, purposes[phase], feedback


def assessment_window_activity(course_id: str, focus: str, after: bool) -> tuple[str, str, str, str]:
    if course_id.startswith("ENGLISH"):
        action = "Students analyse task demands and one response excerpt, record a specific reading/writing error pattern, and complete a short corrected response." if after else "Students use a cumulative retrieval checklist, rehearse evidence-selection and sentence-control routines, and set a self-management target for the assessment."
        evidence = "Individual correction note and revised response excerpt." if after else "Individual retrieval check and assessment-readiness target."
    elif course_id.startswith("MATHEMATICS"):
        action = "Students classify errors from representative solutions, complete targeted re-practice and verify the correction on a parallel transfer item." if after else "Students complete spaced mixed retrieval, compare each step with worked reasoning, and log one final misconception to resolve before the assessment."
        evidence = "Error taxonomy, corrected solution and parallel transfer check." if after else "Cumulative retrieval record with justified corrections."
    else:
        action = "Students use portfolio criteria to identify an evidence gap, annotate a revision decision and improve one selected process or outcome page." if after else "Students audit portfolio evidence against criteria, secure and label work, and set a realistic final refinement priority without starting a new piece."
        evidence = "Annotated portfolio correction and revised evidence page." if after else "Individual portfolio audit and refinement priority."
    action = f"{action} Context: {focus}."
    evidence = f"{evidence} ({focus})."
    purpose = "Assessment for/as learning: use the assessment window to diagnose, correct and regulate learning." if after else "Assessment as learning: final retrieval and readiness check; no high-load new knowledge."
    feedback = f"Brief teacher feedback confirms the next action for {focus}; the learner records the action and evidence of completion."
    return action, evidence, purpose, feedback


def timetable_slots():
    specifications = {
        "ENGLISH-G7-CORE-A": [(1, 1), (3, 2), (5, 3)],
        "MATHEMATICS-G8-CORE-B": [(1, 4), (2, 4), (4, 4), (5, 4)],
        "VISUAL-ARTS-G9-CORE-C": [(2, 5), (4, 5)],
    }
    result = []
    for course in COURSES:
        course_id = course["course_id"]
        for index, (weekday, period) in enumerate(specifications[course_id], 1):
            result.append({
                "slot_id": f"SLOT-{course_id}-{index}", "course_id": course_id, "class_id": course["class_id"],
                "teacher_id": f"TEST-{course_id.split('-')[0]}", "room_id": f"TEST-ROOM-{course_id.split('-')[0]}",
                "weekday": weekday, "period_no": period, "start_time": f"{8+period:02d}:00", "end_time": f"{8+period:02d}:45",
                "valid_from": "2026-09-01", "valid_to": "2027-07-03", "cycle_pattern": "ALL", "active": True,
            })
    return result


def make_plans(calendar: dict, slots: list[dict]):
    settings = {"year_id": "AY2026-27", "academic_start": "2026-09-01", "academic_end": "2027-07-03", "term_2_start": "2027-02-15", "school_weekdays": "1,2,3,4,5"}
    weeks = generate_weeks(settings, calendar["events"])
    plans = []
    for course in COURSES:
        course_id = course["course_id"]
        seen = set()
        unit_occurrences = {}
        prior_focus = "Entry evidence and prior-year learning"
        for week in weeks:
            number = int(week["week_no"])
            focus = FOCI[course_id][number - 1]
            suffix = unit_suffix_for_week(number)
            capacity = compute_available_periods(course, week, slots, calendar["events"])
            phase = (number - 1) % 3
            activities, evidence, purpose, feedback = activity(course_id, focus, phase)
            assessment_events = [event for event in relevant_events_for_week(week, course, calendar["events"]) if event.get("event_type") == "ASSESSMENT" and event_policy(event) == "BLOCK"]
            if capacity == 0:
                suffix, refs, periods = "CAL", "", 0
                learning_focus = "No scheduled instruction; retain the official calendar or assessment label."
                knowledge, practice, activities, evidence, purpose, feedback = "", "", "", "", "", ""
            else:
                if assessment_events:
                    suffix = "U5"
                    end_of_window = max(parse_date(event["end_inclusive"]) for event in assessment_events)
                    after = end_of_window < parse_date(week["date_end"])
                    focus = f"{week['term']} assessment window: correction and learning reflection after the final paper" if after else f"{week['term']} assessment window: cumulative retrieval and self-management"
                    learning_focus = focus
                    activities, evidence, purpose, feedback = assessment_window_activity(course_id, focus, after)
                unit_occurrences[suffix] = unit_occurrences.get(suffix, 0) + 1
                objective_level = min(3, unit_occurrences[suffix])
                refs = f"{course_id}-{suffix}-O{objective_level}"
                periods = min(int(capacity), {"ENGLISH": 3, "MATHEMATICS": 4, "VISUAL": 2}[course_id.split("-")[0]])
                learning_focus = focus
                if course_id.startswith("ENGLISH"):
                    knowledge = f"Vocabulary, syntax, genre/text concepts and cohesion relevant to {focus}."
                elif course_id.startswith("MATHEMATICS"):
                    knowledge = f"Definitions, representations, procedures and connections underpinning {focus}."
                else:
                    knowledge = f"Visual elements, compositional principles, material techniques and contextual concepts relevant to {focus}."
                practice = next(data[4] for data in UNIT_DATA[course_id] if data[0] == suffix)
            repeated = refs in seen and bool(refs)
            if refs:
                seen.add(refs)
            if course_id.startswith("ENGLISH"):
                resources = "School-developed texts and annotation tools"
            elif course_id.startswith("MATHEMATICS"):
                resources = "Worked examples, graph paper, manipulatives or dynamic geometry as needed"
            elif suffix == "U3":
                resources = "Rights-cleared image set, source/licence/attribution log, access dates, school-approved editor and authorship checklist"
            else:
                resources = "Artist references, process journal and media appropriate to the weekly study"
            plans.append({
                "plan_id": f"PLAN-{course_id}-W{number:02d}", "course_id": course_id, "week_id": week["week_id"],
                "unit_id": f"{course_id}-{suffix}", "learning_unit": learning_focus, "prior_learning": prior_focus if capacity else "",
                "objective_refs": refs, "knowledge_content": knowledge, "disciplinary_practice": practice, "activities": activities,
                "evidence": evidence, "assessment_purpose": purpose, "feedback_revision": feedback,
                "resources": resources,
                "values": "Respectful intercultural communication" if course_id.startswith("ENGLISH") else ("Perseverance and intellectual honesty" if course_id.startswith("MATHEMATICS") else "Respect for authorship and diverse expression"),
                "planned_periods": periods, "available_periods": "", "repetition_purpose": "SPIRAL" if repeated else "",
                "progression_delta": f"Reduced scaffolding and higher demand in {focus}." if repeated else "",
                "context_delta": f"New context: {focus}." if repeated else "", "evidence_delta": f"New evidence product for {focus}." if repeated else "",
                "independence_delta": "Learner makes and justifies more decisions independently." if repeated else "",
                "owner": "TEST_FIXTURE owner", "status": "TEST_FIXTURE",
            })
            if capacity:
                prior_focus = focus
    return plans


def main() -> None:
    calendar = read_json(SKILL_DIR / "assets" / "ay2026-27-calendar.json")
    units, objectives = make_units_and_objectives()
    slots = timetable_slots()
    fixture = {
        "schema_version": "2.0", "fixture_status": "TEST_FIXTURE",
        "setup": {"academic_year": "2026-2027", "default_language": "en-GB", "default_profile": "standard"},
        "tables": {"Course_Brief": COURSES, "Timetable_Slots": slots, "Units": units, "Objectives": objectives, "Weekly_Plan": make_plans(calendar, slots)},
    }
    fixture_path = SCRIPT_DIR / "tests" / "fixtures" / "multi-subject-fixture.json"
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    blank = {"schema_version": "2.0", "setup": {"academic_year": "2026-2027", "default_language": "en-GB", "default_profile": "standard"}, "tables": {"Course_Brief": [], "Timetable_Slots": [], "Units": [], "Objectives": [], "Weekly_Plan": []}}
    blank_path = SKILL_DIR / "assets" / "blank-curriculum.json"
    blank_path.write_text(json.dumps(blank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(fixture_path)
    print(blank_path)


if __name__ == "__main__":
    main()
