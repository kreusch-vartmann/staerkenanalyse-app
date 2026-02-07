"""
Blueprint für Report-Management und PDF-Generierung.

Funktionen:
- Report-Konfiguration pro Gruppe (Templates, Logos, Module)
- PDF-Generierung mit konfigurierbarem Design
- Preview/HTML-Ansicht
- Logo-Upload und -Verwaltung
"""

import json
import os
from datetime import datetime
from functools import wraps

from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

from extensions import db
from models import Group, Participant, ReportTemplate, ReportConfiguration, CompanyLogo, ClientLogo

bp = Blueprint('reports', __name__, url_prefix='/reports')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
MAX_LOGO_SIZE = 5 * 1024 * 1024  # 5MB


def allowed_file(filename):
    """Prüft, ob Datei ein erlaubter Dateityp ist."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# =============================================================================
# Logo-Management Routes
# =============================================================================

@bp.route('/<int:group_id>/logo/upload/company', methods=['POST'])
def upload_company_logo(group_id):
    """
    Uploaded zentral ein Company-Logo (überschreibt das aktuelle).
    """
    group = Group.query.get_or_404(group_id)
    
    if 'file' not in request.files:
        return jsonify({'error': 'Keine Datei hochgeladen'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Datei ausgewählt'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Nur Bilder erlaubt (PNG, JPG, GIF)'}), 400
    
    if len(file.read()) > MAX_LOGO_SIZE:
        file.seek(0)
        return jsonify({'error': f'Datei zu groß (max {MAX_LOGO_SIZE//1024//1024}MB)'}), 400
    
    file.seek(0)
    
    # Deaktiviere altes Logo
    old_logo = CompanyLogo.query.filter_by(is_active=True).first()
    if old_logo:
        old_logo.is_active = False
        # Optional: alte Datei löschen
    
    # Speichere neue Datei
    filename = secure_filename(f"company_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file.filename.rsplit('.', 1)[1]}")
    filepath = os.path.join('uploads', 'logos', filename)
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file.save(filepath)
    
    # Speichere in DB
    new_logo = CompanyLogo(
        logo_path=filepath,
        filename=filename,
        is_active=True
    )
    db.session.add(new_logo)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'logo_id': new_logo.id,
        'filepath': filepath
    })


@bp.route('/<int:group_id>/logo/upload/client', methods=['POST'])
def upload_client_logo(group_id):
    """
    Uploaded Client/Auftraggeber-Logo für eine Gruppe.
    """
    group = Group.query.get_or_404(group_id)
    
    if 'file' not in request.files:
        return jsonify({'error': 'Keine Datei hochgeladen'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Datei ausgewählt'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Nur Bilder erlaubt (PNG, JPG, GIF)'}), 400
    
    if len(file.read()) > MAX_LOGO_SIZE:
        file.seek(0)
        return jsonify({'error': f'Datei zu groß (max {MAX_LOGO_SIZE//1024//1024}MB)'}), 400
    
    file.seek(0)
    
    # Lösche altes Client-Logo für diese Gruppe
    old_logo = ClientLogo.query.filter_by(group_id=group_id).first()
    if old_logo:
        # Optional: alte Datei löschen
        db.session.delete(old_logo)
    
    # Speichere neue Datei
    filename = secure_filename(f"client_group{group_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file.filename.rsplit('.', 1)[1]}")
    filepath = os.path.join('uploads', 'logos', filename)
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file.save(filepath)
    
    # Speichere in DB
    new_logo = ClientLogo(
        group_id=group_id,
        logo_path=filepath,
        filename=filename
    )
    db.session.add(new_logo)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'logo_id': new_logo.id,
        'filepath': filepath
    })


# =============================================================================
# Report-Konfiguration Routes
# =============================================================================

@bp.route('/<int:group_id>/configure', methods=['GET', 'POST'])
def configure_report(group_id):
    """
    GET: Zeige Report-Konfigurationsformular
    POST: Speichere Konfiguration
    """
    group = Group.query.get_or_404(group_id)
    templates = ReportTemplate.query.filter_by(is_active=True).all()
    company_logo = CompanyLogo.query.filter_by(is_active=True).first()
    client_logo = ClientLogo.query.filter_by(group_id=group_id).first()
    
    # Existierende oder neue Konfiguration
    config = ReportConfiguration.query.filter_by(group_id=group_id).first()
    if not config:
        # Standard-Konfiguration mit allen Modulen aktiviert
        default_config = {
            "cover_page": {
                "enabled": True,
                "show_title": True,
                "show_participant_name": True,
                "show_group_name": True,
                "show_date": True,
                "show_company_logo": True,
                "show_client_logo": True,
                "title": "Stärkenanalyse",
                "subtitle": "Entwicklungsprofil"
            },
            "self_assessment": {"enabled": True},
            "external_assessment": {"enabled": True},
            "closing_page": {
                "enabled": True,
                "show_signature_fields": True,
                "signature_lines_count": 3,
                "additional_text": ""
            },
            "info_page": {
                "enabled": True,
                "content": "Dieses Profil basiert auf einer Assessment-Center-Methode und stellt Beobachtungen aus Gruppenübungen dar."
            },
            "toc_enabled": False
        }
        config = ReportConfiguration(
            group_id=group_id,
            template_id=templates[0].id if templates else None,
            modules_config=json.dumps(default_config)
        )
        db.session.add(config)
        db.session.commit()
    
    if request.method == 'POST':
        # Parse Module-Konfiguration aus Form
        modules_config = {
            "cover_page": {
                "enabled": request.form.get('cover_page_enabled') == 'on',
                "show_title": request.form.get('cover_page_show_title') == 'on',
                "show_participant_name": request.form.get('cover_page_show_participant_name') == 'on',
                "show_group_name": request.form.get('cover_page_show_group_name') == 'on',
                "show_date": request.form.get('cover_page_show_date') == 'on',
                "show_company_logo": request.form.get('cover_page_show_company_logo') == 'on',
                "show_client_logo": request.form.get('cover_page_show_client_logo') == 'on',
                "title": request.form.get('cover_page_title', 'Stärkenanalyse'),
                "subtitle": request.form.get('cover_page_subtitle', 'Entwicklungsprofil')
            },
            "self_assessment": {
                "enabled": request.form.get('self_assessment_enabled') == 'on'
            },
            "external_assessment": {
                "enabled": request.form.get('external_assessment_enabled') == 'on'
            },
            "closing_page": {
                "enabled": request.form.get('closing_page_enabled') == 'on',
                "show_signature_fields": request.form.get('closing_page_show_signature_fields') == 'on',
                "signature_lines_count": int(request.form.get('closing_page_signature_lines_count', 3)),
                "additional_text": request.form.get('closing_page_additional_text', '')
            },
            "info_page": {
                "enabled": request.form.get('info_page_enabled') == 'on',
                "content": request.form.get('info_page_content', '')
            },
            "toc_enabled": request.form.get('toc_enabled') == 'on'
        }
        
        config.template_id = request.form.get('template_id')
        config.modules_config = json.dumps(modules_config)
        config.updated_at = datetime.now()
        db.session.commit()
        
        flash('Report-Konfiguration gespeichert!', 'success')
        return redirect(url_for('reports.configure_report', group_id=group_id))
    
    modules_config = json.loads(config.modules_config) if config.modules_config else {}
    
    return render_template('reports/configure.html',
                         group=group,
                         config=config,
                         modules_config=modules_config,
                         templates=templates,
                         company_logo=company_logo,
                         client_logo=client_logo)


@bp.route('/<int:group_id>/preview/<int:participant_id>')
def preview_report_html(group_id, participant_id):
    """
    Zeige HTML-Vorschau des Reports (vor PDF-Generierung).
    """
    group = Group.query.get_or_404(group_id)
    participant = Participant.query.get_or_404(participant_id)
    
    if participant.group_id != group_id:
        return jsonify({'error': 'Participant nicht in dieser Gruppe'}), 403
    
    config = ReportConfiguration.query.filter_by(group_id=group_id).first_or_404()
    
    # TODO: Report-Generator als Service implementieren
    # html = ReportGenerator(group, participant, config).build_html()
    
    return render_template('reports/preview.html',
                         group=group,
                         participant=participant,
                         config=config)


@bp.route('/<int:group_id>/generate-pdf/<int:participant_id>', methods=['GET'])
def generate_pdf_report(group_id, participant_id):
    """
    Generiere PDF-Report für einen Participant.
    """
    group = Group.query.get_or_404(group_id)
    participant = Participant.query.get_or_404(participant_id)
    
    if participant.group_id != group_id:
        return jsonify({'error': 'Participant nicht in dieser Gruppe'}), 403
    
    config = ReportConfiguration.query.filter_by(group_id=group_id).first_or_404()
    
    # TODO: Report-Generator als Service implementieren
    # pdf_bytes = ReportGenerator(group, participant, config).to_pdf()
    # return send_file(pdf_bytes, mimetype='application/pdf', as_attachment=True, 
    #                  download_name=f'Report_{participant.name}_{datetime.now():%Y%m%d}.pdf')
    
    return jsonify({'error': 'PDF-Generierung noch nicht implementiert'}), 501


# =============================================================================
# Templates Management Routes
# =============================================================================

@bp.route('/templates', methods=['GET'])
def list_templates():
    """Liste alle Report-Templates."""
    templates = ReportTemplate.query.all()
    return render_template('reports/templates_list.html', templates=templates)


@bp.route('/templates/<int:template_id>', methods=['GET'])
def view_template(template_id):
    """Zeige Template-Details."""
    template = ReportTemplate.query.get_or_404(template_id)
    design_config = json.loads(template.design_config) if template.design_config else {}
    return render_template('reports/template_detail.html', template=template, design_config=design_config)


# =============================================================================
# Hilfsfunktionen
# =============================================================================

def get_default_templates():
    """
    Erstelle oder hole Standard-Templates.
    Wird beim App-Start aufgerufen.
    """
    templates = [
        {
            'name': 'Modern Blue',
            'description': 'Modernes Design mit blauem Akzent',
            'design_config': {
                'primary_color': '#0052CC',
                'secondary_color': '#F0F5FF',
                'accent_color': '#FF6B6B',
                'font_family': 'Inter, sans-serif',
                'font_size_base': '12px',
                'layout_style': 'modern',
                'logo_placement': 'top_center',
                'page_margins': '2cm 2cm 2cm 2cm',
                'header_footer_enabled': True,
                'border_style': 'none',
                'section_divider': 'colored_line'
            }
        },
        {
            'name': 'Classic Professional',
            'description': 'Klassisches professionelles Design',
            'design_config': {
                'primary_color': '#1F2937',
                'secondary_color': '#F3F4F6',
                'accent_color': '#3B82F6',
                'font_family': 'Georgia, serif',
                'font_size_base': '11px',
                'layout_style': 'klassisch',
                'logo_placement': 'top_left',
                'page_margins': '2.5cm 2cm 2.5cm 2cm',
                'header_footer_enabled': True,
                'border_style': 'top_bottom_border',
                'section_divider': 'gray_line'
            }
        },
        {
            'name': 'Minimal Clean',
            'description': 'Minimalistisches, sauberes Design',
            'design_config': {
                'primary_color': '#000000',
                'secondary_color': '#FFFFFF',
                'accent_color': '#6B7280',
                'font_family': 'Helvetica, sans-serif',
                'font_size_base': '10.5px',
                'layout_style': 'minimal',
                'logo_placement': 'top_right',
                'page_margins': '2cm 2cm 2cm 2cm',
                'header_footer_enabled': False,
                'border_style': 'none',
                'section_divider': 'none'
            }
        }
    ]
    
    for template_data in templates:
        if not ReportTemplate.query.filter_by(name=template_data['name']).first():
            template = ReportTemplate(
                name=template_data['name'],
                description=template_data['description'],
                design_config=json.dumps(template_data['design_config']),
                is_active=True
            )
            db.session.add(template)
    
    db.session.commit()
