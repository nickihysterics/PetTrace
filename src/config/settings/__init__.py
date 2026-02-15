import os

_env = os.getenv("DJANGO_ENV", "local").strip().lower()

if _env == "production":
    from .production import *  # noqa: F403
elif _env == "test":
    from .test import *  # noqa: F403
else:
    from .local import *  # noqa: F403
