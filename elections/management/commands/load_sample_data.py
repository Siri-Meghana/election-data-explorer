"""
Load FICTIONAL sample candidates so the app can be demoed without the FEC API.

    python manage.py load_sample_data
    python manage.py load_sample_data --clear   # remove sample rows only

All names are invented and IDs start with 'SAMPLE'. Do not present this as
real election data.
"""

import random
from decimal import Decimal

from django.core.management.base import BaseCommand

from elections.models import Candidate

STATES = ["VA", "MD", "CA", "TX", "NY", "FL", "OH", "WA"]
PARTIES = ["DEM", "REP", "DEM", "REP", "IND", "LIB", "GRE"]
OFFICES = ["S", "H", "H", "S", "P"]


class Command(BaseCommand):
    help = "Load fictional sample candidates (offline demo)"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true",
                            help="Delete sample rows and exit")

    def handle(self, *args, **options):
        Candidate.objects.filter(candidate_id__startswith="SAMPLE").delete()
        if options["clear"]:
            self.stdout.write(self.style.SUCCESS("Sample data removed."))
            return

        rng = random.Random(42)
        for i in range(1, 41):
            raised = Decimal(rng.randint(50_000, 9_000_000))
            spent = (raised * Decimal(rng.uniform(0.4, 0.95))).quantize(Decimal("1"))
            Candidate.objects.create(
                candidate_id=f"SAMPLE{i:03d}",
                name=f"SAMPLE, CANDIDATE {i:02d}",
                party=rng.choice(PARTIES),
                office=rng.choice(OFFICES),
                state=rng.choice(STATES),
                election_year=2024,
                total_receipts=raised,
                total_disbursements=spent,
                cash_on_hand=raised - spent,
                total_individual_contributions=(raised * Decimal("0.6")).quantize(Decimal("1")),
            )

        self.stdout.write(self.style.SUCCESS(
            f"Loaded {Candidate.objects.filter(candidate_id__startswith='SAMPLE').count()} "
            f"fictional candidates."
        ))
