#!/usr/bin/env python3

import sys
import os
import re
from PIL import Image
from xml.etree.ElementTree import Element, SubElement, tostring

# Only allow .png files
ALLOWED_EXTENSIONS = {'.png'}

def is_valid_image(file_path):
    return os.path.splitext(file_path)[1].lower() in ALLOWED_EXTENSIONS

def extract_prompt(png_path):
    """Extract and sanitize the 'parameters' tEXt chunk from PNG metadata."""
    try:
        with Image.open(png_path) as img:
            raw = img.info.get("parameters", "")
            raw = raw.encode("utf-8", "ignore").decode("utf-8", "ignore")
            return sanitize_xml_string(raw.strip())
    except Exception as e:
        print(f"❌ Error reading {png_path}: {e}")
        return None

# Valid XML 1.0 characters (excluding control chars except \t, \n, \r)
_invalid_xml_chars = re.compile(
    r"[\x00-\x08\x0B\x0C\x0E-\x1F\uFFFE\uFFFF"
    r"\uD800-\uDFFF"
    r"\U0001FFFE\U0001FFFF\U0002FFFE\U0002FFFF"
    r"\U0003FFFE\U0003FFFF\U0004FFFE\U0004FFFF"
    r"\U0005FFFE\U0005FFFF\U0006FFFE\U0006FFFF"
    r"\U0007FFFE\U0007FFFF\U0008FFFE\U0008FFFF"
    r"\U0009FFFE\U0009FFFF\U000AFFFE\U000AFFFF"
    r"\U000BFFFE\U000BFFFF\U000CFFFE\U000CFFFF"
    r"\U000DFFFE\U000DFFFF\U000EFFFE\U000EFFFF"
    r"\U000FFFFE\U000FFFFF\U0010FFFE\U0010FFFF]"
)

def sanitize_xml_string(s):
    """Remove characters illegal in XML 1.0."""
    return _invalid_xml_chars.sub("", s)

def create_or_update_xmp(image_path, prompt, overwrite=False):
    """Create or update a sidecar .xmp file with the given prompt as CDATA description."""
    xmp_path = image_path + ".xmp"

    if os.path.exists(xmp_path) and not overwrite:
        print(f"⚠️  Skipping existing file: {xmp_path}")
        return

    # Build base XML structure (excluding the CDATA value for now)
    rdf = Element("x:xmpmeta", {
        "xmlns:x": "adobe:ns:meta/"
    })
    rdf_rdf = SubElement(rdf, "rdf:RDF", {
        "xmlns:rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "xmlns:dc": "http://purl.org/dc/elements/1.1/"
    })
    description = SubElement(rdf_rdf, "rdf:Description", {
        "rdf:about": ""
    })
    dc_description = SubElement(description, "dc:description")
    lang_alt = SubElement(dc_description, "rdf:Alt")
    li = SubElement(lang_alt, "rdf:li", {"xml:lang": "x-default"})
    li.text = "__PROMPT_CDATA_PLACEHOLDER__"

    rough_xml = tostring(rdf, encoding="unicode")
    prompt = prompt.replace("]]>", "]] >")
    cdata_block = f"<![CDATA[{prompt}]]>"
    xml_with_cdata = rough_xml.replace("__PROMPT_CDATA_PLACEHOLDER__", cdata_block)

    xmp_final = (
        '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
        + xml_with_cdata +
        '\n<?xpacket end="w"?>\n'
    )

    try:
        with open(xmp_path, "w", encoding="utf-8") as f:
            f.write(xmp_final)
        print(f"✅ Wrote: {xmp_path}")
    except Exception as e:
        print(f"❌ Failed to write {xmp_path}: {e}")

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Extract prompt metadata from PNG and write to XMP notes.")
    parser.add_argument("images", nargs="+", help="Input image files")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing .xmp files")
    args = parser.parse_args()

    valid_files = []
    for image_path in args.images:
        if is_valid_image(image_path):
            valid_files.append(image_path)
        else:
            print(f"⚠️  Skipping unsupported file type: {image_path}")

    if not valid_files:
        print("❌ No valid .png files to process.")
        sys.exit(1)

    for image_path in valid_files:
        prompt = extract_prompt(image_path)
        if prompt:
            create_or_update_xmp(image_path, prompt, overwrite=args.overwrite)
        else:
            print(f"⚠️  No parameters found in: {image_path}")

if __name__ == "__main__":
    main()
