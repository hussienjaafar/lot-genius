#!/usr/bin/env python3
"""
Markdown link checker for documentation files.
Scans docs/**/*.md for markdown links not starting with http, mailto, #.
Resolves relative paths from file dir and reports missing targets.
Exit code 0 if all resolve; nonzero with a list of broken links.
"""
import os
import re
import sys
from pathlib import Path


def extract_markdown_links(content):
    """Extract markdown links from content, returning (text, url, line_num) tuples"""
    links = []

    # Pattern for markdown links: [text](url)
    pattern = r'\[([^\]]*)\]\(([^)]+)\)'

    for line_num, line in enumerate(content.split('\n'), 1):
        for match in re.finditer(pattern, line):
            text, url = match.groups()
            links.append((text, url, line_num))

    return links


def is_relative_link(url):
    """Check if URL is a relative link that needs validation"""
    # Skip external links, anchors, and mailto
    if url.startswith(('http://', 'https://', 'mailto:', '#')):
        return False

    # Skip image URLs with absolute HTTP sources
    if url.startswith(('http://', 'https://')) and any(url.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg']):
        return False

    return True


def resolve_relative_path(base_file, relative_url):
    """Resolve relative URL from base file location"""
    # Remove anchor fragments
    url_path = relative_url.split('#')[0]

    # Get directory of base file
    base_dir = base_file.parent

    # Resolve relative path
    target_path = (base_dir / url_path).resolve()

    return target_path


def check_markdown_links(root_dir):
    """Check all markdown links in directory"""
    root = Path(root_dir)
    broken_links = []
    total_links = 0
    relative_links = 0

    for md_file in root.glob('**/*.md'):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            links = extract_markdown_links(content)
            total_links += len(links)

            for text, url, line_num in links:
                if is_relative_link(url):
                    relative_links += 1
                    target_path = resolve_relative_path(md_file, url)

                    if not target_path.exists():
                        broken_links.append({
                            'file': str(md_file.relative_to(root)),
                            'line': line_num,
                            'text': text,
                            'url': url,
                            'resolved_path': str(target_path),
                            'relative_to_root': str(target_path.relative_to(root.resolve())) if target_path.is_relative_to(root.resolve()) else str(target_path)
                        })

        except Exception as e:
            print(f'Error reading {md_file}: {e}', file=sys.stderr)

    return broken_links, total_links, relative_links


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_markdown_links.py <directory>")
        sys.exit(1)

    root_dir = sys.argv[1]
    if not os.path.exists(root_dir):
        print(f"Directory not found: {root_dir}")
        sys.exit(1)

    broken_links, total_links, relative_links = check_markdown_links(root_dir)

    print(f"Scanned markdown files in {root_dir}")
    print(f"Total links found: {total_links}")
    print(f"Relative links checked: {relative_links}")
    print()

    if not broken_links:
        print("OK All relative markdown links resolve successfully")
        sys.exit(0)

    print(f"X Found {len(broken_links)} broken relative links:")
    print()

    for link in broken_links:
        print(f"{link['file']}:{link['line']}")
        print(f"  Link text: [{link['text']}]({link['url']})")
        print(f"  Resolved to: {link['resolved_path']}")
        print(f"  Status: FILE NOT FOUND")
        print()

    sys.exit(len(broken_links))


if __name__ == '__main__':
    main()
