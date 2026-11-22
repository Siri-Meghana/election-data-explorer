from django.contrib import admin
from django.contrib.humanize.templatetags.humanize import intcomma

from .models import Candidate, Committee, ElectionSummary


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = [
        "name", "party", "office", "state", "election_year",
        "formatted_receipts", "formatted_disbursements",
    ]
    list_filter = ["party", "office", "election_year", "state"]
    search_fields = ["name", "candidate_id"]
    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description="Total Raised")
    def formatted_receipts(self, obj):
        return f"${intcomma(int(obj.total_receipts))}"

    @admin.display(description="Total Spent")
    def formatted_disbursements(self, obj):
        return f"${intcomma(int(obj.total_disbursements))}"


@admin.register(Committee)
class CommitteeAdmin(admin.ModelAdmin):
    list_display = ["name", "committee_type", "party", "state"]
    list_filter = ["committee_type", "party"]
    search_fields = ["name", "committee_id"]


@admin.register(ElectionSummary)
class ElectionSummaryAdmin(admin.ModelAdmin):
    list_display = [
        "election_year", "state", "office",
        "total_candidates", "total_raised",
    ]
    list_filter = ["election_year", "office"]
