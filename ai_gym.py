"""
KI-Gym: Analyzer Service für Pattern-Extraktion und Prompt-Verbesserungen.
Analysiert ContentEdits und erstellt LearnedPromptRules.
"""

import json
from datetime import datetime, timezone
from typing import List, Dict, Optional

from extensions import db
from models import AIRawResponse, ContentEdit, LearnedPromptRule


# Minimum samples required for training
MIN_SAMPLES_TASKS = 10
MIN_SAMPLES_REPORTS = 50


def get_training_status(response_type: str, observation_area: Optional[str] = None) -> Dict:
    """
    Gibt den aktuellen Trainings-Status zurück.
    
    Args:
        response_type: 'task' oder 'report'
        observation_area: Optional filter (z.B. 'Soziale Kompetenzen')
    
    Returns:
        {
            'total_raw_responses': int,
            'edited_responses': int,
            'pending_analysis': int,
            'avg_edit_magnitude': str,
            'avg_similarity': float,
            'ready_for_training': bool,
            'min_samples_required': int
        }
    """
    # Query raw responses
    query = AIRawResponse.query.filter_by(type=response_type)
    if observation_area:
        query = query.filter_by(observation_area=observation_area)
    
    total_raw = query.count()
    edited_raw = query.filter_by(processing_status='edited').count()
    pending = query.filter_by(processing_status='pending').count()
    
    # Analyze edit metrics
    edits = ContentEdit.query.join(AIRawResponse).filter(
        AIRawResponse.type == response_type
    )
    if observation_area:
        edits = edits.filter(AIRawResponse.observation_area == observation_area)
    
    edits = edits.all()
    
    if edits:
        avg_similarity = sum(e.diff_metrics.get('similarity_percent', 0) for e in edits) / len(edits)
        
        # Count edit magnitudes
        magnitude_counts = {'minor': 0, 'moderate': 0, 'major': 0}
        for edit in edits:
            mag = edit.diff_metrics.get('edit_magnitude', 'moderate')
            magnitude_counts[mag] = magnitude_counts.get(mag, 0) + 1
        
        # Most common magnitude
        avg_magnitude = max(magnitude_counts, key=magnitude_counts.get)
    else:
        avg_similarity = 0.0
        avg_magnitude = "no data"
    
    # Check if ready for training
    min_required = MIN_SAMPLES_TASKS if response_type == 'task' else MIN_SAMPLES_REPORTS
    ready = edited_raw >= min_required
    
    return {
        'total_raw_responses': total_raw,
        'edited_responses': edited_raw,
        'pending_analysis': pending,
        'avg_edit_magnitude': avg_magnitude,
        'avg_similarity': round(avg_similarity, 2),
        'ready_for_training': ready,
        'min_samples_required': min_required
    }


def extract_patterns(edits: List[ContentEdit]) -> Dict:
    """
    Extrahiert Muster aus einer Liste von ContentEdits.
    
    Returns:
        {
            'length_patterns': {...},
            'structure_patterns': {...},
            'tone_patterns': {...},
            'common_edits': [...]
        }
    """
    if not edits:
        return {}
    
    # Length patterns
    length_changes = [e.diff_metrics.get('length_change_percent', 0) for e in edits]
    avg_length_change = sum(length_changes) / len(length_changes)
    
    # Users typically add or remove content?
    adds = sum(1 for lc in length_changes if lc > 5)
    removes = sum(1 for lc in length_changes if lc < -5)
    
    # Magnitude distribution
    magnitudes = [e.diff_metrics.get('edit_magnitude', 'moderate') for e in edits]
    major_edits = sum(1 for m in magnitudes if m == 'major')
    moderate_edits = sum(1 for m in magnitudes if m == 'moderate')
    minor_edits = sum(1 for m in magnitudes if m == 'minor')
    
    # Edit reasons (if provided)
    reasons = [e.edit_reason for e in edits if e.edit_reason and e.edit_reason != "Manuelle Bearbeitung"]
    
    return {
        'length_patterns': {
            'avg_change_percent': round(avg_length_change, 2),
            'tendency': 'expand' if avg_length_change > 5 else 'shorten' if avg_length_change < -5 else 'stable',
            'expansions': adds,
            'reductions': removes
        },
        'magnitude_distribution': {
            'major': major_edits,
            'moderate': moderate_edits,
            'minor': minor_edits,
            'total': len(edits)
        },
        'edit_reasons': reasons[:10]  # Top 10 reasons
    }


