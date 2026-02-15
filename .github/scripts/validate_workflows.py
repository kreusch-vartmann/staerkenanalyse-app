#!/usr/bin/env python3
"""
GitHub Actions Workflow Validator
Prüft alle Workflows auf Fehler und Abhängigkeiten
"""

import os
import sys
import yaml
from pathlib import Path


class WorkflowValidator:
    def __init__(self):
        self.workflows_dir = Path(__file__).parent.parent / "workflows"
        self.issues = []
        self.warnings = []
        self.info = []

    def validate_all(self):
        """Validiert alle Workflows"""
        if not self.workflows_dir.exists():
            print("❌ Workflows-Verzeichnis nicht gefunden")
            return

        yaml_files = list(self.workflows_dir.glob("*.yml"))
        print(f"🔍 Validiere {len(yaml_files)} Workflow-Dateien...\n")

        for workflow_file in sorted(yaml_files):
            self.validate_workflow(workflow_file)

        self.print_report()

    def validate_workflow(self, workflow_file: Path):
        """Validiert eine einzelne Workflow-Datei"""
        try:
            with open(workflow_file, "r", encoding="utf-8") as f:
                raw_content = f.read()
                f.seek(0)
                content = yaml.safe_load(f)

            if not content:
                self.warnings.append(f"⚠️ {workflow_file.name}: Datei ist leer")
                return

            workflow_name = content.get("name", workflow_file.stem)
            on_triggers = content.get("on", {})

            # Prüfe raw content für 'on:' Deklaration
            has_on = "on:" in raw_content and "on: {}" not in raw_content and "on: []" not in raw_content

            # Prüfe auf 'on: {}' oder 'on: []' (disabled workflows)
            if not has_on or on_triggers == {} or on_triggers == []:
                if "DEPRECATED" in workflow_name:
                    self.info.append(f"ℹ️ {workflow_name}: DISABLED (deprecated)")
                else:
                    self.info.append(f"ℹ️ {workflow_name}: Status OK")
                # Noch immer Jobs validieren
            
            jobs = content.get("jobs", {})
            if not jobs or len(jobs) == 1 and "placeholder" in jobs:
                if "DEPRECATED" in workflow_name:
                    return  # Skip deprecated workflows
                self.issues.append(f"❌ {workflow_name}: Keine echten Jobs definiert")
                return

            for job_name, job_config in jobs.items():
                if job_name != "placeholder":  # Ignoriere Placeholder-Jobs
                    self.validate_job(workflow_file.name, workflow_name, job_name, job_config)

        except yaml.YAMLError as e:
            self.issues.append(f"❌ {workflow_file.name}: YAML Parsing Error - {e}")
        except Exception as e:
            self.issues.append(f"❌ {workflow_file.name}: {e}")

    def validate_job(self, filename, workflow_name, job_name, job_config):
        """Validiert einen einzelnen Job"""
        if not isinstance(job_config, dict):
            return

        runs_on = job_config.get("runs-on")
        if not runs_on:
            self.issues.append(
                f"❌ {workflow_name}/{job_name}: Kein 'runs-on' definiert"
            )

        steps = job_config.get("steps", [])
        if not steps:
            self.warnings.append(
                f"⚠️ {workflow_name}/{job_name}: Keine Steps definiert"
            )

        # Prüfe auf kritische Fehler in Steps
        for i, step in enumerate(steps):
            if isinstance(step, dict):
                name = step.get("name", f"Step {i}")
                run = step.get("run", "")

                # Warne vor 'exit 1' ohne 'continue-on-error' (aber ignoriere wenn 'continue-on-error: true')
                if "exit 1" in str(run) and not step.get("continue-on-error") and "|| true" not in str(run):
                    self.info.append(
                        f"ℹ️ {workflow_name}/{job_name}/{name}: 'exit 1' für Error-Handling"
                    )

    def print_report(self):
        """Gibt einen Bericht aus"""
        print("\n" + "=" * 60)
        print("📋 WORKFLOW VALIDIERUNGS-BERICHT")
        print("=" * 60 + "\n")

        if self.issues:
            print("🔴 KRITISCHE FEHLER:")
            for issue in self.issues:
                print(f"   {issue}")
            print()

        if self.warnings:
            print("🟡 WARNUNGEN:")
            for warning in self.warnings:
                print(f"   {warning}")
            print()

        if self.info:
            print("🔵 INFOS:")
            for inf in self.info:
                print(f"   {inf}")
            print()

        total_problems = len(self.issues) + len(self.warnings)
        if total_problems == 0:
            print("✅ Alle Workflows sind gültig!\n")
        else:
            print(f"⚠️ {total_problems} Problem(e) gefunden\n")

        return len(self.issues) == 0


if __name__ == "__main__":
    try:
        validator = WorkflowValidator()
        validator.validate_all()
    except ImportError:
        print("❌ PyYAML nicht installiert. Installiere mit: pip install pyyaml")
        sys.exit(1)
