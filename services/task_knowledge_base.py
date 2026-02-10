"""
Assessment-Center Task Knowledge Base.
Strukturierte Wissensdatenbank mit AC-Aufgabentypen, Kompetenzdimensionen und Best-Practice Phasenmodellen.
Wird vom KI-Prompter verwendet, um fachwissen-basierte Aufgaben zu generieren.

Wissensquellen:
- AC-Fachliteratur (Sarges, Wottawa)
- Wikipedia AC-Definitionen
- Unternehmensstandards für Potenzialanalyse
- Excel-Import: Aufgabengenerator_infos.xlsx (3 Sheets)
"""

# =============================================================================
# 1. AUFGABENTYPEN (12er-Kategorien nach AC-Fachliteratur)
# =============================================================================

TASK_TYPES = {
    "self_presentation": {
        "name": "Selbstpräsentation",
        "name_en": "Self-Presentation",
        "category": "Einzel",
        "typical_duration_range": [2, 5],
        "min_participants": 1,
        "max_participants": 1,
        "description": "TN stellt sich vor: Person, Kompetenzen, Motivation. Beobachtet: Auftreten, Struktur, Selbstbewusstsein.",
        "core_activity": "Vortrag über selbst, strukturierte Präsentation von Stärken und Motivationen",
        "observation_focuses": ["Selbstvertrauen", "Strukturierung", "Kommunikationsfähigkeit", "Überzeugungskraft"],
        "suitable_target_groups": ["Schüler", "Azubis", "Trainees", "Fachkräfte", "Führungskräfte"]
    },
    "group_discussion": {
        "name": "Gruppendiskussion",
        "name_en": "Group Discussion",
        "category": "Gruppe",
        "typical_duration_range": [15, 45],
        "min_participants": 4,
        "max_participants": 8,
        "description": "Kontroverse Themenstellung, Gruppe muss Konsens finden. Beobachtet: Argumentation, Teamgeist, Durchsetzung.",
        "core_activity": "Diskussion über kontroverse Thema mit Ziel zu consensual decision",
        "observation_focuses": ["Argumentation", "Überzeugungskraft", "Teamfähigkeit", "Konfliktfähigkeit", "Moderation"],
        "suitable_target_groups": ["Schüler", "Azubis", "Trainees", "Fachkräfte", "Führungskräfte"]
    },
    "practical_creative_group": {
        "name": "Praktisch-kreative Gruppenaufgabe",
        "name_en": "Practical-Creative Group Task",
        "category": "Gruppe",
        "typical_duration_range": [30, 60],
        "min_participants": 3,
        "max_participants": 6,
        "description": "Hands-on-Aufgabe (z.B. Plakat, Turmbau, Brücke). Fokus: Kooperation, Kreativität, Arbeitsorganisation.",
        "core_activity": "Gemeinsame Herstellung eines Produkts unter Voraussetzungen",
        "observation_focuses": ["Kooperation", "Kreativität", "Arbeitsorganisation", "Zeitmanagement", "Rollenübernahme"],
        "suitable_target_groups": ["Schüler", "Azubis", "Trainees"]
    },
    "roleplay_simulation": {
        "name": "Rollenspiel / Gesprächssimulation",
        "name_en": "Roleplay / Conversation Simulation",
        "category": "2-4 TN",
        "typical_duration_range": [15, 30],
        "min_participants": 2,
        "max_participants": 4,
        "description": "Simulation: Kundengespräch, Konfliktgespräch, Überzeugungsgespräch. Fokus: Gesprächstechnik, Empathie.",
        "core_activity": "Rollengebundene Interaktion zwischen zwei oder mehreren Personen",
        "observation_focuses": ["Empathie", "Kommunikation", "Konfliktkompetenz", "Stressresistenz", "Flexibilität"],
        "suitable_target_groups": ["Azubis", "Trainees", "Fachkräfte", "Führungskräfte"]
    },
    "case_study": {
        "name": "Fallstudie (Case Study)",
        "name_en": "Case Study",
        "category": "Einzel oder Gruppe",
        "typical_duration_range": [15, 30],
        "min_participants": 1,
        "max_participants": 6,
        "description": "Komplexes Geschäftsszenario analysieren, Lösung entwickeln und präsentieren. Fokus: Analytisches Denken.",
        "core_activity": "Analyse und strukturierte Problemlösung eines mehrdimensionalen Szenarios",
        "observation_focuses": ["Analytisches Denken", "Strukturierung", "Entscheidungsfähigkeit", "Problemlösung"],
        "suitable_target_groups": ["Fachkräfte", "Führungskräfte"]
    },
    "in_basket": {
        "name": "Postkorbübung",
        "name_en": "In-Basket Exercise",
        "category": "Einzel",
        "typical_duration_range": [20, 60],
        "min_participants": 1,
        "max_participants": 1,
        "description": "Priorisierung von E-Mails/Dokumenten unter Zeitdruck. Fokus: Entscheidungsfähigkeit, Zeitmanagement.",
        "core_activity": "Umgang mit überquellenden Inbox: Kategorisierung, Priorisierung, delegieren",
        "observation_focuses": ["Selbstorganisation", "Entscheidungsfähigkeit", "Zeitmanagement", "Belastbarkeit"],
        "suitable_target_groups": ["Trainees", "Fachkräfte", "Führungskräfte"]
    },
    "fact_finding": {
        "name": "Fact-Finding-Übung",
        "name_en": "Fact-Finding Exercise",
        "category": "Einzel",
        "typical_duration_range": [15, 30],
        "min_participants": 1,
        "max_participants": 1,
        "description": "Unvollständige Information, TN muss systematisch Fragen stellen um Lösung zu entwickeln.",
        "core_activity": "Informationsbeschaffung durch zielgerichtete Fragen + Lösungsentwicklung",
        "observation_focuses": ["Strategisches Denken", "Fragetechnik", "Systematik", "Problemerkennung"],
        "suitable_target_groups": ["Trainees", "Fachkräfte", "Führungskräfte"]
    },
    "cooperative_planning": {
        "name": "Kooperationsaufgabe / Planspiel",
        "name_en": "Cooperative Planning / Business Simulation",
        "category": "Gruppe",
        "typical_duration_range": [30, 60],
        "min_participants": 4,
        "max_participants": 8,
        "description": "Gemeinsame Problemlösung mit verteilten Ressourcen/Infos. Fokus: Zusammenarbeit, Informationsaustausch.",
        "core_activity": "Koordinierte Bearbeitung einer komplexen Aufgabe mit asymmetrischer Informationsverteilung",
        "observation_focuses": ["Kooperation", "Informationsaustausch", "Verhandlung", "Koordination"],
        "suitable_target_groups": ["Azubis", "Trainees", "Fachkräfte", "Führungskräfte"]
    },
    "prioritization": {
        "name": "Priorisierungs-/Entscheidungsaufgabe",
        "name_en": "Prioritization / Decision Task",
        "category": "Gruppe oder Einzel",
        "typical_duration_range": [20, 40],
        "min_participants": 1,
        "max_participants": 8,
        "description": "Ranking, Auswahl, Budgetverteilung unter Zeitdruck und widersprüchlichen Interessen.",
        "core_activity": "Auswahl und Begründung unter Kriterien-Abwägung und Interessenskonflikten",
        "observation_focuses": ["Entscheidungsfähigkeit", "Begründungskompetenz", "Kriterienbewusstsein", "Durchsetzung"],
        "suitable_target_groups": ["Schüler", "Azubis", "Trainees", "Fachkräfte", "Führungskräfte"]
    },
    "presentation": {
        "name": "Präsentationsaufgabe",
        "name_en": "Presentation Task",
        "category": "Einzel",
        "typical_duration_range": [10, 20],
        "min_participants": 1,
        "max_participants": 1,
        "description": "Fachthema oder spontanes Thema aufbereiten und vortragen. Fokus: Strukturierung, Rhetorik.",
        "core_activity": "Vorbereitung und Durchführung einer sachlichen Präsentation",
        "observation_focuses": ["Strukturierung", "Rhetorik", "Überzeugungskraft", "Fachkompetenz"],
        "suitable_target_groups": ["Schüler", "Azubis", "Trainees", "Fachkräfte", "Führungskräfte"]
    },
    "logic_brainteaser": {
        "name": "Brainteaser / Logikaufgaben",
        "name_en": "Brainteaser / Logic Puzzles",
        "category": "Einzel oder Gruppe",
        "typical_duration_range": [10, 30],
        "min_participants": 1,
        "max_participants": 6,
        "description": "Knobelaufgaben, Schätzfragen (Fermi-Fragen). Fokus: Logisches Denken, Kreativität.",
        "core_activity": "Unkonventionelle Lösungsfindung zu abstrakten oder praktischen Problemen",
        "observation_focuses": ["Logisches Denken", "Kreativität", "Querdenken", "Hartnäckigkeit"],
        "suitable_target_groups": ["Schüler", "Azubis", "Trainees", "Fachkräfte", "Führungskräfte"]
    },
    "structured_interview": {
        "name": "Strukturiertes Interview",
        "name_en": "Structured Interview",
        "category": "Einzel",
        "typical_duration_range": [30, 60],
        "min_participants": 1,
        "max_participants": 2,
        "description": "Kompetenzbasiertes Interview mit situativen Fragen. Fokus: Persönlichkeit, Motivation, Selbsteinschätzung.",
        "core_activity": "Dialog nach Interviewleitfaden mit Szenario- und Verhaltensverankerfragen",
        "observation_focuses": ["Selbstreflexion", "Authentizität", "Motivation", "Selbstbewusstsein"],
        "suitable_target_groups": ["Schüler", "Azubis", "Trainees", "Fachkräfte", "Führungskräfte"]
    }
}


