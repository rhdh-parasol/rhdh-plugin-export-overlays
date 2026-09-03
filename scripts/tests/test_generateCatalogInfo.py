"""Tests for generateCatalogInfo.py."""

from generateCatalogInfo import (
    ANNOTATION_OVERLAY_WORKSPACE,
    ANNOTATION_PACKAGE_REFS,
    ANNOTATION_PLUGIN_REFS,
    ANNOTATION_SOURCE_REPOSITORY,
    ANNOTATION_SOURCE_REVISION,
    DEFAULT_OVERLAY_SLUG,
    RHDH_PLUGINS_COMPONENT_BY_WORKSPACE,
    ROOT_COMPONENT_NAME,
    build_root_entity,
    build_workspace_entity,
    check_files,
    dump_entity,
    extension_refs,
    is_rhdh_plugins_source,
    overlay_entity_name,
    overlay_tree_url,
    planned_files,
    rhdh_plugins_depends_on,
    source_tree_url,
    write_files,
)


RHDH_PLUGINS_SOURCE = {
    "repo": "https://github.com/redhat-developer/rhdh-plugins",
    "repo-ref": "97a6e3a7c468a7624b62f957fc7c077127bf51c6",
    "repo-flat": False,
    "repo-backstage-version": "1.52.0",
}

COMMUNITY_SOURCE = {
    "repo": "https://github.com/backstage/community-plugins",
    "repo-ref": "0e830be044ca334c5304b541e4757b621eb1e6db",
    "repo-flat": False,
    "repo-backstage-version": "1.52.0",
}

FLAT_SOURCE = {
    "repo": "https://github.com/backstage/backstage",
    "repo-ref": "v1.52.0",
    "repo-flat": True,
    "repo-backstage-version": "1.52.0",
}


def test_overlay_entity_name():
    assert overlay_entity_name("bulk-import") == "overlay-bulk-import"


def test_is_rhdh_plugins_source():
    assert is_rhdh_plugins_source(RHDH_PLUGINS_SOURCE["repo"])
    assert not is_rhdh_plugins_source(COMMUNITY_SOURCE["repo"])


def test_source_tree_url_nested():
    assert source_tree_url(RHDH_PLUGINS_SOURCE, "bulk-import") == (
        "https://github.com/redhat-developer/rhdh-plugins/tree/"
        "97a6e3a7c468a7624b62f957fc7c077127bf51c6/workspaces/bulk-import"
    )


def test_source_tree_url_flat():
    assert source_tree_url(FLAT_SOURCE, "backstage") == (
        "https://github.com/backstage/backstage/tree/v1.52.0"
    )


def test_overlay_tree_url():
    assert overlay_tree_url(DEFAULT_OVERLAY_SLUG, "bulk-import") == (
        "https://github.com/rhdh-parasol/rhdh-plugin-export-overlays/tree/"
        "main/workspaces/bulk-import"
    )


def test_depends_on_only_for_known_rhdh_plugins_workspaces():
    assert rhdh_plugins_depends_on("bulk-import") == (
        "red-hat-developer-hub-bulk-import"
    )
    assert rhdh_plugins_depends_on("konflux") is None
    assert rhdh_plugins_depends_on("github") is None
    assert "konflux" not in RHDH_PLUGINS_COMPONENT_BY_WORKSPACE


def test_workspace_entity_rhdh_plugins_has_depends_on():
    entity = build_workspace_entity(
        "bulk-import",
        RHDH_PLUGINS_SOURCE,
        ["plugins/bulk-import", "plugins/bulk-import-backend"],
        DEFAULT_OVERLAY_SLUG,
    )
    assert entity["metadata"]["name"] == "overlay-bulk-import"
    assert entity["spec"]["type"] == "rhdh-overlay-workspace"
    assert entity["spec"]["subcomponentOf"] == f"component:default/{ROOT_COMPONENT_NAME}"
    assert entity["spec"]["dependsOn"] == [
        "component:default/red-hat-developer-hub-bulk-import"
    ]
    assert (
        entity["metadata"]["annotations"]["github.com/project-slug"]
        == DEFAULT_OVERLAY_SLUG
    )


def test_workspace_entity_includes_lifecycle_annotations():
    entity = build_workspace_entity(
        "adoption-insights",
        RHDH_PLUGINS_SOURCE,
        ["plugins/adoption-insights"],
        DEFAULT_OVERLAY_SLUG,
        ["plugin:rhdh/adoption-insights"],
        [
            "package:rhdh/rhdh-bsp-adoption-insights",
            "package:rhdh/rhdh-bsp-adoption-insights-backend",
        ],
    )
    annotations = entity["metadata"]["annotations"]
    assert annotations[ANNOTATION_OVERLAY_WORKSPACE] == "adoption-insights"
    assert annotations[ANNOTATION_SOURCE_REPOSITORY] == RHDH_PLUGINS_SOURCE["repo"]
    assert annotations[ANNOTATION_SOURCE_REVISION] == RHDH_PLUGINS_SOURCE["repo-ref"]
    assert annotations[ANNOTATION_PLUGIN_REFS] == "plugin:rhdh/adoption-insights"
    assert annotations[ANNOTATION_PACKAGE_REFS] == (
        "package:rhdh/rhdh-bsp-adoption-insights, "
        "package:rhdh/rhdh-bsp-adoption-insights-backend"
    )


