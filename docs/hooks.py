"""Inclui figuras e tabelas canônicas no site sem duplicar arquivos de origem."""

from pathlib import Path

from mkdocs.structure.files import File


def on_files(files, config):
    root = Path(config.config_file_path).resolve().parent.parent
    for folder in ["figures", "tables"]:
        for path in sorted((root / "reports" / folder).rglob("*")):
            if path.is_file() and path.suffix in {".png", ".csv"}:
                relative = path.relative_to(root / "reports")
                files.append(
                    File.generated(config, f"assets/{relative.as_posix()}", abs_src_path=str(path))
                )
    return files


def on_page_markdown(markdown, page, config, files):
    # Keep source Markdown links valid in the repository while serving the same
    # canonical files under the site's assets directory.
    return markdown.replace("../../reports/", "../assets/")
