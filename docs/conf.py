project = "CWL-Airflow"
copyright = "2019, Michael Kotliar, Andrey Kartashov, Artem Barski"
author = "Michael Kotliar, Andrey Kartashov, Artem Barski"

extensions = ["recommonmark", "sphinx_markdown_tables", "sphinxcontrib.openapi"]
master_doc = "index"
html_theme = "sphinx_rtd_theme"

source_parsers = {
    '.md': CommonMarkParser,
}

source_suffix = ['.rst', '.md']