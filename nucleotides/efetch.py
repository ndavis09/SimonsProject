import hashlib

import requests


EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def efetch_nucleotide(db, id, rettype, retmode):
    """Fetch a record from NCBI efetch and return the text content.

    Args:
        db: NCBI database (spec default: 'nucleotide').
        accession_id: Record id (small doc: '30271926').
        rettype: Retrieval type (spec default: 'fasta').
        retmode: Retrieval mode (spec default: 'xml').
    """
    params = {
        "db": db,
        "id": id,
        "rettype": rettype,
        "retmode": retmode,
    }

    resp = requests.get(EFETCH_URL, params=params, timeout=(5, 30))
    resp.raise_for_status()

    content = resp.text
    if not content:
        raise ValueError("Empty response from NCBI efetch.")

    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    meta = {
        "sha256": digest,
        "content_length": str(len(content.encode("utf-8"))),
    }
    return content, meta