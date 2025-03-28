import os
from ingest_b4s import benchmark_file_bs4, extract_epub_bs4_spine_aligned
from ingest_lxml import benchmark_file_lxml, extract_epub_lxml_spine_aligned
from difflib import SequenceMatcher
from ebooklib import epub
import re
import unicodedata

def compare_parsers(folder_path, use_memory=True):
    files = [f for f in os.listdir(folder_path) if f.endswith('.epub')]
    results = []

    print(f"\n📂 Comparing bs4 vs lxml in folder: {folder_path}\n")

    for file in files:
        full_path = os.path.join(folder_path, file)

        print(f"📘 File: {file}")
        res_bs4 = benchmark_file_bs4(full_path, use_memory)
        res_lxml = benchmark_file_lxml(full_path, use_memory)

        results.append((res_bs4, res_lxml))

        print(f"  🥣 bs4  → {res_bs4['time']:.3f} sec, {res_bs4['memory']:.1f} KB, {res_bs4['chunks']} chunks")
        print(f"  ⚡ lxml → {res_lxml['time']:.3f} sec, {res_lxml['memory']:.1f} KB, {res_lxml['chunks']} chunks\n")

    print("\n📊 Final Comparison:")
    print(f"{'Filename':<30} | {'bs4 Time':<8} | {'lxml Time':<9} | {'bs4 Mem':<8} | {'lxml Mem':<9}")
    print("-" * 75)

def normalize(text):
    """Normalize text to reduce superficial differences."""
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def compare_first_book_chunks(folder_path, similarity_threshold=0.95, max_mismatches=5):
    # Pick the first EPUB in the folder
    epub_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.epub')]
    if not epub_files:
        print("❌ No .epub files found in the folder.")
        return

    epub_path = os.path.join(folder_path, epub_files[1])
    print(f"\n📘 Comparing spine-aligned chunks from: {epub_path}")

    # Extract chunks using both parsers
    _, chunks_bs4 = extract_epub_bs4_spine_aligned(epub_path)
    _, chunks_lxml = extract_epub_lxml_spine_aligned(epub_path)

    print(f"\n🔢 Chunk counts — bs4: {len(chunks_bs4)}, lxml: {len(chunks_lxml)}")

    # Compare chunks by spine order
    min_len = min(len(chunks_bs4), len(chunks_lxml))
    mismatches = []

    for i in range(min_len):
        name_bs4, text_bs4 = chunks_bs4[i]
        name_lxml, text_lxml = chunks_lxml[i]

        norm_bs4 = normalize(text_bs4)
        norm_lxml = normalize(text_lxml)

        ratio = SequenceMatcher(None, norm_bs4, norm_lxml).ratio()

        if ratio < similarity_threshold:
            mismatches.append((
                i, name_bs4, ratio,
                len(norm_bs4), len(norm_lxml),
                norm_bs4[:250], norm_lxml[:250]
            ))

    print(f"\n⚠️ Found {len(mismatches)} mismatched chunks (similarity < {similarity_threshold:.2f})")

    for i, name, ratio, len_bs4, len_lxml, preview_bs4, preview_lxml in mismatches[:max_mismatches]:
        print(f"\n📎 Chunk {i} — File: {name}")
        print(f"  Similarity: {ratio:.3f}")
        print(f"  Lengths — bs4: {len_bs4}, lxml: {len_lxml}")
        print("  🥣 bs4  :", preview_bs4)
        print("  ⚡ lxml :", preview_lxml)

    if len(chunks_bs4) != len(chunks_lxml):
        print(f"\n⚠️ Chunk count mismatch! bs4={len(chunks_bs4)}, lxml={len(chunks_lxml)}")

    print("\n✅ Spine-aligned comparison complete.")

def log_epub_spine(epub_path):
    book = epub.read_epub(epub_path)

    print(f"\n🦴 Spine order for: {epub_path}")
    print("---------------------------------------------------")

    spine = book.spine  # list of tuples: [(idref, properties), ...]
    idrefs = [item[0] for item in spine]

    for i, idref in enumerate(idrefs):
        item = book.get_item_with_id(idref)
        print(f"{i:02d}. ID: {idref:<20} | Name: {item.get_name()}")


if __name__ == "__main__":
    folder = r'./books' 
    #compare_first_book_chunks(folder)
    #log_epub_spine('./books/03.epub')
    compare_parsers(folder)