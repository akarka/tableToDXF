"""Masaüstü UI (F-003, ADR-004).

Bu paket çekirdeğin (`tabletodxf.api`, `tabletodxf.config`, `tabletodxf.ods_reader`)
**üstünde** durur, asla altında: çekirdek modüller bu paketi hiç içe aktarmaz,
`tkinter` görmez. Suite, çekirdeği bu paket hiç kurulu olmadan kullanabilir.

    tabletodxf-ui              (kurulumdan sonra)
    python -m tabletodxf.ui    (kurulum olmadan)
"""

from __future__ import annotations


def main() -> int:
    from .app import run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
