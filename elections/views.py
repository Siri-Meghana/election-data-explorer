"""
Views for the Election Data Explorer: a dashboard, a searchable candidate
list, and a candidate detail page.
"""

from django.db.models import Avg, Count, Sum
from django.http import Http404
from django.shortcuts import render
from django.views.generic import DetailView, ListView

from .models import Candidate


def dashboard(request):
    """Home page: overview of campaign finance totals for one cycle."""
    cycle = int(request.GET.get("cycle", 2024))

    candidates = Candidate.objects.filter(election_year=cycle)

    stats = candidates.aggregate(
        total_candidates=Count("id"),
        total_raised=Sum("total_receipts"),
        total_spent=Sum("total_disbursements"),
        avg_raised=Avg("total_receipts"),
    )

    party_totals = (
        candidates
        .values("party")
        .annotate(
            count=Count("id"),
            raised=Sum("total_receipts"),
            spent=Sum("total_disbursements"),
        )
        .order_by("-raised")
    )

    office_totals = (
        candidates
        .values("office")
        .annotate(count=Count("id"), raised=Sum("total_receipts"))
        .order_by("-raised")
    )

    context = {
        "cycle": cycle,
        "stats": stats,
        "party_totals": party_totals,
        "top_candidates": candidates[:10],
        "office_totals": office_totals,
        "available_cycles": [2026, 2024, 2022, 2020, 2018],
    }
    return render(request, "elections/dashboard.html", context)


class CandidateListView(ListView):
    """Searchable, filterable list of candidates."""

    model = Candidate
    template_name = "elections/candidate_list.html"
    context_object_name = "candidates"
    paginate_by = 25

    def get_queryset(self):
        qs = Candidate.objects.all()

        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(name__icontains=search)

        party = self.request.GET.get("party")
        if party:
            qs = qs.filter(party=party)

        office = self.request.GET.get("office")
        if office:
            qs = qs.filter(office=office)

        state = self.request.GET.get("state")
        if state:
            qs = qs.filter(state=state.upper())

        cycle = self.request.GET.get("cycle")
        if cycle and cycle.isdigit():
            qs = qs.filter(election_year=int(cycle))

        sort = self.request.GET.get("sort", "-total_receipts")
        allowed_sorts = [
            "name", "-name", "total_receipts", "-total_receipts",
            "total_disbursements", "-total_disbursements",
            "cash_on_hand", "-cash_on_hand",
        ]
        if sort in allowed_sorts:
            qs = qs.order_by(sort)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        context["selected_party"] = self.request.GET.get("party", "")
        context["selected_office"] = self.request.GET.get("office", "")
        context["selected_state"] = self.request.GET.get("state", "")
        context["selected_cycle"] = self.request.GET.get("cycle", "")
        context["selected_sort"] = self.request.GET.get("sort", "-total_receipts")
        context["party_choices"] = Candidate.PARTY_CHOICES
        context["office_choices"] = Candidate.OFFICE_CHOICES
        return context


class CandidateDetailView(DetailView):
    """One candidate's finances, plus their results across election cycles."""

    model = Candidate
    template_name = "elections/candidate_detail.html"
    context_object_name = "candidate"

    def get_object(self):
        # A candidate has one row per cycle: use ?cycle=YYYY, else the latest.
        qs = Candidate.objects.filter(candidate_id=self.kwargs["candidate_id"])
        cycle = self.request.GET.get("cycle", "")
        if cycle.isdigit():
            qs = qs.filter(election_year=int(cycle))
        candidate = qs.order_by("-election_year").first()
        if candidate is None:
            raise Http404("No candidate matches this ID")
        return candidate

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cycles"] = Candidate.objects.filter(
            candidate_id=self.object.candidate_id
        ).order_by("-election_year")
        return context
