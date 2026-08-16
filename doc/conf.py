"""Sphinx configuration for Mini2FA documentation."""

project = 'Mini2FA'
copyright = '2026, Mini2FA Contributors'
author = 'Mini2FA Contributors'

extensions = [
    'myst_parser',
]

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

master_doc = 'index'
exclude_patterns = ['_build']
html_theme = 'sphinx_rtd_theme'
