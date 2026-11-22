"""
Tests for the Election Data Explorer.

Run with: python manage.py test elections
The FEC API is always mocked, so no network access or API key is needed.
"""

from decimal import Decimal
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from .models import Candidate


def fake_response(payload, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.ok = status < 400
    resp.json.return_value = payload
    resp.text = str(payload)
    return resp


class CandidateModelTest(TestCase):
    def setUp(self):
        self.candidate = Candidate.objects.create(
            candidate_id="P00000001", name="TEST CANDIDATE", party="DEM",
            office="P", state="VA", election_year=2024,
            total_receipts=Decimal("1000000.00"),
            total_disbursements=Decimal("750000.00"),
            cash_on_hand=Decimal("250000.00"),
        )

    def test_str_representation(self):
        self.assertIn("TEST CANDIDATE", str(self.candidate))
        self.assertIn("Democratic", str(self.candidate))

    def test_burn_rate_calculation(self):
        self.assertEqual(self.candidate.burn_rate, 75.0)

    def test_burn_rate_zero_receipts(self):
        c = Candidate.objects.create(candidate_id="P00000002", name="ZERO",
                                     party="REP", office="S", election_year=2024)
        self.assertEqual(c.burn_rate, 0)

    def test_same_candidate_cannot_have_two_rows_in_one_cycle(self):
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError), transaction.atomic():
            Candidate.objects.create(candidate_id="P00000001", name="DUP",
                                     party="DEM", office="P", election_year=2024)


