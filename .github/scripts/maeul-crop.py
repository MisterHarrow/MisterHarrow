#!/usr/bin/env python3
"""Strip the Maeul header + Village collection panel and crop to the timeline/terrain.

Usage: maeul-crop.py FILE.svg [FILE.svg ...]   (files are rewritten in place)
Exits non-zero if the expected markup isn't found, so a changed upstream
layout fails the job instead of committing a broken image.
"""
import re
import sys

PAD = 15  # space kept left of the timeline line


def remove_element(svg, start_pattern, tag):
    m = re.search(start_pattern, svg)
    if not m:
        raise ValueError(f"not found: {start_pattern}")
    start, depth, pos = m.start(), 0, m.start()
    opener, closer = re.compile(rf"<{tag}[\s>]"), f"</{tag}>"
    while True:
        o = opener.search(svg, pos)
        c = svg.find(closer, pos)
        if c == -1:
            raise ValueError(f"unclosed <{tag}> for {start_pattern}")
        if o and o.start() < c:
            depth += 1
            pos = o.end()
        else:
            depth -= 1
            pos = c + len(closer)
            if depth == 0:
                return svg[:start] + svg[pos:]


def process(svg):
    root = re.search(r'<svg\b[^>]*viewBox="0 0 (\d+(?:\.\d+)?) (\d+(?:\.\d+)?)"[^>]*>', svg)
    if not root:
        raise ValueError("root <svg> viewBox not found")
    width, height = float(root.group(1)), root.group(2)

    # Header: "@username" and the date-range line, then the collection panel.
    svg = remove_element(svg, r'<text x="24" y="17"[^>]*font-size="14"', "text")
    svg = remove_element(svg, r'<text x="24" y="32"[^>]*font-size="9"', "text")
    svg = remove_element(svg, r'<g class="village-collection"', "g")

    line = re.search(r'<g class="calendar-timeline".*?<line x1="(\d+(?:\.\d+)?)"', svg, re.S)
    if not line:
        raise ValueError("calendar timeline not found")
    left = max(0.0, float(line.group(1)) - PAD)
    new_w = width - left
    fmt = lambda n: f"{n:g}"

    # Crop the root viewBox and intrinsic size; keep the rounded background aligned.
    root_tag = root.group(0)
    new_root = root_tag.replace(f'viewBox="0 0 {root.group(1)} {height}"',
                                f'viewBox="{fmt(left)} 0 {fmt(new_w)} {height}"')
    new_root = re.sub(r'\bwidth="[\d.]+"', f'width="{fmt(new_w)}"', new_root, count=1)
    svg = svg.replace(root_tag, new_root, 1)
    svg = re.sub(rf'<rect width="{root.group(1)}" height="{height}"',
                 f'<rect x="{fmt(left)}" width="{fmt(new_w)}" height="{height}"', svg, count=1)

    # Re-space the stats bar evenly across the cropped width.
    bar = re.search(r'<g class="stats-bar">.*?</g>', svg, re.S)
    if bar:
        texts = re.findall(r'<text x="[\d.]+"', bar.group(0))
        slot = new_w / max(len(texts), 1)
        it = iter(range(len(texts)))

        def place(m):
            i = next(it)
            return f'<text x="{fmt(round(left + slot * (i + 0.5), 2))}" text-anchor="middle"'

        new_bar = re.sub(r'<text x="[\d.]+"', place, bar.group(0))
        new_bar = new_bar.replace('font-size="10"', 'font-size="9"')
        svg = svg.replace(bar.group(0), new_bar, 1)
    return svg


def main(paths):
    for path in paths:
        with open(path, encoding="utf-8") as f:
            svg = f.read()
        if 'data-maeul-cropped="1"' in svg:
            print(f"{path}: already cropped")
            continue
        svg = process(svg).replace("<svg ", '<svg data-maeul-cropped="1" ', 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"{path}: cropped")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