# =============================================================================
# 2. KOMPETENZDIMENSIONEN MIT VERHALTENSANKERN (10 Dimensionen)
# =============================================================================

COMPETENCY_DIMENSIONS = {
    "communication": {
        "name": "Kommunikationsfähigkeit",
        "name_en": "Communication",
        "description": "Klar, sachlich und respektvoll mit anderen kommunizieren; aktiv zuhören",
        "positive_indicators": [
            "Drückt sich klar und verständlich aus",
            "Hört aktiv zu und lässt ausreden",
            "Stellt gezielte Rückfragen zum Verständnis",
            "Passt Sprache und Stil an Zielgruppe an",
            "Fasst Ergebnisse und Argumente zusammen"
        ],
        "negative_indicators": [
            "Redet unklar, schweift ab, verliert den roten Faden",
            "Unterbricht andere, hört nicht aktiv zu",
            "Stellt keine Fragen, bleibt passiv",
            "Nutzt ungeeignete Sprache (zu salopp/zu steif/Fachkauderwelsch)",
            "Gibt keine Zusammenfassungen, Ergänzungen unklar"
        ]
    },
    "teamwork": {
        "name": "Teamfähigkeit / Kooperation",
        "name_en": "Teamwork",
        "description": "Zusammenarbeit, Unterstützung anderer, Kompromissbereitschaft und Kollegialität",
        "positive_indicators": [
            "Bezieht andere aktiv in Entscheidungen ein",
            "Geht offen auf Vorschläge anderer ein",
            "Bietet Hilfe und Unterstützung an",
            "Zeigt Wertschätzung für Beiträge anderer",
            "Sucht bei Meinungsverschiedenheiten nach Kompromissen"
        ],
        "negative_indicators": [
            "Dominiert die Gruppe oder schließt andere aus",
            "Ignoriert oder wertet Beiträge anderer ab",
            "Arbeitet isoliert, ohne andere einzubeziehen",
            "Wirkt uninteressiert an Ideen der Gruppe",
            "Beharrt unnachgiebig auf eigener Position"
        ]
    },
    "leadership": {
        "name": "Führungsverhalten",
        "name_en": "Leadership",
        "description": "Initiative ergreifen, strukturieren, moderieren, delegieren und Gruppe lenken",
        "positive_indicators": [
            "Übernimmt Initiative und strukturiert den Prozess",
            "Moderiert Diskussionen fair und konstruktiv",
            "Delegiert Aufgaben sinnvoll nach Stärken",
            "Gibt konstruktives Feedback und ermutigt",
            "Behält Zeitrahmen und Phasen im Blick"
        ],
        "negative_indicators": [
            "Wartet passiv ab, übernimmt keine Verantwortung",
            "Dominiert autoritär ohne Beteiligung",
            "Verteilt Aufgaben unfair oder gar nicht",
            "Kritisiert destruktiv oder gibt kein Feedback",
            "Verliert Zeitmanagement völlig aus den Augen"
        ]
    },
    "analytical_thinking": {
        "name": "Analytisches / Logisches Denken",
        "name_en": "Analytical Thinking",
        "description": "Probleme strukturieren, systematisch analysieren, Zusammenhänge erkennen",
        "positive_indicators": [
            "Strukturiert Probleme systematisch",
            "Erkennt Zusammenhänge und Muster",
            "Zerlegt komplexe Aufgaben in Teilschritte",
            "Begründet Entscheidungen logisch",
            "Erkennt Prioritäten und Kernthemen"
        ],
        "negative_indicators": [
            "Geht unsystematisch und planlos vor",
            "Erkennt keine Zusammenhänge",
            "Fühlt sich von Komplexität schnell überfordert",
            "Entscheidet willkürlich oder 'aus dem Bauch'",
            "Verliert sich in Nebensächlichkeiten"
        ]
    },
    "decision_making": {
        "name": "Entscheidungsfähigkeit",
        "name_en": "Decision-Making",
        "description": "Unter Unsicherheit und Zeitdruck zu tragfähigen Entscheidungen gelangen",
        "positive_indicators": [
            "Entscheidet auch unter Zeitdruck",
            "Sammelt relevante Informationen bevor Entscheidung",
            "Wägt Optionen und Risiken ab",
            "Handelt nach Entscheidung überzeugend",
            "Reflektiert Entscheidungen nachträglich kritisch"
        ],
        "negative_indicators": [
            "Ist unschlüssig und verzögert Entscheidungen",
            "Entscheidet ohne genug Information",
            "Wirft getätigte Entscheidungen ständig um",
            "Versteckt sich hinter anderen bei Verantwortung",
            "Zeigt keine Überzeugung für eigene Entscheidungen"
        ]
    },
    "persuasiveness": {
        "name": "Überzeugungskraft / Durchsetzungsvermögen",
        "name_en": "Persuasiveness",
        "description": "Argumente vertreten, andere überzeugen, Ziele erreichen",
        "positive_indicators": [
            "Argumentiert logisch aufgebaut und überzeugend",
            "Nutzt Beispiele und Evidenz zur Begründung",
            "Passt Argumentation an Zuhörer an",
            "Setzt sich für eigene Positionen ein",
            "Bleibt sachlich auch bei Widerstand"
        ],
        "negative_indicators": [
            "Argumentiert wirr ohne logischen Aufbau",
            "Nutzt nur allgemeine Aussagen ohne Beispiele",
            "Ändert Argumentation unangemessen",
            "Gibt zu schnell auf bei Widerspruch",
            "Wird emotional oder unhöflich bei Konflikten"
        ]
    },
    "conflict_management": {
        "name": "Konfliktfähigkeit",
        "name_en": "Conflict Management",
        "description": "Konstruktiver Umgang mit Meinungsverschiedenheiten und Konflikten",
        "positive_indicators": [
            "Sucht Dialog statt Vermeidung",
            "Versucht andere Perspektiven zu verstehen",
            "Bleibt sachlich in emotionalen Situationen",
            "Bringt konstruktive Lösungsvorschläge",
            "Zeigt Empathie auch bei Uneinigung"
        ],
        "negative_indicators": [
            "Weicht Konflikt aus oder ignoriert ihn",
            "Wertet gegnerische Position kategorisch ab",
            "Wird persönlich oder emotional angegriffen",
            "Sieht nur eigene Position, keine Alternativen",
            "Trägt Konflikte nach außen"
        ]
    },
    "stress_resilience": {
        "name": "Stressresistenz / Belastbarkeit",
        "name_en": "Stress Resilience",
        "description": "Leistungsfähigkeit unter Druck bewahren, Belastungen verarbeiten",
        "positive_indicators": [
            "Bleibt unter Zeitdruck konzentriert und sachlich",
            "Behält Übersicht in chaotischen Situationen",
            "Geht mit Rückschlägen konstruktiv um",
            "Priorisiert souverän bei Überbelastung",
            "Zeigt konstante Leistung über längere Zeit"
        ],
        "negative_indicators": [
            "Wird hektisch, nervös, verliert Übersicht",
            "Reagiert mit Rückzug oder Blockade",
            "Wird frustriert bei kleinen Rückschlägen",
            "Versucht alles gleichzeitig, schafft nichts",
            "Leistungseinbruch bei zunehmendem Druck"
        ]
    },
    "creativity": {
        "name": "Kreativität / Innovationsfähigkeit",
        "name_en": "Creativity",
        "description": "Originelle Ideen, neue Lösungsansätze, unkonventionelles Denken",
        "positive_indicators": [
            "Bringt originelle, unkonventionelle Ideen ein",
            "Denkt über naheliegende Lösungen hinaus",
            "Greift Ideen anderer auf und entwickelt weiter",
            "Experimentiert mit verschiedenen Ansätzen",
            "Verbindet verschiedene Perspektiven"
        ],
        "negative_indicators": [
            "Bringt nur Standardlösungen oder keine Ideen",
            "Bleibt beim Offensichtlichen",
            "Lehnt neue Ideen sofort ab",
            "Ist festgefahren in einem Lösungsweg",
            "Betrachtet Probleme nur eindimensional"
        ]
    },
    "self_organization": {
        "name": "Selbstorganisation / Zeitmanagement",
        "name_en": "Self-Organization",
        "description": "Prioritäten setzen, strukturiert arbeiten, Ziele erreichen",
        "positive_indicators": [
            "Plant Vorgehen strukturiert",
            "Setzt Prioritäten klar",
            "Einhält Fristen und Deadlines",
            "Arbeitet zielgerichtet ohne viel Ablenkung",
            "Passt Plan an veränderte Situationen an"
        ],
        "negative_indicators": [
            "Arbeitet unstrukturiert ohne Plan",
            "Kann nicht zwischen wichtig/unwichtig unterscheiden",
            "Überschreitet ständig Fristen",
            "Lässt sich leicht ablenken",
            "Hält starr am ursprünglichen Plan fest"
        ]
    }
}


