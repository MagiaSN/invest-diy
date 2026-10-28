"""invest-diy: self-hosted market dashboards built on public data.

Each tool is a sub-package of investdiy/ that declares a TOOL dict in its __init__.py and has a web/
folder with its pages. investdiy/server.py discovers the tools and mounts each one at /<slug>/.
Shared code lives in investdiy/common/ (Python) and investdiy/web/static/ (front end).
"""
