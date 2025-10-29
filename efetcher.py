import argparse
import os
import re
import sys
import tempfile

import requests
from xml.sax import make_parser
from xml.sax.handler import ContentHandler

EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


class TSeqSequenceExtractor(ContentHandler):
    """
    XML handler that streams out only the <TSeq_sequence> text.
    Whitespace/newlines are removed so the sequence is contiguous.
    SAX (rather than ElementTree approach) for parsing larger data as stream
    """
    def __init__(self, output_stream):
        super().__init__()
        self.output_stream = output_stream
        self.in_tseq_sequence = False

    def startElement(self, name, attrs):
        if name == "TSeq_sequence":
            self.in_tseq_sequence = True

    def endElement(self, name):
        if name == "TSeq_sequence":
            self.in_tseq_sequence = False

    def characters(self, content):
        if self.in_tseq_sequence and content:
            # Remove all whitespace to guarantee sequence is contiguous.
            # 'translate' beats 'replace' for speed/manageability on larger files.
            self.output_stream.write(content.translate({ord(c): None for c in " \t\r\n"}))


def fetch_efetch_xml_to_file(parameters, destination_path):
    """
    Download the EFetch payload to a temp file.
    """
    try:
        with requests.get(EFETCH_URL, params=parameters, stream=True, timeout=(10, 60)) as response:
            response.raise_for_status()
            with open(destination_path, "wb") as output_file:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:  # keep-alive chunks can be empty
                        output_file.write(chunk)
    except requests.HTTPError as exc:
        sys.exit(f"HTTP error fetching EFetch data: {exc}")
    except requests.RequestException as exc:
        sys.exit(f"Network error fetching EFetch data: {exc}")


def extract_sequence_to_file(xml_path, sequence_path):
    """
    Parse the XML and stream <TSeq_sequence> text into a separate file.
    """
    try:
        parser = make_parser()
        with open(sequence_path, "w", encoding="utf-8") as seq_out, open(xml_path, "rb") as xml_in:
            handler = TSeqSequenceExtractor(seq_out)
            parser.setContentHandler(handler)
            parser.parse(xml_in)
    except Exception as exc:
        sys.exit(f"XML parse error while extracting sequence: {exc}")


def find_regex_spans(sequence_text, pattern_text):
    """
    Return a list of (start, end) spans for all regex matches (0-based, end-exclusive).

    Guards against zero-length matches to ensure forward progress.
    """
    try:
        compiled_regex = re.compile(pattern_text)
    except re.error as exc:
        sys.exit(f"Invalid regex: {exc}")

    spans = []
    search_position = 0
    text_length = len(sequence_text)

    while True:
        match_object = compiled_regex.search(sequence_text, search_position)
        if not match_object:
            break # no match end condition

        start_index = match_object.start()
        end_index = match_object.end()

        spans.append((start_index, end_index))

        # guard against zero-length match loop
        if end_index == start_index:
            search_position = end_index + 1
            if search_position > text_length:
                break # matches exhausted end condition
        else:
            search_position = end_index

    return spans


def build_context_snippet(sequence_text, start_index, end_index, context_chars):
    """
    Build a snippet showing up to `context_chars` on both sides of the match.
    Adds leading/trailing ellipses only if the match is not at a boundary.
    """
    if context_chars < 0:
        context_chars = 0

    seq_len = len(sequence_text)
    left_start = max(0, start_index - context_chars)
    right_end = min(seq_len, end_index + context_chars)

    left_context = sequence_text[left_start:start_index]
    match_text = sequence_text[start_index:end_index]
    right_context = sequence_text[end_index:right_end]

    # ellipses only if match is found in the middle of the sequence
    left_ellipsis = "..." if left_start > 0 else ""
    right_ellipsis = "..." if right_end < seq_len else ""

    return f"{left_ellipsis}{left_context}{match_text}{right_context}{right_ellipsis}"


def main():
    parser = argparse.ArgumentParser(description="Fetch NCBI nucleotide via EFetch and grep regex match positions.")
    parser.add_argument("--db", default="nucleotide", help="EFetch database (default: nucleotide)")
    parser.add_argument("--id", dest="record_id", default="224589800", help="Record id/accession (default: 224589800)")
    parser.add_argument("--rettype", default="fasta", help="Retrieval type (default: fasta)")
    parser.add_argument("--retmode", default="xml", help="Retrieval mode (default: xml)")
    parser.add_argument("--regex", required=True, help="Regular expression to search for within the sequence")
    parser.add_argument("--context", type=int, default=1, help="Context characters to show on each side (default: 1)")
    parser.add_argument("--output", help="Write results to this file instead of stdout")
    parser.add_argument("--keep-files", action="store_true", help="Keep temp XML/sequence files for debugging")

    args = parser.parse_args()

    # use temp files, could rearchitect around persistent files for a later version
    temp_dir = tempfile.mkdtemp(prefix="efetch_")
    xml_path = os.path.join(temp_dir, "payload.xml")
    seq_path = os.path.join(temp_dir, "sequence.txt")

    try:
        query_params = {
            "db": args.db,
            "id": args.record_id,
            "rettype": args.rettype,
            "retmode": args.retmode,
        }

        fetch_efetch_xml_to_file(query_params, xml_path)
        extract_sequence_to_file(xml_path, seq_path)
        with open(seq_path, "r", encoding="utf-8") as seq_file_handle:
            sequence_text = seq_file_handle.read()

        spans = find_regex_spans(sequence_text, args.regex)

        def emit_lines(handle):
            for start_index, end_index in spans:
                snippet = build_context_snippet(sequence_text, start_index, end_index, args.context)
                handle.write(f'{start_index}:"{snippet}"\n')

        if args.output:
            with open(args.output, "w", encoding="utf-8") as output_handle:
                emit_lines(output_handle)
        else:
            emit_lines(sys.stdout)

    finally:
        # temp file cleanup
        if not args.keep_files:
            try:
                if os.path.exists(xml_path):
                    os.remove(xml_path)
                if os.path.exists(seq_path):
                    os.remove(seq_path)
                if os.path.isdir(temp_dir):
                    os.rmdir(temp_dir)
            except OSError as exc:
                print(f"File cleanup error: {exc}")


if __name__ == "__main__":
    main()