# =============================================================================
# 3. ZIELGRUPPEN (6 Kategorien für Target-Group-Differenzierung)
# =============================================================================

TARGET_GROUPS = {
    "students": {
        "name": "Schüler",
        "label": "Schüler (Berufsorientierung)",
        "description": "Schüler in der Berufsorientierung, Stärkenanalyse vor Ausbildungswahl",
        "typical_duration": "3-4 Stunden (½ Tag)",
        "task_style": "Stärkenbasiert, niedrigschwellig, ermutigend, nicht bedrohlich, wertschätzend",
        "suitable_task_types": [
            "self_presentation", "group_discussion", "practical_creative_group",
            "prioritization", "presentation", "logic_brainteaser"
        ],
        "complexity": "niedrig",
        "num_tasks": "4-6",
        "competency_focus": ["teamwork", "communication", "creativity", "decision_making"]
    },
    "volunteers": {
        "name": "Ehrenamt",
        "label": "Ehrenamt (Freiwilligenarbeit)",
        "description": "Freiwillige im Ehrenamt, z.B. Vereine, soziale Projekte, Gemeinwesenarbeit",
        "typical_duration": "3-5 Stunden (½ Tag)",
        "task_style": "Sinnorientiert, gemeinschaftsbezogen, praxisnah, mit Fokus auf Kommunikation, Verantwortung und Zusammenarbeit",
        "suitable_task_types": [
            "group_discussion", "cooperative_planning", "roleplay_simulation",
            "prioritization", "presentation", "practical_creative_group"
        ],
        "complexity": "niedrig-mittel",
        "num_tasks": "4-6",
        "competency_focus": ["teamwork", "communication", "conflict_management", "decision_making"]
    },
    "apprentices": {
        "name": "Azubis",
        "label": "Auszubildende (Potenzialanalyse)",
        "description": "Berufsausbildende in Potenzialanalyse oder Potenzialentwicklung",
        "typical_duration": "4-6 Stunden (½-1 Tag)",
        "task_style": "Praxisnah, handwerklich/fachlich, mit realistischen Szenarien",
        "suitable_task_types": [
            "self_presentation", "group_discussion", "practical_creative_group",
            "roleplay_simulation", "prioritization", "presentation"
        ],
        "complexity": "mittel",
        "num_tasks": "5-7",
        "competency_focus": ["teamwork", "analytical_thinking", "communication", "leadership"]
    },
    "trainees": {
        "name": "Trainees",
        "label": "Trainees / Berufseinsteiger",
        "description": "Hochschulabsolventen und Berufseeinsteiger in Auswahl-Assessments",
        "typical_duration": "6-8 Stunden (1 Tag)",
        "task_style": "Fokus auf Potenzial, nicht auf Erfahrung, Gruppenübungen zentral, realistische Geschäftsszenarien",
        "suitable_task_types": [
            "self_presentation", "group_discussion", "case_study",
            "cooperative_planning", "prioritization", "presentation"
        ],
        "complexity": "mittel-hoch",
        "num_tasks": "6-8",
        "competency_focus": ["analytical_thinking", "communication", "decision_making", "leadership"]
    },
    "experts": {
        "name": "Fachkräfte",
        "label": "Fachkräfte (Auswahl / Entwicklung)",
        "description": "Erfahrene Fachkräfte in Auswahl oder Development Center",
        "typical_duration": "1 Tag (8 Stunden)",
        "task_style": "Fachbezogene Fallstudien, branchenspezifische Szenarien, Fokus auf Expertise und Entscheidungen",
        "suitable_task_types": [
            "case_study", "in_basket", "fact_finding",
            "cooperative_planning", "roleplay_simulation", "structured_interview"
        ],
        "complexity": "hoch",
        "num_tasks": "6-8",
        "competency_focus": ["analytical_thinking", "decision_making", "leadership", "persuasiveness"]
    },
    "leaders": {
        "name": "Führungskräfte-Nachwuchs",
        "label": "Führungskräfte-Nachwuchs (Development Center)",
        "description": "Potenzielle/Nachwuchs-Führungskräfte in umfassenden Development Centern",
        "typical_duration": "1-2 Tage (12-16 Stunden)",
        "task_style": "Komplexe Führungssimulationen, Führungsgespräche, strategische Entscheidungen",
        "suitable_task_types": [
            "case_study", "in_basket", "fact_finding", "cooperative_planning",
            "roleplay_simulation", "structured_interview"
        ],
        "complexity": "sehr hoch",
        "num_tasks": "8-10",
        "competency_focus": ["leadership", "decision_making", "analytical_thinking", "stress_resilience"]
    },
    "employees": {
        "name": "Bestandsmitarbeiter",
        "label": "Bestandsmitarbeiter (Development / Evaluations-AC)",
        "description": "Bestehende Mitarbeiter in Evaluations-AC oder Potenzialentwicklung",
        "typical_duration": "4-6 Stunden (½-1 Tag)",
        "task_style": "Entwicklungsfokus statt Auswahlentscheidung, Stärkenorientierung",
        "suitable_task_types": [
            "group_discussion", "cooperative_planning", "roleplay_simulation",
            "presentation", "structured_interview", "case_study"
        ],
        "complexity": "mittel",
        "num_tasks": "5-7",
        "competency_focus": ["teamwork", "leadership", "decision_making", "communication"]
    }
}


