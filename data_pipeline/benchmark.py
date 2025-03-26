import os
from ingest_b4s import benchmark_file_bs4
from ingest_lxml import benchmark_file_lxml

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

    for bs4, lxml in results:
        print(f"{bs4['filename']:<30} | {bs4['time']:.3f} s   | {lxml['time']:.3f} s   | "
              f"{bs4['memory']:.1f} KB | {lxml['memory']:.1f} KB")

if __name__ == "__main__":
    folder = r'./books'  # Change to your actual folder path
    compare_parsers(folder)
