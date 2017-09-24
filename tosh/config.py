"""Read yaml configuration files."""
import yaml


class Config:
    """Configuration file reader."""

    def __init__(self, fh):
        """Initialize the configuration from a file handle."""
        self._config = yaml.load(fh)
        fh.close()

    def get(self, *args):
        """Get a key from a path given as multiple strings from the config file."""
        value = self._config
        for segment in args:
            if value is None:
                return None
            value = value.get(segment)
        return value
