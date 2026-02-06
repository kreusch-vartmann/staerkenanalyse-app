#!/usr/bin/env python3
"""AI Code Review mit Mistral API für GitHub Pull Requests."""

import os
import sys
from pathlib import Path

try:
    from mistralai import Mistral
except ImportError:
    print("❌ mistralai Package nicht gefunden! Installiere mit: pip install mistralai")
    sys.exit(1)

try:
    from github import Github
except ImportError:
    print("❌ PyGithub Package nicht gefunden! Installiere mit: pip install PyGithub")
    sys.exit(1)


def get_changed_files():
    """Liest geänderte Python-Dateien aus Environment."""
    files_str = os.environ.get('CHANGED_FILES', '')
    if not files_str:
        return []
    return [f.strip() for f in files_str.split('\n') if f.strip() and f.strip().endswith('.py')]


def read_file_content(filepath):
    """Liest Dateiinhalt."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"❌ Fehler beim Lesen von {filepath}: {e}")
        return None


def review_with_mistral(files_content):
    """Sendet Code an Mistral API für Review."""
    api_key = os.environ.get('MISTRAL_API_KEY')
    if not api_key:
        print("❌ MISTRAL_API_KEY nicht gefunden!")
        sys.exit(1)

    client = Mistral(api_key=api_key)
    
    # Prompt aus Template laden
    prompt_path = Path('.github/prompts/code-review-template.txt')
    if prompt_path.exists():
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
    else:
        prompt_template = """Analysiere folgenden Python-Code auf:
- Sicherheitslücken
- Flask-Best-Practices
- SQLAlchemy-Patterns
- Code-Qualität

Code:
{code}

Gib ein strukturiertes Review mit konkreten Empfehlungen."""

    # Code für Review vorbereiten (max 5 Dateien, 500 Zeilen pro Datei)
    code_snippets = []
    for file, content in list(files_content.items())[:5]:
        lines = content.split('\n')
        if len(lines) > 500:
            content = '\n'.join(lines[:500]) + f"\n... ({len(lines) - 500} weitere Zeilen)"
        code_snippets.append(f"### {file}\n```python\n{content}\n```")
    
    code_for_review = "\n\n".join(code_snippets)
    prompt = prompt_template.replace("{diff_content}", code_for_review)

    try:
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Mistral API Fehler: {e}")
        return None


def post_review_comment(review_text):
    """Postet Review-Kommentar auf GitHub PR."""
    github_token = os.environ.get('GITHUB_TOKEN')
    pr_number = int(os.environ.get('PR_NUMBER', 0))
    repo_name = os.environ.get('REPO')

    if not all([github_token, pr_number, repo_name]):
        print("❌ GitHub-Umgebungsvariablen fehlen!")
        sys.exit(1)

    try:
        g = Github(github_token)
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        comment_body = f"""## 🤖 Mistral AI Code Review

{review_text}

---
*Automatisch generiert mit Mistral AI - Bitte manuell validieren!*
"""
        pr.create_issue_comment(comment_body)
        print("✅ Review-Kommentar erfolgreich gepostet!")
    except Exception as e:
        print(f"❌ Fehler beim Posten des Kommentars: {e}")
        sys.exit(1)


def main():
    """Hauptfunktion."""
    print("🤖 Starte AI Code Review...")
    
    # Geänderte Dateien abrufen
    changed_files = get_changed_files()
    if not changed_files:
        print("ℹ️ Keine Python-Dateien geändert - überspringe Review")
        sys.exit(0)

    print(f"📁 Gefundene Dateien: {len(changed_files)}")
    for f in changed_files:
        print(f"  - {f}")
    
    # Dateiinhalte lesen
    files_content = {}
    for file in changed_files:
        content = read_file_content(file)
        if content:
            files_content[file] = content

    if not files_content:
        print("⚠️ Keine Dateiinhalte gelesen - überspringe Review")
        sys.exit(0)

    # Mistral API Review
    print("🔍 Sende Code an Mistral API...")
    review = review_with_mistral(files_content)
    
    if not review:
        print("❌ Kein Review von Mistral API erhalten")
        sys.exit(1)

    # Review auf GitHub posten
    print("📝 Poste Review-Kommentar...")
    post_review_comment(review)
    
    print("✅ AI Code Review abgeschlossen!")
    sys.exit(0)  # Expliziter Success Exit-Code


if __name__ == "__main__":
    main()
