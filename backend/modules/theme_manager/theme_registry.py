"""Registro cerrado de temas visuales oficiales."""
from __future__ import annotations

from copy import deepcopy


THEME_KEYS = frozenset({
    'ocean-deep', 'neutral-professional', 'natura-green',
    'aurora-violet', 'warm-sand', 'executive-premium', 'alto-contraste',
})


def build_system_themes(default_config: dict) -> list[dict]:
    def theme(code, name, description, icon, mode, colors, category='profesional'):
        config = deepcopy(default_config)
        config['colorMode'] = mode
        config['colors'].update(colors)
        config['modes'] = {'oscuro': {}, 'claro': {}}
        return {
            'codigo': code, 'nombre': name, 'descripcion': description,
            'categoria': category, 'activo': 1, 'es_sistema': 1,
            'css_path': '', 'icono': icon, 'configuracion': config,
        }

    return [
        theme('ocean-deep', 'Océano Profundo', 'Administración, auditoría y uso nocturno.', 'waves', 'dark', {
            'background': '#061326', 'surface': '#0c2340', 'surfaceSoft': '#123052', 'text': '#f3f8ff',
            'muted': '#9fb4cc', 'primary': '#12b9df', 'primaryHover': '#0ea5c6', 'accent': '#4e7cff', 'border': '#1c4567'}),
        theme('neutral-professional', 'Neutro Profesional', 'Tema claro para trabajo diario.', 'briefcase-business', 'light', {
            'background': '#f4f7fb', 'surface': '#ffffff', 'surfaceSoft': '#f8fafc', 'text': '#17243b',
            'muted': '#66758b', 'primary': '#2563eb', 'primaryHover': '#1d4ed8', 'accent': '#0ea5c6', 'border': '#dfe6ef'}),
        theme('natura-green', 'Natura Verde', 'Salud, nutrición, familias y pedagogía.', 'sprout', 'light', {
            'background': '#f4f7f0', 'surface': '#fffef9', 'surfaceSoft': '#f1f6ec', 'text': '#183428',
            'muted': '#61756a', 'primary': '#4e9a51', 'primaryHover': '#397d3d', 'accent': '#168b76', 'border': '#d8e5d4'}),
        theme('aurora-violet', 'Aurora Violeta', 'Innovación, Motor Documental e inteligencia artificial.', 'sparkles', 'dark', {
            'background': '#120a2d', 'surface': '#24104c', 'surfaceSoft': '#321360', 'text': '#faf6ff',
            'muted': '#c2b4da', 'primary': '#b832d8', 'primaryHover': '#9825b6', 'accent': '#6d5cff', 'border': '#482378'}),
        theme('warm-sand', 'Arena Cálida', 'Capacitación, docentes y trabajo comunitario.', 'sun', 'light', {
            'background': '#f6efe5', 'surface': '#fffaf2', 'surfaceSoft': '#f4e8d6', 'text': '#3c2d20',
            'muted': '#7d6b58', 'primary': '#b77825', 'primaryHover': '#965e19', 'accent': '#d09a4c', 'border': '#e5d3bb'}),
        theme('executive-premium', 'Ejecutivo Premium', 'Gerencia, presentaciones y reportes ejecutivos.', 'gem', 'dark', {
            'background': '#08090b', 'surface': '#111318', 'surfaceSoft': '#181b21', 'text': '#f7f3e9',
            'muted': '#aaa498', 'primary': '#d2aa45', 'primaryHover': '#b88f2e', 'accent': '#9f7b27', 'border': '#3c3421'}),
        theme('alto-contraste', 'Alto Contraste', 'Accesibilidad reforzada.', 'contrast', 'dark', {
            'background': '#000000', 'surface': '#0a0a0a', 'surfaceSoft': '#171717', 'text': '#ffffff',
            'muted': '#e5e7eb', 'primary': '#facc15', 'primaryHover': '#eab308', 'accent': '#22d3ee',
            'border': '#facc15', 'danger': '#fb7185'}, 'accesibilidad'),
    ]
