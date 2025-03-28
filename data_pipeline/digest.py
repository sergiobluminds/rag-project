import zipfile
import re
from enum import Enum
from lxml import etree
import os
from lxml import html
from collections import defaultdict

class EPUBVersion(Enum):
    EPUB2 = "2.0"
    EPUB3 = "3.0"
    UNKNOWN = "Unknown"

def detect_epub_version(epub_path):
    try:
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            # Step 1: Find the path to the content.opf from META-INF/container.xml
            with zip_ref.open("META-INF/container.xml") as container_file:
                container_tree = etree.parse(container_file)
                opf_path = container_tree.xpath("//*[local-name()='rootfile']")[0].get("full-path")

            # Step 2: Read the content.opf and extract the version
            with zip_ref.open(opf_path) as opf_file:
                opf_content = opf_file.read().decode("utf-8")
                version_match = re.search(r'<package[^>]*version="([^"]+)"', opf_content)
                version = version_match.group(1) if version_match else None

                if version == "2.0":
                    return EPUBVersion.EPUB2
                elif version == "3.0":
                    return EPUBVersion.EPUB3
                else:
                    return EPUBVersion.UNKNOWN

    except Exception as e:
        print(f"Error detecting version: {e}")
        return EPUBVersion.UNKNOWN


def unzip_epub(epub_path, extract_to):
    """Unzips EPUB archive to specified directory."""
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def extract_epub3_toc_fallback(epub_dir):
    """Brute-force extract TOC links from any <nav> in ftoc.xhtml or nav.xhtml."""
    toc_entries = []

    # Locate ftoc.xhtml or nav.xhtml
    nav_path = None
    for root, _, files in os.walk(epub_dir):
        for file in files:
            if file.lower().endswith(".xhtml") and "toc" in file.lower():
                nav_path = os.path.join(root, file)
                break
        if nav_path:
            break

    if not nav_path:
        print("❌ No TOC file found.")
        return toc_entries

    # Parse using lxml.html
    tree = html.parse(nav_path)
    navs = tree.xpath('//nav')

    for nav in navs:
        text = nav.text_content().lower()
        if "contents" in text or "table of contents" in text:
            links = nav.xpath('.//a')
            for a in links:
                href = a.get("href")
                title = a.text_content().strip()
                if href and title:
                    toc_entries.append({"title": title, "src": href})
            break  # only use the first likely nav

    return toc_entries


def extract_epub3_chapters(epub_dir, toc_entries):
    """
    Given extracted EPUB 3 dir and parsed TOC entries, extract chapter content.
    Returns a list of {'id', 'title', 'content'}.
    """
    chapters = []

    for entry in toc_entries:
        src = entry["src"]
        title = entry["title"]

        # Split into file and optional anchor
        file_part, anchor = (src.split("#") + [None])[:2]
        file_path = None

        # Locate file path
        for root, _, files in os.walk(epub_dir):
            if file_part in files:
                file_path = os.path.join(root, file_part)
                break

        if not file_path or not os.path.exists(file_path):
            continue

        try:
            tree = html.parse(file_path)
        except:
            continue

        content = []
        found_start = False

        # If there's an anchor, try to find it
        if anchor:
            anchor_elems = tree.xpath(f'//*[@id="{anchor}"]')
            if not anchor_elems:
                continue
            start_elem = anchor_elems[0]
        else:
            start_elem = tree.xpath('//body')[0]

        current = start_elem

        while current is not None:
            # Stop at next anchor, header, or section
            if found_start and (current.tag in ["h1", "h2", "section"] or current.get("id")):
                break

            if not found_start or current == start_elem:
                found_start = True
                content.append(html.tostring(current, encoding="unicode", method="text").strip())

            current = current.getnext()

        chapters.append({
            "id": re.sub(r'\W+', '_', anchor or title.lower()),
            "title": title,
            "content": "\n".join(content).strip()
        })

    return chapters

from lxml import html
import re
from collections import defaultdict

def extract_epub3_chapters_precise(epub_dir, toc_entries):
    chapters = []

    # Group entries by file
    file_groups = defaultdict(list)
    for entry in toc_entries:
        file, anchor = (entry["src"].split("#") + [None])[:2]
        file_groups[file].append((anchor, entry["title"]))

    for file_part, anchor_title_pairs in file_groups.items():
        # Locate file
        file_path = None
        for root, _, files in os.walk(epub_dir):
            if file_part in files:
                file_path = os.path.join(root, file_part)
                break
        if not file_path:
            continue

        try:
            doc = html.parse(file_path)
        except:
            continue

        # Build a map of all id’d elements
        anchors = doc.xpath('//*[@id]')
        anchor_map = {a.get("id"): a for a in anchors}
        anchor_map[None] = doc.xpath('//body')[0]

        for idx, (anchor, title) in enumerate(anchor_title_pairs):
            raw_elem = anchor_map.get(anchor)
            if raw_elem is None:
                chapters.append({
                    "id": re.sub(r'\W+', '_', anchor or title.lower()),
                    "title": title,
                    "content": ""
                })
                continue

            # Traverse upward to <section> or <h2>/<h3> to get starting block
            parent = raw_elem
            while parent is not None and parent.tag not in ("section", "h1", "h2", "h3", "div", "article"):
                parent = parent.getparent()
            start_elem = parent or raw_elem

            # Locate the next anchor for stopping
            stop_elem = None
            for j in range(idx + 1, len(anchor_title_pairs)):
                next_anchor = anchor_title_pairs[j][0]
                if next_anchor and next_anchor in anchor_map:
                    # Traverse up again for next section/block
                    stop_raw = anchor_map[next_anchor]
                    stop_parent = stop_raw
                    while stop_parent is not None and stop_parent.tag not in ("section", "h1", "h2", "h3", "div", "article"):
                        stop_parent = stop_parent.getparent()
                    stop_elem = stop_parent or stop_raw
                    break

            # Collect content from start to before stop
            content = []
            current = start_elem
            while current is not None:
                if current == stop_elem:
                    break
                content.append(html.tostring(current, encoding="unicode", method="text").strip())
                current = current.getnext()

            chapters.append({
                "id": re.sub(r'\W+', '_', anchor or title.lower()),
                "title": title,
                "content": "\n".join(content).strip()
            })

    return chapters




if __name__ == "__main__":
    epub_path = "./books/04.epub"
    extract_to = "./extracted_book"

    unzip_epub(epub_path, extract_to)
    toc = extract_epub3_toc_fallback(extract_to)

    #for entry in toc:
    #    print(f"{entry['title']} -> {entry['src']}")

    chapters = extract_epub3_chapters(extract_to, toc)
    precise_chapters = extract_epub3_chapters_precise(extract_to, toc)
    #print(f'chapters: {chapters[13]}')
    print(f'precise_chapters: {precise_chapters[14]}')
