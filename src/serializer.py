import json
import os
import tempfile
from dataclasses import asdict

from src.errors import ProjectLoadError
from src.models import Project

REQUIRED_FIELDS = ("name", "version")


class Serializer:
    def save(self, project: Project, path: str) -> None:
        """Write project to JSON atomically (temp file → replace)."""
        data = asdict(project)
        dir_name = os.path.dirname(os.path.abspath(path))
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def load(self, path: str) -> Project:
        """Read and validate a project JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ProjectLoadError(f"Invalid JSON: {e}") from e

        for field in REQUIRED_FIELDS:
            if field not in data:
                raise ProjectLoadError(f"Missing required field: '{field}'")

        return Project(name=data["name"], version=data["version"])
