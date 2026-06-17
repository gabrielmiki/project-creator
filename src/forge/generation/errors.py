from forge.infrastructure import GenerationTransaction as _  # noqa: F401


class DirectoryNotEmptyError(Exception):
    """Raised when output_dir exists and is non-empty."""


class MissingDependencyError(Exception):
    """Raised when a plugin has a requires dependency not in the selected plugin set."""