# =============================================================================
# 4. PHASENER-MODELLE (2 Vorlagen mit prozentalen Zeitverteilungen)
# =============================================================================

PHASE_TEMPLATES = {
    "simple": {
        "name": "Einfache Aufgabe (4 Phasen)",
        "description": "Für kurze, weniger komplexe Aufgaben (30-45 Min)",
        "phases": [
            {
                "name": "Instruktion & Vorbereitung",
                "percentage": 0.20,  # 20% der Gesamtdauer
                "description": "Aufgabenstellung erklären, Materialien verteilen, Fragen klären",
            },
            {
                "name": "Individuelle Vorbereitung",
                "percentage": 0.10,
                "description": "Jeder TN arbeitet für sich (lesen, denken, notieren)",
            },
            {
                "name": "Gruppenbearbeitung",
                "percentage": 0.60,
                "description": "Gemeinsame Durchführung, Diskussion, Entscheidungsfindung",
            },
            {
                "name": "Ergebnis & Reflexion",
                "percentage": 0.10,
                "description": "Ergebnis vorstellen, kurze Reflexion, Abbau",
            }
        ]
    },
    "complex": {
        "name": "Komplexe Aufgabe (6 Phasen)",
        "description": "Für längere, mehrphasige Aufgaben mit strategischer Komponente (60-90 Min)",
        "phases": [
            {
                "name": "Briefing",
                "percentage": 0.08,
                "description": "Szenario präsentieren, Rollen verteilen, Rahmen setzen",
            },
            {
                "name": "Individuelle Vorbereitung",
                "percentage": 0.12,
                "description": "Position/Argumente/Rolle für sich erarbeiten",
            },
            {
                "name": "Explorations-Phase",
                "percentage": 0.18,
                "description": "Austausch, Informationssammlung, erste Ideen, gegenseitiges Verstehen",
            },
            {
                "name": "Entscheidungs-Phase",
                "percentage": 0.18,
                "description": "Diskussion, Priorisierung, Konsensfindung, Beschließung",
            },
            {
                "name": "Ergebnissicherung",
                "percentage": 0.10,
                "description": "Dokumentation, Formalisierung, Präsentation",
            },
            {
                "name": "Reflexion & Abbau",
                "percentage": 0.06,
                "description": "Debriefing, Selbsteinschätzung, Raum wieder aufräumen",
            }
        ]
    }
}


