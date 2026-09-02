"""Verificaciones estáticas del laboratorio visual aislado.

No importa la aplicación, no abre una base de datos y no consume servicios.
"""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "frontend" / "theme-lab"
ALLOWED_STORAGE_KEY = "pi_theme_lab_preview"


def read(relative: str) -> str:
    return (LAB / relative).read_text(encoding="utf-8")


def test_theme_lab_files_and_contract() -> None:
    expected = {
        "index.html",
        "theme-lab.css",
        "theme-lab.js",
        "assets/favicon.svg",
        "themes/institutional.css",
        "themes/executive.css",
    }
    assert all((LAB / path).is_file() for path in expected)
    html = read("index.html")
    assert 'class="pi-theme-lab"' in html
    assert 'data-theme="institutional"' in html
    assert "Tema Institucional" in html
    assert "Tema Ejecutivo" in html
    assert "Restaurar Tema Institucional" in html
    assert "<script src=\"theme-lab.js\" defer></script>" in html
    assert not re.search(r"<script(?![^>]+src=)[^>]*>", html, re.IGNORECASE)


def test_no_network_or_executable_escape_hatches() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in LAB.rglob("*") if path.is_file())
    combined = combined.replace("http://www.w3.org/2000/svg", "")
    forbidden = (
        "fetch(", "XMLHttpRequest", "WebSocket", "eval(", "EventSource",
        "navigator.serviceWorker", "/api/", "DATABASE_URL", "railway.app",
        "http://", "https://", "//cdn", "@import url",
    )
    assert all(token not in combined for token in forbidden)


def test_storage_is_exclusive_and_themes_are_isolated() -> None:
    js = read("theme-lab.js")
    html = read("index.html")
    assert ALLOWED_STORAGE_KEY in js
    assert "localStorage.removeItem(STORAGE_KEY)" in js
    assert "localStorage.setItem(STORAGE_KEY" in js
    assert "primeraInfanciaThemeCache" not in js
    assert "data-theme" in html
    for name in ("institutional", "executive"):
        css = read(f"themes/{name}.css")
        assert f'.pi-theme-lab[data-theme="{name}"]' in css


def test_semantic_variables_and_scoped_components() -> None:
    css = read("theme-lab.css")
    themes = read("themes/institutional.css") + read("themes/executive.css")
    variables = (
        "--pi-bg", "--pi-sidebar-bg", "--pi-header-bg", "--pi-surface",
        "--pi-surface-soft", "--pi-text", "--pi-text-muted", "--pi-border",
        "--pi-primary", "--pi-primary-hover", "--pi-accent", "--pi-success",
        "--pi-warning", "--pi-danger", "--pi-focus", "--pi-radius-card",
        "--pi-radius-button", "--pi-shadow-card", "--pi-space-unit",
    )
    assert all(variable in themes for variable in variables)
    components = (
        ".pi-lab-button", ".pi-lab-card", ".pi-lab-input", ".pi-lab-select",
        ".pi-lab-table", ".pi-lab-modal", ".pi-lab-alert", ".pi-lab-badge",
        ".pi-lab-sidebar", ".pi-lab-header", ".pi-lab-kpi",
    )
    assert all(component in css for component in components)
    assert "!important" not in css + themes


def test_executive_review_contract() -> None:
    html = read("index.html")
    executive = read("themes/executive.css")
    assert all(variable in executive for variable in (
        "--pi-sidebar-bg-secondary", "--pi-accent-soft", "--pi-border-strong", "--pi-info",
    ))
    assert all(value in html for value in ("1.248", ">48<", ">325<", ">128<"))
    assert "68 % consumido" in html
    assert "680 de 1.000 créditos utilizados" in html
    assert "320 disponibles" in html
    assert 'aria-busy="true"' in html and "Procesando…" in html
    assert all(status in html for status in ("ACTIVO", "PENDIENTE", "VENCIDO", "SUSPENDIDO"))
    assert all(item in html for item in ("Eventos", "Capacitaciones", "Entregas", "Recordatorios"))
    assert 'aria-invalid="true"' in html


def test_only_fictitious_named_data_is_present() -> None:
    html = read("index.html")
    expected_fictitious = (
        "Fundación Demostración", "Administrador General", "UDS Demostración 1",
        "Centro Infantil Los Pinos", "Hogar Infantil Pequeños Sueños", "Participante Ejemplo",
    )
    assert all(value in html for value in expected_fictitious)
    assert not re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", html)
    assert not re.search(r"\b(?:\+?57)?3\d{9}\b", html)
