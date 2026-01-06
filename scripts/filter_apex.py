"""Filter and build an APEx documentation subset from a source metadata tree.

This module exposes small, testable functions for working with the
open-science-catalog-metadata layout and a `main()` entrypoint that
performs the file-system operations.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

LICENSE_TO_KEEP = "proprietary"


# --- Small helpers -------------------------------------------------


def recreate_dir(path: Path) -> None:
    """Remove and recreate a directory.

    The function is idempotent and guarantees the path exists and is empty
    on return.
    """
    logging.debug("Recreating dir: %s", str(path))
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Dict:
    logging.debug("Reading file %s", str(path))
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data: Dict) -> None:
    logging.debug("Writing file %s", str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


# --- Core ----------------------------------


def write_project_collection(dest: Path, project: Dict) -> None:
    """Write a project's collection.json filtering out experiment/workflow links."""
    filtered_links = [
        link
        for link in project.get("links", [])
        if "title" not in link
        or (
            "experiment: " not in link["title"].lower()
            and "workflow: " not in link["title"].lower()
        )
    ]
    project = dict(project)  # shallow copy to avoid mutating caller's data
    project["links"] = filtered_links
    write_json(dest, project)


def get_project_themes(project: Dict) -> List[str]:
    """Extract theme ids mentioned in a project links list."""
    return [
        link["href"].split("/themes/")[1].split("/")[0]
        for link in project.get("links", [])
        if "title" in link and "theme: " in link["title"].lower()
    ]


def add_project_themes_to_dict(
    themes: Dict[str, List[Dict]], ref: Dict, project: Dict
) -> Dict[str, List[Dict]]:
    """Add a project ref to all themes referenced by the project."""
    p_themes = get_project_themes(project)
    for theme in p_themes:
        themes.setdefault(theme, []).append(ref)
    return themes


def get_theme_links(
    theme: Dict, projects: List[Dict]
) -> List[Dict]:
    """Build the links for a theme catalogue by appending child project links."""
    links = [
        link
        for link in theme.get("links", [])
        if link.get("rel") not in ("root", "child")
    ]
    for project in projects:
        links.append(
            {
                "rel": "child",
                "href": str(
                    Path("../..") / "projects" / project["id"] / "collection.json"
                ),
                "title": project["title"],
            }
        )
    return links


def get_catalogue_links(catalogue: Dict) -> List[Dict]:
    """Return catalogue links, keeping only top-level children for themes/projects."""
    return [
        link
        for link in catalogue.get("links", [])
        if link.get("rel") != "child"
        or link.get("title", "").lower() in ["themes", "projects"]
    ]


def build_projects(
    projects_source: Path,
    target: Path,
    license_to_keep: str = LICENSE_TO_KEEP, # @TODO - Remove this!
) -> Tuple[List[str], Dict[str, List[Dict]], Dict]:
    """Build project collections by filtering based on the APEx condition
    and copy them to the target directory.

    Returns a tuple of (filtered_refs, themes, filtered_catalogue_dict).
    """
    recreate_dir(target / "projects")

    catalog_path = projects_source / "catalog.json"
    catalog = load_json(catalog_path)

    filtered_refs: List[str] = []
    themes: Dict[str, List[Dict]] = {}

    for project in [p for p in catalog.get("links", []) if p.get("rel") == "child"]:
        project_id = project["href"].split("/")[1]
        collection = projects_source / project["href"]

        if not collection.exists():
            logger.warning("Missing project collection: %s", collection)
            continue

        data = load_json(collection)

        # @TODO - Update condition for filtering on APEx projects!
        if data.get("license", "").lower() != license_to_keep:
            logging.debug("Copying project: %s", project_id)
            filtered_refs.append(project["href"])
            dest = target / "projects" / project["href"]
            write_project_collection(dest, data)
            themes = add_project_themes_to_dict(
                themes, {"id": project_id, "title": data["title"]}, data
            )
        else:
            logging.debug("Skipping project: %s", project_id)

    # Build filtered catalogue
    filtered_catalogue = dict(catalog)
    filtered_catalogue["links"] = [
        link
        for link in catalog.get("links", [])
        if link.get("rel") not in ["root"] and link.get("href") in filtered_refs
    ]

    write_json(target / "projects" / "catalog.json", filtered_catalogue)

    return filtered_refs, themes, filtered_catalogue


def build_themes(
    themes: Dict[str, List[Dict]],
    themes_source: Path,
    target: Path,
) -> None:

    themes_target = target / "themes"
    recreate_dir(themes_target)

    catalog_path = themes_source / "catalog.json"
    catalog = load_json(catalog_path)

    for theme_id, projects in themes.items():
        logging.debug("Copying theme: %s", theme_id)
        source = themes_source / theme_id
        dest = themes_target / theme_id
        shutil.copytree(source, dest)

        theme = load_json(dest / "catalog.json")
        theme["links"] = get_theme_links(theme, projects)
        write_json(dest / "catalog.json", theme)

    # Build filtered catalogue
    filtered_catalogue = dict(catalog)
    filtered_catalogue["links"] = [
        link
        for link in catalog.get("links", [])
        if link.get("rel") not in ["root"]
        and link.get("href").split("/")[1] in themes.keys()
    ]

    write_json(themes_target / "catalog.json", filtered_catalogue)


def build_main_catalogue(catalogue_source: Path, target: Path) -> None:
    catalogue_target = target / "catalog.json"
    logging.debug("Building the main catalog.json file")
    catalogue = load_json(catalogue_source)
    catalogue["title"] = "APEx Documentation Repository"
    catalogue["links"] = get_catalogue_links(catalogue)
    write_json(catalogue_target, catalogue)


# --- Main Entrypoint ------------------------------------------------


def main(
    *,
    source_base: Path = Path("open-science-catalog-metadata"),
    target_base: Path = Path("catalog"),
    license_to_keep: str = LICENSE_TO_KEEP,
) -> None:

    recreate_dir(target_base)
    
    filtered_refs, themes, _ = build_projects(
        source_base / "projects", target_base, license_to_keep
    )
    build_themes(themes, source_base / "themes", target_base)
    build_main_catalogue(source_base / "catalog.json", target_base)

    logging.info(
        "Copied %i projects and %i themes", len(filtered_refs), len(themes.keys())
    )


if __name__ == "__main__":
    main()
