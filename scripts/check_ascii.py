#!/usr/bin/env python3
"""
ASCII checker for documentation files.
Scans given paths and prints any file/offset/char code >127.
Exit code 0 if none found; nonzero if found.
"""
import os
import sys
from pathlib import Path


def scan_non_ascii(root_dir):
    """Scan for non-ASCII characters in markdown files"""
    root = Path(root_dir)
    results = []

    for md_file in root.glob('**/*.md'):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            for line_num, line in enumerate(content.split('\n'), 1):
                for char_pos, char in enumerate(line):
                    if ord(char) > 127:
                        results.append({
                            'file': str(md_file.relative_to(root)),
                            'line': line_num,
                            'pos': char_pos,
                            'char': char,
                            'ord': ord(char),
                            'hex': hex(ord(char)),
                            'context': line[max(0, char_pos-10):char_pos+10]
                        })
        except Exception as e:
            print(f'Error reading {md_file}: {e}', file=sys.stderr)

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_ascii.py <directory>")
        sys.exit(1)

    root_dir = sys.argv[1]
    if not os.path.exists(root_dir):
        print(f"Directory not found: {root_dir}")
        sys.exit(1)

    results = scan_non_ascii(root_dir)

    if not results:
        print(f"OK All files in {root_dir} contain only ASCII characters")
        sys.exit(0)

    print(f"Found {len(results)} non-ASCII characters:")
    print()

    # Group by file for cleaner output
    by_file = {}
    for r in results:
        if r['file'] not in by_file:
            by_file[r['file']] = []
        by_file[r['file']].append(r)

    for filename, chars in by_file.items():
        print(f"{filename}:")
        for r in chars[:10]:  # Show first 10 per file
            try:
                # Safe character representation
                char_repr = r['char'] if r['char'].isprintable() else f'\\u{r["ord"]:04x}'
                context_safe = ''.join(c if ord(c) <= 127 and c.isprintable() else '?' for c in r['context'])
                print(f"  Line {r['line']}, pos {r['pos']}: {char_repr} (U+{r['hex'][2:].upper().zfill(4)}) in: '{context_safe}'")
            except UnicodeEncodeError:
                print(f"  Line {r['line']}, pos {r['pos']}: [unprintable] (U+{r['hex'][2:].upper().zfill(4)})")

        if len(chars) > 10:
            print(f"  ... and {len(chars) - 10} more non-ASCII characters")
        print()

    sys.exit(len(results))


if __name__ == '__main__':
    main()
