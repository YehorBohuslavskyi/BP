"""Source-fragment storage with stable file, kind, and byte-range identities."""
from pathlib import Path

class FragmentCatalog:
    """Store source fragments keyed by their original byte ranges."""
    def __init__(self, project_root: Path) -> None:
        """Anchor relative fragment filenames to the project root."""
        self.project_root = project_root.resolve()
        self.fragments: dict[str, dict] = {}

    def add(self, element, kind: str, name: str) -> str:
        """Register a Slither element once and return its stable fragment ID."""
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
        """Return a registered fragment or raise for an unknown ID."""
        if fragment_id not in self.fragments:
            raise ValueError(f"Fragment not found: {fragment_id}")
        
        return self.fragments[fragment_id]

    def to_dict(self) -> dict:
        """Return a shallow copy of the fragment lookup."""
        return self.fragments.copy()
