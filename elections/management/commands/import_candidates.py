"""
Import candidate financial totals from the FEC API (/candidates/totals/).

Usage:
    python manage.py import_candidates --cycle 2024 --office S --max-pages 3
    python manage.py import_candidates --cycle 2024 --state VA

Get a free API key at https://api.open.fec.gov/developers/ and put it in .env
as FEC_API_KEY. Re-running updates existing candidates (no duplicates).
"""

import time
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.management.base import BaseCommand

from elections.fec import fec_get
from elections.models import Candidate

PARTY_CODES = {"DEM", "REP", "LIB", "GRE", "IND"}


def to_decimal(value):
    try:
        return Decimal(str(value)) if value not in (None, "") else Decimal("0")
    except InvalidOperation:
        return Decimal("0")


def first_present(item, *keys, default=None):
    for key in keys:
        if item.get(key) not in (None, ""):
            return item[key]
    return default


class Command(BaseCommand):
    help = "Import candidate totals from the FEC API"

    def add_arguments(self, parser):
        parser.add_argument("--cycle", type=int, default=2024,
                            help="Election cycle (even year), default 2024")
        parser.add_argument("--office", choices=["P", "S", "H"],
                            help="P=President, S=Senate, H=House")
        parser.add_argument("--state", help="Two-letter state code, e.g. VA")
        parser.add_argument("--per-page", type=int, default=100,
                            help="Results per API page (max 100)")
        parser.add_argument("--max-pages", type=int, default=5,
                            help="Stop after this many pages (default 5)")

    def handle(self, *args, **options):
        if settings.FEC_API_KEY == "DEMO_KEY":
            self.stdout.write(self.style.WARNING(
                "Using DEMO_KEY (heavily rate limited). Get a free key at "
                "https://api.open.fec.gov/developers/ and set FEC_API_KEY in .env"
            ))

        cycle = options["cycle"]
        params = {
            "api_key": settings.FEC_API_KEY,
            "cycle": cycle,
            "per_page": min(options["per_page"], 100),
            "page": 1,
        }
        if options["office"]:
            params["office"] = options["office"]
        if options["state"]:
            params["state"] = options["state"].upper()

        created_count = updated_count = 0
        self.stdout.write(f"Importing candidates for the {cycle} cycle...")

        while params["page"] <= options["max_pages"]:
            data = fec_get("candidates/totals/", params)
            results = data.get("results", [])
            if not results:
                break

            for item in results:
                candidate_id = item.get("candidate_id")
                if not candidate_id:
                    continue

                party = (item.get("party") or "").upper()
                incumbent = first_present(
                    item, "incumbent_challenge", "incumbent_challenge_full", default=""
                )

                # One row per candidate per cycle, so importing 2026 never
                # overwrites the same candidate's 2024 numbers.
                _, created = Candidate.objects.update_or_create(
                    candidate_id=candidate_id,
                    election_year=cycle,
                    defaults={
                        "name": item.get("name") or item.get("candidate_name") or "Unknown",
                        "party": party if party in PARTY_CODES else "OTH",
                        "office": item.get("office") or "",
                        "state": item.get("state") or "",
                        "district": str(item.get("district") or ""),
                        "incumbent_challenge": incumbent[:1].upper(),
                        "status": item.get("candidate_status") or "",
                        "total_receipts": to_decimal(item.get("receipts")),
                        "total_disbursements": to_decimal(item.get("disbursements")),
                        "cash_on_hand": to_decimal(first_present(
                            item, "cash_on_hand_end_period",
                            "last_cash_on_hand_end_period",
                        )),
                        "total_individual_contributions": to_decimal(
                            item.get("individual_contributions")
                        ),
                    },
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

            total_pages = data.get("pagination", {}).get("pages", 1)
            self.stdout.write(f"  page {params['page']} of {total_pages} done")
            if params["page"] >= total_pages:
                break
            params["page"] += 1
            time.sleep(0.5)

        self.stdout.write(self.style.SUCCESS(
            f"Done. {created_count} new, {updated_count} updated candidates."
        ))
