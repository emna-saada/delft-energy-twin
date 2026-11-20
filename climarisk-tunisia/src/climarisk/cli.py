"""Command line: ``climarisk run`` / ``climarisk portfolio`` / ``climarisk report`` / ``climarisk maps``."""
from __future__ import annotations

import argparse
import json


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="climarisk", description="ClimaRisk Tunisie pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("portfolio", help="generate the synthetic portfolio")
    r = sub.add_parser("run", help="full pipeline -> outputs/kpis.json")
    r.add_argument("--scenario", choices=["ssp245", "ssp585"], default=None,
                   help="print the KPIs of one scenario after the run")
    r.add_argument("--horizon", choices=["2030", "2050"], default="2050")
    sub.add_parser("maps", help="render PNG hazard maps")
    sub.add_parser("report", help="render the PDF report")
    args = ap.parse_args(argv)

    if args.cmd == "portfolio":
        from .portfolio import main as m
        m()
    elif args.cmd == "run":
        from .pipeline import run
        k = run()
        key = f"{args.scenario}_{args.horizon}" if args.scenario else None
        print(json.dumps(k["periods"][key] if key else k["periods"], indent=2, default=float))
    elif args.cmd == "maps":
        from .maps import render_all
        render_all()
    elif args.cmd == "report":
        from .reporting import build_report
        print(build_report())


if __name__ == "__main__":
    main()
