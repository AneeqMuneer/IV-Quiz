#!/usr/bin/env python3
"""
Scans the 'pictures' folder that sits next to index.html and writes pictures/manifest.js,
which the Pictorial round reads. Run it once, and again whenever you add or change pictures.

Expected layout (folder names are the places; they are never shown on the wheel):

    index.html
    pictures/
        Hunza/
            1.jpg          <- the FIRST image (alphabetical / numeric order) goes on the wheel
            2.jpg          <- all images are shown after the wheel stops
            questions.txt  <- optional, up to 3 questions:
                                 Q: In which valley is this fort?
                                 A: Hunza Valley
                                 Q: Which mountain stands behind it?
                                 A: Rakaposhi
                                 Q: ...
                                 A: ...
        Skardu/
            ...

Usage:   python make_pictures_manifest.py
"""
import json, os, re, sys
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
PICS = os.path.join(HERE, "pictures")
IMG = re.compile(r"\.(jpe?g|png|webp|gif|avif|bmp)$", re.I)

def natural(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]

def main():
    if not os.path.isdir(PICS):
        sys.exit("Could not find a 'pictures' folder next to this script: " + PICS)
    places = []
    for name in sorted(os.listdir(PICS), key=natural):
        d = os.path.join(PICS, name)
        if not os.path.isdir(d):
            continue
        files = sorted((f for f in os.listdir(d) if IMG.search(f)), key=natural)
        if not files:
            print("  (skipped, no images) " + name)
            continue
        qtxt = ""
        for f in os.listdir(d):
            if f.lower() == "questions.txt":
                with open(os.path.join(d, f), encoding="utf-8-sig") as fh:
                    qtxt = fh.read()
        places.append({
            "name": name,
            "images": ["pictures/" + quote(name) + "/" + quote(f) for f in files],
            "qtxt": qtxt,
        })
        print("  %-30s %2d picture(s)%s" % (name, len(files), "" if qtxt else "   (no questions.txt)"))
    out = os.path.join(HERE, "manifest.js")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("window.IVQ_PICTURES = " + json.dumps(places, ensure_ascii=False, indent=1) + ";\n")
    print("\nWrote %s with %d place(s)." % (out, len(places)))

if __name__ == "__main__":
    main()
