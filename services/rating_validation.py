"""
Deterministisches Sicherheitsnetz für KI-generierte SK-/VK-Bewertungen.

Hintergrund: Die Riemann-Kreuz-Polaritäts-Regeln (z.B. in
prompts/reubelriemannv1.txt, Schritt Q2) sind reine Prompt-Instruktionen an
die KI. Weder Mistral noch Gemini halten sie zuverlässig zu 100% ein (siehe
CONTEXT.md-Historie / Session-Analyse vom 2026-09-18: konkreter Nachweis
über einen Analyse-Screenshot, bei dem sowohl die Mindestabstands- als auch
die Cap-Regel verletzt wurden). Dieses Modul erzwingt die Kernregeln
NACHTRÄGLICH und rein deterministisch in Python, damit:

1. Die Zahlen bei identischem KI-Rohoutput IMMER exakt gleich sind
   (kein Interpretationsspielraum mehr nach diesem Schritt).
2. Provider-Unterschiede (Mistral vs. Gemini) die Regelkonformität nicht
   mehr beeinflussen können - unabhängig davon, wie gut das jeweilige
   Modell "rechnen" konnte.

Es werden NUR die beiden dokumentierten SK-Polaritätspaare hart erzwungen
(flexibility<->process_orientation, results_orientation<->team_orientation).
VK bleibt bewusst unangetastet (siehe Prompt: "keine Polaritäts-Pflicht").
Fehlt eine der beiden Dimensionen eines Paares in der KI-Antwort, wird das
Paar übersprungen (kein Erfinden von Werten). Andere, hier nicht bekannte
Dimensions-Keys werden nur auf gültigen Wertebereich/Raster geprüft, sonst
unverändert übernommen - das Modul funktioniert daher auch für ältere/andere
Prompts, die dieselben kanonischen Keys nutzen.
"""

from __future__ import annotations

RATING_MIN = 0.0
RATING_MAX = 10.0
RATING_STEP = 0.5

# Die beiden SK-Polaritätspaare aus dem Riemann-Kreuz-Modell (siehe
# prompts/reubelriemannv1.txt, Abschnitt "DIMENSIONEN, ACHSEN..." und
# Schritt Q2). Deklarierte Design-Heuristik, kein wissenschaftlicher Beleg
# (siehe Analyse zum Riemann-Thomann-Modell) - aber, sofern gewünscht,
# konsistent und nachvollziehbar durchgesetzt.
SK_POLARITY_PAIRS = (
    ("flexibility", "process_orientation"),
    ("results_orientation", "team_orientation"),
)


def _round_to_grid(value: float, step: float = RATING_STEP) -> float:
    """Rundet auf das nächste 0,5-Raster (kaufmännisch)."""
    return round(round(value / step) * step, 2)


def _clamp(value: float, low: float = RATING_MIN, high: float = RATING_MAX) -> float:
    return max(low, min(high, value))


def _sanitize_numeric_dict(ratings: dict) -> dict:
    """Rundet/clamped alle numerischen Werte eines Ratings-Dicts.

    Nicht-numerische oder fehlende Werte werden unverändert durchgelassen
    (kein Erfinden von Daten, keine harten Abstürze bei kaputten KI-Antworten).
    """
    if not isinstance(ratings, dict):
        return ratings

    sanitized = dict(ratings)
    for key, value in ratings.items():
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            continue
        sanitized[key] = _clamp(_round_to_grid(numeric_value))
    return sanitized


def _required_gap(higher_value: float) -> float:
    """Mindestabstand-Tabelle aus prompts/reubelriemannv1.txt, Schritt Q2.

    Abhängig NUR vom höheren der beiden Werte eines Polaritätspaares.
    """
    if higher_value >= 8.5:
        return 4.0
    if higher_value >= 7.0:
        return 3.0
    if higher_value >= 5.5:
        return 2.0
    return 1.0


def _enforce_polarity_pair(sk_ratings: dict, key_a: str, key_b: str) -> None:
    """Erzwingt den Mindestabstand für EIN Polaritätspaar (in-place).

    Die höhere Dimension wird NIE verändert, nur die niedrigere wird -
    falls nötig - nach unten korrigiert. Bei exaktem Gleichstand gewinnt
    deterministisch `key_a` (stabile, reproduzierbare Tie-Break-Regel).
    """
    if key_a not in sk_ratings or key_b not in sk_ratings:
        return

    try:
        value_a = float(sk_ratings[key_a])
        value_b = float(sk_ratings[key_b])
    except (TypeError, ValueError):
        return

    if value_a >= value_b:
        higher_key, higher_value, lower_key, lower_value = key_a, value_a, key_b, value_b
    else:
        higher_key, higher_value, lower_key, lower_value = key_b, value_b, key_a, value_a

    required_gap = _required_gap(higher_value)
    if higher_value - lower_value < required_gap:
        corrected = _clamp(_round_to_grid(higher_value - required_gap))
        sk_ratings[lower_key] = corrected


def enforce_rating_consistency(sk_ratings: dict, vk_ratings: dict) -> tuple[dict, dict]:
    """Deterministisches Nach-Prüfen/Korrigieren von KI-Bewertungen.

    Reihenfolge ist wichtig: zuerst runden/clampen, DANACH erst die
    Polaritäts-Korrektur (die selbst wieder rasterkonforme Werte erzeugt).

    Gibt neue Dicts zurück, mutiert die Eingabe nicht.
    """
    sk_result = _sanitize_numeric_dict(sk_ratings)
    vk_result = _sanitize_numeric_dict(vk_ratings)

    if isinstance(sk_result, dict):
        for key_a, key_b in SK_POLARITY_PAIRS:
            _enforce_polarity_pair(sk_result, key_a, key_b)

    return sk_result, vk_result