def analyze_and_suggest_rules(response_type: str, observation_area: Optional[str] = None) -> List[Dict]:
    """
    Analysiert vorhandene Edits und schlägt LearnedPromptRules vor.
    
    Args:
        response_type: 'task' oder 'report'
        observation_area: Optional filter
    
    Returns:
        List of rule suggestions (not yet saved to DB):
        [{
            'rule_type': str,
            'rule_content': dict,
            'confidence': float,
            'reasoning': str,
            'samples_analyzed': int
        }]
    """
    # Get all edited responses
    query = AIRawResponse.query.filter_by(type=response_type, processing_status='edited')
    if observation_area:
        query = query.filter_by(observation_area=observation_area)
    
    raw_responses = query.all()
    
    if not raw_responses:
        return []
    
    # Collect all edits
    all_edits = []
    for raw in raw_responses:
        all_edits.extend(raw.edits)
    
    if not all_edits:
        return []
    
    # Extract patterns
    patterns = extract_patterns(all_edits)
    
    # Generate rules based on patterns
    rules = []
    
    # Rule 1: Length adjustment
    length_pattern = patterns.get('length_patterns', {})
    if abs(length_pattern.get('avg_change_percent', 0)) > 10:
        tendency = length_pattern['tendency']
        if tendency == 'expand':
            instruction = "Generiere ausführlichere Inhalte mit mehr Details und Beispielen."
            confidence = min(0.8, length_pattern['expansions'] / len(all_edits))
        elif tendency == 'shorten':
            instruction = "Formuliere prägnanter und fokussierter. Vermeide redundante Informationen."
            confidence = min(0.8, length_pattern['reductions'] / len(all_edits))
        else:
            instruction = None
            confidence = 0
        
        if instruction and confidence > 0.3:
            rules.append({
                'rule_type': 'length',
                'rule_content': {
                    'pattern': f"User ändert Länge durchschnittlich um {length_pattern['avg_change_percent']}%",
                    'instruction': instruction
                },
                'confidence': round(confidence, 2),
                'reasoning': f"Basierend auf {len(all_edits)} Edits: {length_pattern['expansions']} Erweiterungen, {length_pattern['reductions']} Kürzungen",
                'samples_analyzed': len(all_edits)
            })
    
    # Rule 2: Edit magnitude
    mag_dist = patterns.get('magnitude_distribution', {})
    if mag_dist.get('major', 0) > len(all_edits) * 0.3:
        # Viele große Änderungen → Output entspricht nicht den Erwartungen
        rules.append({
            'rule_type': 'quality',
            'rule_content': {
                'pattern': f"{mag_dist['major']} von {mag_dist['total']} Edits sind major changes",
                'instruction': "Achte besonders auf die spezifischen Anforderungen der Nutzer. Die bisherigen Outputs erfordern häufig größere Überarbeitungen."
            },
            'confidence': min(0.7, mag_dist['major'] / mag_dist['total']),
            'reasoning': f"Hohe Rate an major edits deutet auf systematische Qualitätslücke hin",
            'samples_analyzed': len(all_edits)
        })
    
    # Rule 3: Consistency (if mostly minor edits)
    if mag_dist.get('minor', 0) > len(all_edits) * 0.6:
        rules.append({
            'rule_type': 'consistency',
            'rule_content': {
                'pattern': f"{mag_dist['minor']} von {mag_dist['total']} Edits sind nur minor changes",
                'instruction': "Die bisherige Qualität ist gut. Behalte den aktuellen Stil und die Struktur bei."
            },
            'confidence': min(0.9, mag_dist['minor'] / mag_dist['total']),
            'reasoning': "Nur kleinere Anpassungen nötig zeigen gute Grundqualität",
            'samples_analyzed': len(all_edits)
        })
    
    return rules


