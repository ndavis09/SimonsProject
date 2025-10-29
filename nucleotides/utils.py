from typing import Tuple
import xml.etree.ElementTree as ET
from xml.dom import minidom


def split_tseq_sequence(xml_text):
    """
    Split an NCBI TSeq XML payload into (metadata_xml, sequence_text).
    """
    root = ET.fromstring(xml_text)

    # collect sequences
    sequences = []
    for elem in root.iter():
        if elem.tag == "TSeq_sequence" and (elem.text or "").strip():
            sequences.append(elem.text.strip())

    # remove all TSeq_sequence elements from tree
    for parent in root.iter():
        # work on a copy of children list for safe removal
        for child in list(parent):
            if child.tag == "TSeq_sequence":
                parent.remove(child)

    rough = ET.tostring(root, encoding="utf-8")
    pretty = minidom.parseString(rough).toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

    return pretty, "".join(sequences)
