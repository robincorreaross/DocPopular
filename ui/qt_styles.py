"""
qt_styles.py - Tema Dark/Slate centralizado para o DocPopular (PySide6).
Paleta inspirada no RossPDFEditor com adaptações para o visual PFPB.
"""

# Cores do sistema
COLORS = {
    "bg_main": "#0A1628",
    "bg_sidebar": "#0D1B2A",
    "bg_card": "#0D1B2A",
    "bg_input": "#152030",
    "border": "#1E3450",
    "accent": "#4FC3F7",
    "accent_dark": "#1565C0",
    "text_primary": "#E3F2FD",
    "text_secondary": "#90A4AE",
    "text_muted": "#546E7A",
    "text_label": "#78909C",
    "hover": "#1E3A5F",
    "success": "#66BB6A",
    "error": "#EF5350",
    "warning": "#FF9800",
    "delete_bg": "#B71C1C",
    "delete_hover": "#FF5252",
    "btn_primary": "#1565C0",
    "btn_primary_hover": "#1976D2",
    "btn_secondary": "#37474F",
    "btn_secondary_hover": "#455A64",
    "btn_green": "#2E7D32",
    "btn_green_hover": "#388E3C",
    "separator": "#1E3450",
    "sidebar_active": "#1E3A5F",
}


GLOBAL_QSS = f"""
/* ── Base ──────────────────────────────────────────── */
QMainWindow, QWidget#central {{
    background-color: {COLORS['bg_main']};
}}

QLabel {{
    color: {COLORS['text_primary']};
    background: transparent;
}}

/* ── Sidebar ──────────────────────────────────────── */
QFrame#sidebar {{
    background-color: {COLORS['bg_sidebar']};
    border-right: 1px solid {COLORS['border']};
}}

QPushButton#sidebar_btn {{
    background-color: transparent;
    color: {COLORS['text_primary']};
    border: none;
    border-left: 4px solid transparent;
    border-radius: 0px;
    padding: 12px 24px;
    text-align: left;
    font-size: 14px;
    font-weight: bold;
}}

QPushButton#sidebar_btn:hover {{
    background-color: {COLORS['hover']};
}}

QPushButton#sidebar_btn[active="true"] {{
    background-color: {COLORS['sidebar_active']};
    border-left: 4px solid {COLORS['accent']};
    color: {COLORS['accent']};
}}

/* ── Cards ──────────────────────────────────────── */
QFrame#card {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 16px;
}}

/* ── Inputs ──────────────────────────────────────── */
QLineEdit {{
    background-color: {COLORS['bg_input']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
    selection-background-color: {COLORS['accent_dark']};
}}

QLineEdit:focus {{
    border: 1px solid {COLORS['accent']};
}}

/* ── Botões Primários ─────────────────────────────── */
QPushButton#btn_primary {{
    background-color: {COLORS['btn_primary']};
    color: white;
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 12px 24px;
}}

QPushButton#btn_primary:hover {{
    background-color: {COLORS['btn_primary_hover']};
}}

QPushButton#btn_primary:disabled {{
    background-color: {COLORS['btn_secondary']};
    color: {COLORS['text_muted']};
}}

/* ── Botões Secundários ──────────────────────────── */
QPushButton#btn_secondary {{
    background-color: {COLORS['btn_secondary']};
    color: white;
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 12px 24px;
}}

QPushButton#btn_secondary:hover {{
    background-color: {COLORS['btn_secondary_hover']};
}}

/* ── Botões Verdes ───────────────────────────────── */
QPushButton#btn_green {{
    background-color: {COLORS['btn_green']};
    color: white;
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 12px 24px;
}}

QPushButton#btn_green:hover {{
    background-color: {COLORS['btn_green_hover']};
}}

/* ── ComboBox ────────────────────────────────────── */
QComboBox {{
    background-color: {COLORS['bg_input']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
}}

QComboBox::drop-down {{
    border: none;
    width: 30px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
    selection-background-color: {COLORS['hover']};
    border: 1px solid {COLORS['border']};
}}

/* ── ScrollArea ──────────────────────────────────── */
QScrollArea {{
    background: transparent;
    border: none;
}}

QScrollBar:horizontal, QScrollBar:vertical {{
    background: {COLORS['bg_main']};
    border: none;
    width: 10px;
    height: 10px;
}}

QScrollBar::handle:horizontal, QScrollBar::handle:vertical {{
    background: {COLORS['border']};
    border-radius: 5px;
    min-width: 30px;
    min-height: 30px;
}}

QScrollBar::handle:horizontal:hover, QScrollBar::handle:vertical:hover {{
    background: {COLORS['text_muted']};
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0px;
    width: 0px;
}}

/* ── ProgressBar ─────────────────────────────────── */
QProgressBar {{
    background-color: {COLORS['bg_input']};
    border: none;
    border-radius: 6px;
    text-align: center;
    color: {COLORS['text_primary']};
    font-size: 11px;
    height: 12px;
}}

QProgressBar::chunk {{
    background-color: {COLORS['accent']};
    border-radius: 6px;
}}

/* ── Separadores ─────────────────────────────────── */
QFrame#separator {{
    background-color: {COLORS['separator']};
    max-height: 1px;
    min-height: 1px;
}}

/* ── MessageBox ──────────────────────────────────── */
QMessageBox {{
    background-color: {COLORS['bg_main']};
}}

QMessageBox QLabel {{
    color: {COLORS['text_primary']};
    font-size: 13px;
}}

QMessageBox QPushButton {{
    background-color: {COLORS['btn_primary']};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 12px;
    min-width: 80px;
}}

QMessageBox QPushButton:hover {{
    background-color: {COLORS['btn_primary_hover']};
}}
"""