def apply_training(response_type: str, observation_area: Optional[str] = None, 
                   created_by_id: Optional[int] = None) -> Dict:
    """
    Führt Training durch: Analysiert Edits, erstellt LearnedPromptRules.
    
    Args:
        response_type: 'task' oder 'report'
        observation_area: Optional filter
        created_by_id: User ID der Person, die Training triggert
    
    Returns:
        {
            'status': 'success' | 'error',
            'rules_created': int,
            'samples_analyzed': int,
            'message': str
        }
    """
    try:
        # Check if ready for training
        status = get_training_status(response_type, observation_area)
        if not status['ready_for_training']:
            return {
                'status': 'error',
                'rules_created': 0,
                'samples_analyzed': 0,
                'message': f"Nicht genug Daten. Benötigt: {status['min_samples_required']}, vorhanden: {status['edited_responses']}"
            }
        
        # Generate rule suggestions
        rule_suggestions = analyze_and_suggest_rules(response_type, observation_area)
        
        if not rule_suggestions:
            return {
                'status': 'error',
                'rules_created': 0,
                'samples_analyzed': status['edited_responses'],
                'message': "Keine Muster gefunden, die Rules rechtfertigen würden"
            }
        
        # Save rules to database
        rules_created = 0
        for suggestion in rule_suggestions:
            rule = LearnedPromptRule(
                type=response_type,
                observation_area=observation_area,
                rule_type=suggestion['rule_type'],
                rule_content=suggestion['rule_content'],
                confidence=suggestion['confidence'],
                samples_analyzed=suggestion['samples_analyzed'],
                reasoning=suggestion['reasoning'],
                is_active=True,
                created_by_id=created_by_id
            )
            db.session.add(rule)
            rules_created += 1
        
        # Mark analyzed responses as 'analyzed'
        query = AIRawResponse.query.filter_by(type=response_type, processing_status='edited')
        if observation_area:
            query = query.filter_by(observation_area=observation_area)
        
        for raw_resp in query.all():
            raw_resp.processing_status = 'analyzed'
        
        db.session.commit()
        
        return {
            'status': 'success',
            'rules_created': rules_created,
            'samples_analyzed': status['edited_responses'],
            'message': f"✓ {rules_created} Rules erstellt aus {status['edited_responses']} Edits"
        }
    
    except Exception as e:
        db.session.rollback()
        return {
            'status': 'error',
            'rules_created': 0,
            'samples_analyzed': 0,
            'message': f"Fehler beim Training: {str(e)}"
        }


def get_active_rules(response_type: str, observation_area: Optional[str] = None) -> List[LearnedPromptRule]:
    """
    Holt alle aktiven Rules für einen bestimmten Typ.
    
    Args:
        response_type: 'task' oder 'report'
        observation_area: Optional filter
    
    Returns:
        List of active LearnedPromptRule objects, sorted by confidence (desc)
    """
    query = LearnedPromptRule.query.filter_by(type=response_type, is_active=True)
    if observation_area:
        query = query.filter(
            (LearnedPromptRule.observation_area == observation_area) |
            (LearnedPromptRule.observation_area.is_(None))  # Global rules
        )
    
    return query.order_by(LearnedPromptRule.confidence.desc()).all()


def format_rules_for_prompt(rules: List[LearnedPromptRule]) -> str:
    """
    Formatiert LearnedPromptRules als Text für System-Prompts.
    
    Args:
        rules: Liste von LearnedPromptRule objects
    
    Returns:
        Formatierter String mit allen Rules
    """
    if not rules:
        return ""
    
    lines = ["\n=== GELERNTE BEST PRACTICES (aus Nutzer-Edits) ==="]
    
    for i, rule in enumerate(rules, 1):
        content = rule.rule_content
        instruction = content.get('instruction', '')
        pattern = content.get('pattern', '')
        
        lines.append(f"\n{i}. [{rule.rule_type.upper()}] (Confidence: {rule.confidence:.0%})")
        if pattern:
            lines.append(f"   Beobachtung: {pattern}")
        lines.append(f"   → {instruction}")
    
    lines.append("\nBerücksichtige diese Erkenntnisse in deiner Antwort.\n")
    
    return "\n".join(lines)
