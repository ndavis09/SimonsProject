from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages

from .forms import FetchForm
from .efetch import efetch_nucleotide
from .models import FetchedDocument
from .utils import split_tseq_sequence


class HomeView(View):
    """Home page with a small form to fetch and store an efetch payload, or load fetched docs from DB."""

    template_name = "nucleotides/home.html"

    def get(self, request):
        form = FetchForm()
        docs = FetchedDocument.objects.order_by("-fetched_at")[:10]
        return render(request, self.template_name, {"form": form, "docs": docs})

    def post(self, request):
        form = FetchForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        db = form.cleaned_data["db"]
        accession_id = form.cleaned_data["accession_id"]
        rettype = form.cleaned_data["rettype"]
        retmode = form.cleaned_data["retmode"]

        try:
            content, meta = efetch_nucleotide(db, accession_id, rettype, retmode)
        except Exception as exc:
            messages.error(request, f"Fetch failed: {exc}")
            return render(request, self.template_name, {"form": form})

        # Upsert-like behavior: replace if same key combo already exists.
        doc, _created = FetchedDocument.objects.update_or_create(
            db=db,
            accession_id=accession_id,
            rettype=rettype,
            retmode=retmode,
            defaults={
                "content": content,
                "content_length": int(meta["content_length"]),
                "sha256": meta["sha256"],
            },
        )

        messages.success(request, f"Saved {doc} ({doc.content_length} bytes).")
        return redirect("fetch-detail", pk=doc.pk)


class FetchDetailView(View):
    template_name = "nucleotides/detail.html"

    def get(self, request, pk: int):
        doc = get_object_or_404(FetchedDocument, pk=pk)
        metadata_xml, sequence_text = split_tseq_sequence(doc.content)

        context = {
            "doc": doc,
            "metadata_xml": metadata_xml,
            "sequence_text": sequence_text,
            "sequence_len": len(sequence_text),
        }
        return render(request, self.template_name, context)