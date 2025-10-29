from django.db import models


class FetchedDocument(models.Model):
    """
    Stores an efetch result + parameters.
    """

    # defaults taken from spec; could change for later version
    db = models.CharField(max_length=64, default="nucleotide")
    accession_id = models.CharField(max_length=64, db_index=True)
    rettype = models.CharField(max_length=32, default="fasta")
    retmode = models.CharField(max_length=32, default="xml")

    content = models.TextField()
    content_length = models.BigIntegerField()
    sha256 = models.CharField(max_length=64)

    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("db", "accession_id", "rettype", "retmode")
        indexes = [
            models.Index(fields=["accession_id", "db"]),
        ]

    def __str__(self):
        return f"{self.db}:{self.accession_id} ({self.rettype}/{self.retmode})"