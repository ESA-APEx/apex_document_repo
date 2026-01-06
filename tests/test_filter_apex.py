import json
from pathlib import Path
import importlib.util

# Load the module directly from its file path so tests work regardless of
# whether `scripts` is a package on sys.path.
spec = importlib.util.spec_from_file_location(
    "filter_apex",
    Path(__file__).resolve().parents[1] / "scripts" / "filter_apex.py",
)
fa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fa)


def test_get_project_themes():
    project = {
        "links": [
            {"href": "/themes/atmosphere/", "title": "Theme: Atmosphere"},
            {"href": "/themes/land/", "title": "Theme: Land"},
            {"href": "/other/", "title": "Not a theme"},
        ]
    }
    themes = fa.get_project_themes(project)
    assert set(themes) == {"atmosphere", "land"}


def test_add_project_themes_to_new_dict():
    themes = {}
    ref = {"id": "project-1", "title": "Project One"}
    project = {"links": [{"href": "/themes/atmosphere/", "title": "Theme: Atmosphere"}]}
    out = fa.add_project_themes_to_dict(themes, ref, project)
    assert "atmosphere" in out
    assert out["atmosphere"][0]["id"] == "project-1"


def test_add_project_themes_to_existing_dict():
    refs = [
        {"id": "project-1", "title": "Project One"},
        {"id": "project-existing", "title": "Project Existing"},
    ]
    themes = {"atmosphere": [refs[1]]}

    project = {"links": [{"href": "/themes/atmosphere/", "title": "Theme: Atmosphere"}]}
    out = fa.add_project_themes_to_dict(themes, refs[0], project)
    assert "atmosphere" in out
    assert out["atmosphere"][0]["id"] == "project-existing"


def test_write_project_collection_filters_links(tmp_path: Path):
    dest = tmp_path / "projects" / "project-1" / "collection.json"
    project = {
        "title": "P1",
        "links": [
            {"href": "/x", "title": "Experiment: something"},
            {"href": "/y"},
            {"href": "/z", "title": "Workflow: something else"},
        ],
    }
    fa.write_project_collection(dest, project)
    with open(dest) as f:
        data = json.load(f)
    # only the link without title should remain
    assert len(data["links"]) == 1
    assert data["links"][0]["href"] == "/y"


def test_recreate_dir(tmp_path: Path):
    d = tmp_path / "some_dir"
    d.mkdir()
    (d / "file").write_text("x")
    assert d.exists()
    fa.recreate_dir(d)
    assert d.exists()
    assert not any(d.iterdir())


def test_get_theme_links(tmp_path: Path):
    theme = {
        "links": [
            {"rel": "root", "href": "/"},
            {"rel": "related", "href": "/info", "title": "Info"},
        ]
    }
    projects = [{"id": "project-1", "title": "Project One"}]
    projects_target = tmp_path / "projects_target"
    links = fa.get_theme_links(theme, projects, projects_target)
    # should include the related link and one child link
    rels = [l.get("rel") for l in links]
    assert "related" in rels
    assert "child" in rels
    # child href should be under projects_target
    child = next(l for l in links if l["rel"] == "child")
    assert child["href"] == str(projects_target / "project-1" / "collection.json")


def test_get_catalogue_links():
    catalogue = {
        "links": [
            {"rel": "child", "title": "Themes"},
            {"rel": "child", "title": "Projects"},
            {"rel": "child", "title": "Something Else"},
            {"rel": "root"},
        ]
    }
    links = fa.get_catalogue_links(catalogue)
    titles = [l.get("title", "").lower() for l in links]
    assert "themes" in titles and "projects" in titles
    assert not any(l.get("title") == "Something Else" for l in links)


def test_build_full_catalogue(tmp_path: Path):
    # Setup projects source
    projects_source = tmp_path / "open-science-catalog-metadata" / "projects"
    projects_source.mkdir(parents=True)

    catalog = {
        "links": [
            {"rel": "root", "href": "/", "title": "root"},
            {
                "rel": "child",
                "href": "projects/project-1/collection.json",
                "title": "Project 1",
            },
            {
                "rel": "child",
                "href": "projects/project-2/collection.json",
                "title": "Project 2",
            },
        ]
    }
    write_path = projects_source / "catalog.json"
    write_path.write_text(json.dumps(catalog))

    # project 1: public license and references a theme
    p1_path = projects_source / "projects" / "project-1"
    p1_path.mkdir(parents=True)
    p1 = {
        "title": "P1",
        "license": "public",
        "links": [{"href": "/themes/atmosphere/", "title": "Theme: Atmosphere"}],
    }
    (p1_path / "collection.json").write_text(json.dumps(p1))

    # project 2: proprietary license -> should be filtered out
    p2_path = projects_source / "projects" / "project-2"
    p2_path.mkdir(parents=True)
    p2 = {"title": "P2", "license": "proprietary", "links": []}
    (p2_path / "collection.json").write_text(json.dumps(p2))
    
    # build the projects
    projects_target = tmp_path / "projects_target"
    filtered_refs, themes, filtered_catalogue = fa.build_projects(
        projects_source, projects_target, license_to_keep="proprietary"
    )

    # project-1 should be included
    assert "projects/project-1/collection.json" in filtered_refs
    assert "project-2" not in " ".join(filtered_refs)

    # verify written project file
    assert (projects_target / "projects" / "project-1" / "collection.json").exists()

    # setup themes source and build themes
    themes_source = tmp_path / "open-science-catalog-metadata" / "themes"
    atmosphere = themes_source / "atmosphere"
    atmosphere.mkdir(parents=True)
    theme_catalog = {"links": [{"rel": "root", "href": "/"}], "title": "Atmosphere"}
    (atmosphere / "catalog.json").write_text(json.dumps(theme_catalog))

    # build the themes
    themes_target = tmp_path / "themes_target"
    fa.build_themes(themes, themes_source, themes_target, projects_target)

    # Check that theme was copied and updated
    dest_theme_catalog = themes_target / "atmosphere" / "catalog.json"
    assert dest_theme_catalog.exists()
    data = json.loads(dest_theme_catalog.read_text())
    # Links should include a child to project-1
    assert any(l.get("rel") == "child" for l in data.get("links", []))

    # Build main catalogue
    cat_source = tmp_path / "open-science-catalog-metadata" / "catalog.json"
    main_catalog = {
        "links": [{"rel": "child", "title": "Themes"}, {"rel": "other"}],
        "title": "Orig",
    }
    cat_source.parent.mkdir(parents=True, exist_ok=True)
    cat_source.write_text(json.dumps(main_catalog))

    catalogue_target = tmp_path / "catalogue.json"
    fa.build_main_catalogue(cat_source, catalogue_target)
    result = json.loads(catalogue_target.read_text())
    assert result["title"] == "APEx Documentation Repository"
    assert all(
        l.get("rel") != "child" or l.get("title", "").lower() in ["themes", "projects"]
        for l in result["links"]
    )
