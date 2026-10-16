# Releasing

No package publication or release workflow is configured yet. The package version is `0.1.0a1`; the changelog remains Unreleased. A GitHub repository does not imply a PyPI package has been reserved or published.

Before releasing:

1. Run tests, lint, format, schema regeneration, and a clean wheel build.
2. Install the wheel in a clean environment and exercise CSV/XLSX discovery → review → export.
3. Review dependencies/notices and inspect distribution contents for private or generated files.
4. Update the package version in both `pyproject.toml` and `src/atlasweave/__init__.py`; explain compatibility in the changelog.
5. Document that engine changes require rediscovery; bump schema versions separately for incompatible document changes.
6. Confirm support/security contact settings and known limitations.
7. Create a reviewed release tag and notes; configure trusted publishing only when distribution is intended.

Keep prior tags and artifacts available. If a release is broken, publish corrected notes and a patch release; do not silently replace tagged artifacts. Saved projects are not migrated automatically.