def test_workspace_entity_community_has_no_depends_on():
    entity = build_workspace_entity(
        "github",
        COMMUNITY_SOURCE,
        ["plugins/github-actions"],
        DEFAULT_OVERLAY_SLUG,
    )
    assert "dependsOn" not in entity["spec"]
    assert entity["metadata"]["name"] == "overlay-github"


def test_extension_refs_are_derived_and_verified(tmp_path):
    plugin_dir = tmp_path / "catalog-entities" / "extensions" / "plugins"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "adoption-insights.yaml").write_text(
        """
apiVersion: extensions.backstage.io/v1alpha1
kind: Plugin
metadata:
  name: adoption-insights
  namespace: rhdh
spec:
  packages:
    - rhdh-bsp-adoption-insights
    - rhdh-bsp-adoption-insights-backend
""",
        encoding="utf-8",
    )
    metadata_dir = tmp_path / "workspaces" / "adoption-insights" / "metadata"
    metadata_dir.mkdir(parents=True)
    for name in ("rhdh-bsp-adoption-insights", "rhdh-bsp-adoption-insights-backend"):
        (metadata_dir / f"{name}.yaml").write_text(
            f"""
apiVersion: extensions.backstage.io/v1alpha1
kind: Package
metadata:
  name: {name}
  namespace: rhdh
spec:
  partOf:
    - adoption-insights
""",
            encoding="utf-8",
        )

    plugin_refs, package_refs = extension_refs(
        tmp_path, tmp_path / "workspaces" / "adoption-insights"
    )

    assert plugin_refs == ["plugin:rhdh/adoption-insights"]
    assert package_refs == [
        "package:rhdh/rhdh-bsp-adoption-insights",
        "package:rhdh/rhdh-bsp-adoption-insights-backend",
    ]


def test_extension_refs_omit_plugin_with_unexpected_package(tmp_path):
    plugin_dir = tmp_path / "catalog-entities" / "extensions" / "plugins"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "sample.yaml").write_text(
        """
kind: Plugin
metadata:
  name: sample
  namespace: rhdh
spec:
  packages:
    - expected-package
""",
        encoding="utf-8",
    )
    metadata_dir = tmp_path / "workspaces" / "sample" / "metadata"
    metadata_dir.mkdir(parents=True)
    (metadata_dir / "unexpected.yaml").write_text(
        """
kind: Package
metadata:
  name: unexpected-package
  namespace: rhdh
spec:
  partOf:
    - sample
""",
        encoding="utf-8",
    )

    plugin_refs, package_refs = extension_refs(
        tmp_path, tmp_path / "workspaces" / "sample"
    )

    assert plugin_refs == []
    assert package_refs == ["package:rhdh/unexpected-package"]


def test_workspace_entity_unmapped_rhdh_plugins_has_no_depends_on():
    entity = build_workspace_entity(
        "konflux",
        RHDH_PLUGINS_SOURCE,
        ["plugins/konflux", "plugins/konflux-backend"],
        DEFAULT_OVERLAY_SLUG,
    )
    assert "dependsOn" not in entity["spec"]


def test_root_entity():
    entity = build_root_entity(DEFAULT_OVERLAY_SLUG, 65)
    assert entity["metadata"]["name"] == ROOT_COMPONENT_NAME
    assert entity["spec"]["type"] == "repository"
    assert "65 overlay workspaces" in entity["metadata"]["description"]


def test_dump_entity_has_generator_header():
    rendered = dump_entity(build_root_entity(DEFAULT_OVERLAY_SLUG, 1))
    assert rendered.startswith("# Generated by scripts/generateCatalogInfo.py")
    assert "apiVersion: backstage.io/v1alpha1" in rendered


def test_planned_files_and_check(tmp_path):
    ws = tmp_path / "workspaces" / "bulk-import"
    ws.mkdir(parents=True)
    (ws / "source.json").write_text(
        '{"repo":"https://github.com/redhat-developer/rhdh-plugins",'
        '"repo-ref":"abc1234","repo-flat":false}\n',
        encoding="utf-8",
    )
    (ws / "plugins-list.yaml").write_text(
        "plugins/bulk-import:\nplugins/bulk-import-backend:\n",
        encoding="utf-8",
    )
    obsolete = tmp_path / "workspaces" / "obsolete" / "catalog-info.yaml"
    obsolete.parent.mkdir(parents=True)
    obsolete.write_text(
        "# Generated by scripts/generateCatalogInfo.py. Do not edit by hand.\n"
        "# Re-run: python3 scripts/generateCatalogInfo.py\n"
        "stale\n",
        encoding="utf-8",
    )

    files = planned_files(tmp_path, DEFAULT_OVERLAY_SLUG)
    paths = [path for path, _ in files]
    assert tmp_path / "catalog-info.yaml" in paths
    assert ws / "catalog-info.yaml" in paths
    assert check_files(files) == 1

    write_files(files, dry_run=False, repo_root=tmp_path)
    assert check_files(files) == 0
    assert not obsolete.exists()

    (ws / "catalog-info.yaml").write_text("stale\n", encoding="utf-8")
    assert check_files(files) == 1