# =============================================================================
# 5. MAPPING: Beobachtungsbereiche → Kompetenzdimensionen
# =============================================================================

OBSERVATION_AREA_TO_DIMENSIONS = {
    "Soziale Kompetenzen": [
        "teamwork",           # Zentral
        "communication",      # Zentral
        "leadership",         # Zentral
        "conflict_management",# Zentral
        "creativity",         # Sekundär
        "stress_resilience",  # Sekundär
    ],
    "Verbale Kompetenzen": [
        "communication",      # Zentral
        "persuasiveness",     # Zentral
        "analytical_thinking",# Zentral
        "presentation_skill", # Zentral (aber "presentation" in COMPETENCY_DIMENSIONS)
        "decision_making",    # Sekundär
        "self_organization",  # Sekundär
    ]
}

# Übersetzungshilfe für die zwei App-Bereiche zu den neuen Dimensionen
OBSERVATION_AREA_TO_DIMENSIONS["Verbale Kompetenzen"] = [
    "communication",
    "persuasiveness",
    "analytical_thinking",
    "decision_making",
    "creativity",
    "stress_resilience",
]


# =============================================================================
# HELPER FUNCTION: get_knowledge_for_prompt()
# =============================================================================

def get_knowledge_for_prompt(observation_area: str, participant_count: int, 
                            duration_minutes: int, target_group: str = None) -> str:
    """
    Generiert formatierten Knowledge-Context für KI-Prompt.
    
    Wählt basierend auf Parametern:
    - Passende Aufgabentypen
    - Relevante Kompetenzdimensionen
    - Geeignete Phasenstuktur
    - Zielgruppen-spezifische Anforderungen
    
    Args:
        observation_area: "Soziale Kompetenzen" oder "Verbale Kompetenzen"
        participant_count: Anzahl Teilnehmer
        duration_minutes: Dauer in Minuten
        target_group: Optional target-group key aus TARGET_GROUPS
    
    Returns:
        Formatierter String mit AC-Fachwissen für Prompt-Injection
    """
    
    # Zielgruppe auflösen
    if target_group and target_group in TARGET_GROUPS:
        tg = TARGET_GROUPS[target_group]
        tg_name = tg["name"]
        suitable_types = tg["suitable_task_types"]
        tg_style = tg["task_style"]
        tg_complexity = tg["complexity"]
    else:
        tg_name = "Allgemein (nicht spezifiziert)"
        suitable_types = list(TASK_TYPES.keys())
        tg_style = "Professionelle Assessment-Center Standards"
        tg_complexity = "mittel"
    
    # Phasenstuktur auswählen (>45 Min = komplex)
    phase_template = PHASE_TEMPLATES["complex"] if duration_minutes > 45 else PHASE_TEMPLATES["simple"]
    
    # Kompetenzdimensionen für Bereich
    relevant_dimensions = OBSERVATION_AREA_TO_DIMENSIONS.get(
        observation_area,
        list(COMPETENCY_DIMENSIONS.keys())[:5]
    )
    dimensions_str = ", ".join([
        COMPETENCY_DIMENSIONS[d]["name"] 
        for d in relevant_dimensions if d in COMPETENCY_DIMENSIONS
    ])
    
    # Geeignete Aufgabentypen filtern
    suitable_task_list = []
    for tt_key in suitable_types:
        if tt_key in TASK_TYPES:
            tt = TASK_TYPES[tt_key]
            # Teilnehmer-Bereich prüfen
            if (tt["min_participants"] <= participant_count <= tt["max_participants"]):
                suitable_task_list.append(f"  • {tt['name']}: {tt['description']}")
    
    if not suitable_task_list:
        # Fallback: Alle Typen mit passender Teilnehmerzahl
        for tt_key, tt in TASK_TYPES.items():
            if tt["min_participants"] <= participant_count <= tt["max_participants"]:
                suitable_task_list.append(f"  • {tt['name']}: {tt['description']}")
    
    suitable_tasks_str = "\n".join(suitable_task_list[:5])  # Max 5, um Länge zu begrenzen
    
    # Phasen beschreiben
    phases_str = "\n".join([
        f"  {i+1}. {p['name']} ({int(p['percentage']*100)}%): {p['description']}"
        for i, p in enumerate(phase_template['phases'])
    ])
    
    # Knowledge Context zusammenstellen
    knowledge_text = f"""
### AC-FACHWISSEN (Strukturierte Wissensdatenbank)

**Zielgruppe:** {tg_name}
**Komplexitätslevel:** {tg_complexity}
**Aufgabenstil:** {tg_style}

**Beobachtungsbereiche (Fokus):** {dimensions_str}

**Geeignete Aufgabentypen für diese Parameter:**
{suitable_tasks_str}

**Empfohlene Phasenstruktur ({phase_template['name']}):**
{phases_str}

**Wichtige AC-Standards:**
- Zeitdruck ist ein gewolltes Gestaltungselement
- Aufgabe sollte NICHT vollständig in der Zeit zu bewältigen sein
- Beobachter notieren konkrete Verhaltensbeispiele, nicht nur Bewertungen
- Realistische Szenarien mit Relevanz für Zielgruppe
- Materialien und Ressourcen klar spezifizieren
- Rollen und Aufgaben eindeutig zuordnen"""
    
    return knowledge_text


# =============================================================================
# HILFSFUNKTION: Alle Dimensionen für Rendering
# =============================================================================

def get_all_competencies() -> dict:
    """Gibt alle Kompetenzdimensionen zurück (für UI-Rendering etc.)"""
    return COMPETENCY_DIMENSIONS


def get_all_target_groups() -> dict:
    """Gibt alle Zielgruppen zurück"""
    return TARGET_GROUPS


def get_target_group_options() -> list:
    """Gibt Zielgruppen-Optionen als Liste für Dropdowns zurück"""
    return [
        {"value": None, "label": "Automatisch (Standardvorgaben)"},
    ] + [
        {"value": key, "label": tg["label"]}
        for key, tg in TARGET_GROUPS.items()
    ]