class DashboardViewTest(TestCase):
    def setUp(self):
        Candidate.objects.create(
            candidate_id="S00000001", name="SENATE CANDIDATE", party="REP",
            office="S", state="TX", election_year=2024,
            total_receipts=Decimal("500000.00"),
            total_disbursements=Decimal("300000.00"))
        Candidate.objects.create(
            candidate_id="H00000001", name="HOUSE CANDIDATE", party="DEM",
            office="H", state="CA", election_year=2024,
            total_receipts=Decimal("200000.00"),
            total_disbursements=Decimal("150000.00"))

    def test_dashboard_loads_with_data(self):
        response = self.client.get(reverse("elections:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Election Data Dashboard")
        self.assertContains(response, "SENATE CANDIDATE")

    def test_dashboard_cycle_filter_with_no_data(self):
        response = self.client.get(reverse("elections:dashboard") + "?cycle=2022")
        self.assertEqual(response.status_code, 200)

    def test_navigation_only_has_dashboard_and_candidates(self):
        html = self.client.get(reverse("elections:dashboard")).content.decode()
        self.assertIn("Candidates", html)
        self.assertNotIn(">Contributions<", html)
        self.assertNotIn(">API<", html)

    def test_removed_pages_return_404(self):
        self.assertEqual(self.client.get("/contributions/").status_code, 404)
        self.assertEqual(self.client.get("/api/").status_code, 404)


class CandidateListViewTest(TestCase):
    def setUp(self):
        Candidate.objects.create(
            candidate_id="P00000010", name="ALICE DEMOCRAT", party="DEM",
            office="P", state="NY", election_year=2024,
            total_receipts=Decimal("5000000.00"))
        Candidate.objects.create(
            candidate_id="P00000011", name="BOB REPUBLICAN", party="REP",
            office="P", state="FL", election_year=2022,
            total_receipts=Decimal("4000000.00"))

    def get(self, query=""):
        return self.client.get(reverse("elections:candidate_list") + query)

    def test_list_loads(self):
        response = self.get()
        self.assertContains(response, "ALICE DEMOCRAT")
        self.assertContains(response, "BOB REPUBLICAN")

    def test_search_by_name(self):
        response = self.get("?q=ALICE")
        self.assertContains(response, "ALICE DEMOCRAT")
        self.assertNotContains(response, "BOB REPUBLICAN")

    def test_filter_by_party(self):
        response = self.get("?party=DEM")
        self.assertContains(response, "ALICE DEMOCRAT")
        self.assertNotContains(response, "BOB REPUBLICAN")

    def test_filter_by_state(self):
        response = self.get("?state=fl")
        self.assertNotContains(response, "ALICE DEMOCRAT")
        self.assertContains(response, "BOB REPUBLICAN")

    def test_filter_by_cycle(self):
        response = self.get("?cycle=2022")
        self.assertNotContains(response, "ALICE DEMOCRAT")
        self.assertContains(response, "BOB REPUBLICAN")

    def test_bad_cycle_value_does_not_crash(self):
        self.assertEqual(self.get("?cycle=abc").status_code, 200)


class CandidateDetailViewTest(TestCase):
    def setUp(self):
        for year, raised in ((2024, "103000000"), (2026, "5000000")):
            Candidate.objects.create(
                candidate_id="S6TEST001", name="TWICE, CANDIDATE", party="DEM",
                office="S", state="OH", election_year=year,
                total_receipts=Decimal(raised),
                total_disbursements=Decimal("1000"))
        self.url = reverse("elections:candidate_detail", args=["S6TEST001"])

    def test_defaults_to_latest_cycle(self):
        self.assertContains(self.client.get(self.url), "2026 Cycle")

    def test_cycle_parameter_selects_a_cycle(self):
        self.assertContains(self.client.get(self.url + "?cycle=2024"), "2024 Cycle")

    def test_shows_all_cycles_table(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Fundraising by Election Cycle")
        self.assertContains(response, "?cycle=2024")

    def test_unknown_cycle_or_id_is_404(self):
        self.assertEqual(self.client.get(self.url + "?cycle=1999").status_code, 404)
        missing = reverse("elections:candidate_detail", args=["X99999999"])
        self.assertEqual(self.client.get(missing).status_code, 404)


class ImportCandidatesTest(TestCase):
    payload = {
        "results": [
            {"candidate_id": "S0TEST001", "name": "TEST, ONE", "party": "DEM",
             "office": "S", "state": "VA", "district": "00",
             "incumbent_challenge": "I", "election_year": 2024,
             "receipts": 1500000.5, "disbursements": 900000,
             "cash_on_hand_end_period": 600000.5,
             "individual_contributions": 1000000},
            {"candidate_id": "H0TEST002", "name": "TEST, TWO", "party": "GRN",
             "office": "H", "state": "MD", "receipts": None,
             "disbursements": None},
        ],
        "pagination": {"pages": 1, "count": 2},
    }

    @patch("elections.fec.requests.get")
    def test_import_creates_and_updates(self, mock_get):
        mock_get.return_value = fake_response(self.payload)
        call_command("import_candidates", "--cycle", "2024", stdout=StringIO())
        self.assertEqual(Candidate.objects.count(), 2)
        one = Candidate.objects.get(candidate_id="S0TEST001")
        self.assertEqual(one.party, "DEM")
        self.assertEqual(one.cash_on_hand, Decimal("600000.5"))
        self.assertEqual(one.incumbent_challenge, "I")
        two = Candidate.objects.get(candidate_id="H0TEST002")
        self.assertEqual(two.party, "OTH")      # unknown party code
        self.assertEqual(two.total_receipts, 0)  # null money values
        call_command("import_candidates", "--cycle", "2024", stdout=StringIO())
        self.assertEqual(Candidate.objects.count(), 2)  # no duplicates

    @patch("elections.fec.requests.get")
    def test_api_error_shows_message(self, mock_get):
        mock_get.return_value = fake_response({"error": "bad param"}, status=422)
        with self.assertRaises(CommandError) as ctx:
            call_command("import_candidates", stdout=StringIO())
        self.assertIn("422", str(ctx.exception))

    @patch("elections.fec.requests.get")
    def test_rate_limit_message(self, mock_get):
        mock_get.return_value = fake_response({}, status=429)
        with self.assertRaises(CommandError) as ctx:
            call_command("import_candidates", stdout=StringIO())
        self.assertIn("rate limit", str(ctx.exception).lower())

    @patch("elections.management.commands.import_candidates.time.sleep")
    @patch("elections.fec.requests.get")
    def test_follows_pages(self, mock_get, _sleep):
        def page(n):
            return fake_response({
                "results": [{"candidate_id": f"S0PAGE00{n}", "name": f"PAGE {n}",
                             "party": "DEM", "office": "S"}],
                "pagination": {"pages": 2}})
        mock_get.side_effect = [page(1), page(2)]
        call_command("import_candidates", "--cycle", "2024", stdout=StringIO())
        self.assertEqual(Candidate.objects.count(), 2)
        self.assertEqual(mock_get.call_args_list[1].kwargs["params"]["page"], 2)

    @patch("elections.fec.requests.get")
    def test_second_cycle_does_not_overwrite_first(self, mock_get):
        def payload(receipts):
            return fake_response({"results": [{
                "candidate_id": "S6TEST001", "name": "TWICE, CANDIDATE",
                "party": "DEM", "office": "S", "state": "OH",
                "receipts": receipts}], "pagination": {"pages": 1}})
        mock_get.return_value = payload(103000000)
        call_command("import_candidates", "--cycle", "2024", stdout=StringIO())
        mock_get.return_value = payload(5000000)
        call_command("import_candidates", "--cycle", "2026", stdout=StringIO())
        rows = {c.election_year: int(c.total_receipts) for c in Candidate.objects.all()}
        self.assertEqual(rows, {2024: 103000000, 2026: 5000000})
        mock_get.return_value = payload(6000000)
        call_command("import_candidates", "--cycle", "2026", stdout=StringIO())
        self.assertEqual(Candidate.objects.count(), 2)


class FecRetryTest(TestCase):
    ok = {"results": [{"candidate_id": "S0RETRY01", "name": "RETRY, OK",
                       "party": "DEM", "office": "S"}],
          "pagination": {"pages": 1}}

    @patch("elections.fec.time.sleep")
    @patch("elections.fec.requests.get")
    def test_retries_after_timeouts_then_succeeds(self, mock_get, _sleep):
        mock_get.side_effect = [
            fake_response({"message": "Query timed out"}, status=504),
            fake_response({"message": "Query timed out"}, status=504),
            fake_response(self.ok),
        ]
        call_command("import_candidates", "--cycle", "2024", stdout=StringIO())
        self.assertEqual(mock_get.call_count, 3)
        self.assertTrue(Candidate.objects.filter(candidate_id="S0RETRY01").exists())

    @patch("elections.fec.time.sleep")
    @patch("elections.fec.requests.get")
    def test_gives_up_with_helpful_message(self, mock_get, _sleep):
        mock_get.return_value = fake_response({"message": "Query timed out"}, status=504)
        with self.assertRaises(CommandError) as ctx:
            call_command("import_candidates", stdout=StringIO())
        self.assertEqual(mock_get.call_count, 4)
        self.assertIn("timed out", str(ctx.exception))


class SampleDataTest(TestCase):
    def test_load_and_clear(self):
        call_command("load_sample_data", stdout=StringIO())
        self.assertEqual(
            Candidate.objects.filter(candidate_id__startswith="SAMPLE").count(), 40)
        call_command("load_sample_data", "--clear", stdout=StringIO())
        self.assertEqual(Candidate.objects.count(), 0)
