from __future__ import annotations

import uvicorn

from quantforge.config.settings import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "quantforge.dashboard.api:app",
        host=settings.dashboard_api_host,
        port=settings.dashboard_api_port,
        reload=False,
    )


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
