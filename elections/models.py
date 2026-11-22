"""
Data models for FEC election data.

Models represent candidates, committees (PACs, campaign committees),
and financial contributions — the core entities in campaign finance data.
"""

from django.db import models


class Candidate(models.Model):
    """A candidate for federal office (President, Senate, House)."""

    OFFICE_CHOICES = [
        ("P", "President"),
        ("S", "Senate"),
        ("H", "House"),
    ]

    PARTY_CHOICES = [
        ("DEM", "Democratic"),
        ("REP", "Republican"),
        ("LIB", "Libertarian"),
        ("GRE", "Green"),
        ("IND", "Independent"),
        ("OTH", "Other"),
    ]

    STATUS_CHOICES = [
        ("C", "Statutory candidate"),
        ("F", "Statutory candidate for future election"),
        ("N", "Not yet a statutory candidate"),
        ("P", "Statutory candidate in prior cycle"),
    ]

    candidate_id = models.CharField(
        max_length=9, db_index=True,
        help_text="FEC candidate ID (e.g., P80001571). The same candidate has "
                  "one row per election cycle."
    )
    name = models.CharField(max_length=200, db_index=True)
    party = models.CharField(max_length=3, choices=PARTY_CHOICES, blank=True, db_index=True)
    office = models.CharField(max_length=1, choices=OFFICE_CHOICES, db_index=True)
    state = models.CharField(
        max_length=2, blank=True, db_index=True,
        help_text="Two-letter state code"
    )
    district = models.CharField(
        max_length=2, blank=True,
        help_text="Congressional district (House candidates only)"
    )
    incumbent_challenge = models.CharField(
        max_length=1, blank=True,
        help_text="I=Incumbent, C=Challenger, O=Open seat"
    )
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, blank=True)
    election_year = models.IntegerField(db_index=True, null=True)

    # Financial summary (updated from FEC totals)
    total_receipts = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Total money raised"
    )
    total_disbursements = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Total money spent"
    )
    cash_on_hand = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_individual_contributions = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-total_receipts"]
        indexes = [
            models.Index(fields=["party", "office"]),
            models.Index(fields=["state", "office"]),
            models.Index(fields=["election_year", "office"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["candidate_id", "election_year"],
                name="unique_candidate_per_cycle",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_party_display()}) - {self.get_office_display()}"

    @property
    def burn_rate(self):
        """Percentage of raised funds that have been spent."""
        if self.total_receipts > 0:
            return round(float(self.total_disbursements / self.total_receipts) * 100, 1)
        return 0


class Committee(models.Model):
    """A political committee (PAC, Super PAC, campaign committee, party committee)."""

    TYPE_CHOICES = [
        ("P", "Presidential campaign"),
        ("H", "House campaign"),
        ("S", "Senate campaign"),
        ("N", "PAC - Nonqualified"),
        ("O", "Super PAC (Independent Expenditure-Only)"),
        ("Q", "PAC - Qualified"),
        ("X", "Party - Nonqualified"),
        ("Y", "Party - Qualified"),
    ]

    committee_id = models.CharField(
        max_length=9, unique=True, db_index=True,
        help_text="FEC committee ID (e.g., C00580100)"
    )
    name = models.CharField(max_length=200, db_index=True)
    committee_type = models.CharField(max_length=1, choices=TYPE_CHOICES, blank=True)
    party = models.CharField(max_length=3, blank=True)
    state = models.CharField(max_length=2, blank=True)
    candidate = models.ForeignKey(
        Candidate, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="committees"
    )

    total_receipts = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_disbursements = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_independent_expenditures = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-total_receipts"]

    def __str__(self):
        return f"{self.name} ({self.committee_id})"


class ElectionSummary(models.Model):
    """Aggregated election statistics by cycle, state, and office."""

    election_year = models.IntegerField(db_index=True)
    state = models.CharField(max_length=2, blank=True, db_index=True)
    office = models.CharField(max_length=1, choices=Candidate.OFFICE_CHOICES)

    total_candidates = models.IntegerField(default=0)
    total_raised = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_spent = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    avg_raised = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    dem_raised = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Total raised by Democratic candidates"
    )
    rep_raised = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Total raised by Republican candidates"
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["election_year", "state", "office"]
        ordering = ["-election_year"]
        verbose_name_plural = "Election summaries"

    def __str__(self):
        return f"{self.election_year} {self.state or 'National'} {self.get_office_display()}"
