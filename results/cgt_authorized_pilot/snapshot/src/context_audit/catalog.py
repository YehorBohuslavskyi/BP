from pathlib import Path

class FragmentCatalog:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.fragments: dict[str, dict] = {}

    def add(self, element, kind: str, name: str) -> str:
        mapping = element.source_mapping
        source_path = Path(mapping.filename.absolute).resolve()

        try:
            file_name = source_path.relative_to(self.project_root).as_posix()
        except ValueError:
            file_name = source_path.as_posix()

        fragment_id = (
            f"{file_name}:{kind}:"
            f"{mapping.start}:{mapping.length}"
        )

        if fragment_id not in self.fragments:
            self.fragments[fragment_id] = {
                "id": fragment_id,
                "kind": kind,
                "name": name,
                "file": file_name,
                "source": mapping.content
            }

        return fragment_id

    def get(self, fragment_id: str) -> dict:
        if fragment_id not in self.fragments:
            raise ValueError(f"Fragment not found: {fragment_id}")
        
        return self.fragments[fragment_id]

    def to_dict(self) -> dict:
        return self.fragments.copy()