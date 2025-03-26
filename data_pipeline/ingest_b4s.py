import os
import time
import tracemalloc
from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup

def extract_epub_bs4(epub_path):
    book = epub.read_epub(epub_path)

    metadata = {
        'title': book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else '',
        'author': book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else ''
    }

    chapters = []
    for item in book.get_items():
        if item.get_type() == ITEM_DOCUMENT:
            try:
                content = item.get_content()
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text(separator=' ', strip=True)
                if text:
                    chapters.append(text)
            except Exception as e:
                print(f"⚠️ bs4 error in {item.get_name()}: {e}")

    return metadata, chapters

def benchmark_file_bs4(epub_path, use_memory=True):
    if use_memory:
        tracemalloc.start()

    start = time.time()
    metadata, chapters = extract_epub_bs4(epub_path)
    elapsed = time.time() - start

    memory = None
    if use_memory:
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        memory = peak / 1024

    return {
        'method': 'bs4',
        'filename': os.path.basename(epub_path),
        'time': elapsed,
        'memory': memory,
        'chunks': len(chapters),
        'text_len': sum(len(c) for c in chapters)
    }
