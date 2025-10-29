from django import forms


class FetchForm(forms.Form):
    """Simple efetch parameter form with sensible defaults."""
    db = forms.CharField(initial="nucleotide", max_length=64)
    accession_id = forms.CharField(label="id", initial="30271926", max_length=64)
    rettype = forms.CharField(initial="fasta", max_length=32)
    retmode = forms.CharField(initial="xml", max_length=32)