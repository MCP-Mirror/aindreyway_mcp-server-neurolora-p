"""Type stubs for appdirs package."""

def user_data_dir(
    appname: str,
    appauthor: str | None = None,
    version: str | None = None,
    roaming: bool = False,
) -> str:
    """Return full path to the user-specific data dir for this application."""
    ...

def user_config_dir(
    appname: str,
    appauthor: str | None = None,
    version: str | None = None,
    roaming: bool = False,
) -> str:
    """Return full path to the user-specific config dir for this application."""
    ...

def user_cache_dir(
    appname: str,
    appauthor: str | None = None,
    version: str | None = None,
) -> str:
    """Return full path to the user-specific cache dir for this application."""
    ...

def user_log_dir(
    appname: str,
    appauthor: str | None = None,
    version: str | None = None,
) -> str:
    """Return full path to the user-specific log dir for this application."""
    ...

def user_state_dir(
    appname: str,
    appauthor: str | None = None,
    version: str | None = None,
    roaming: bool = False,
) -> str:
    """Return full path to the user-specific state dir for this application."""
    ...

def site_data_dir(
    appname: str,
    appauthor: str | None = None,
    version: str | None = None,
    multipath: bool = False,
) -> str:
    """Return full path to the user-shared data dir for this application."""
    ...

def site_config_dir(
    appname: str,
    appauthor: str | None = None,
    version: str | None = None,
    multipath: bool = False,
) -> str:
    """Return full path to the user-shared config dir for this application."""
    ...
