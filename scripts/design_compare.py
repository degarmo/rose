"""Side-by-side images of the design and the built app, for docs/design/compare/.

Pairs each reference in docs/design/reference/ with the capture of the same name in
docs/design/after/ (both written by e2e/scripts), and writes one image per pair: the
design on the left, the app on the right, each labelled, tops aligned.

    backend/.venv/bin/python scripts/design_compare.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DESIGN = Path(__file__).resolve().parents[1] / "docs" / "design"
GAP = 40
LABEL = 56
BACKGROUND = (242, 240, 239)


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def side_by_side(reference, built):
    with Image.open(reference) as left, Image.open(built) as right:
        left, right = left.convert("RGB"), right.convert("RGB")
        width = left.width + right.width + GAP * 3
        height = max(left.height, right.height) + LABEL + GAP
        sheet = Image.new("RGB", (width, height), BACKGROUND)
        sheet.paste(left, (GAP, LABEL))
        sheet.paste(right, (GAP * 2 + left.width, LABEL))
    draw = ImageDraw.Draw(sheet)
    draw.text((GAP, 16), "Design", fill=(115, 115, 115), font=font(24))
    draw.text((GAP * 2 + left.width, 16), "Built", fill=(115, 115, 115), font=font(24))
    return sheet


def main():
    out = DESIGN / "compare"
    out.mkdir(exist_ok=True)
    for old in out.glob("*.png"):
        old.unlink()
    made = []
    for reference in sorted((DESIGN / "reference").glob("*.png")):
        built = DESIGN / "after" / reference.name
        if built.exists():
            side_by_side(reference, built).save(out / reference.name, optimize=True)
            made.append(reference.name)
    print(f"{len(made)} comparisons in {out}")


if __name__ == "__main__":
    main()
