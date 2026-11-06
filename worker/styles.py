"""12 phong cach cua de bai. Chon bang bien GROUP (so nhom) trong .env."""
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageChops, ImageDraw

COMMON = ", simple, centered single subject, encyclopedia illustration"

STYLES = {
 1:  ("Pixel art", "pixel art, 16-bit sprite, limited color palette, clean square pixels, plain white background", "pixel"),
 2:  ("Van Gogh swirl", "in the style of Vincent van Gogh, swirling thick impasto brush strokes, vivid blue and yellow, post-impressionist", None),
 3:  ("Mondrian geometric", "Piet Mondrian De Stijl, flat primary colors red yellow blue, thick black grid lines, geometric abstraction", "mondrian"),
 4:  ("Ukiyo-e", "ukiyo-e Japanese woodblock print, flat colors, bold outlines, washi paper texture", None),
 5:  ("Watercolor", "watercolor painting, soft translucent washes, paper texture, white background", None),
 6:  ("Neon", "glowing neon light sign art, vibrant luminous neon tube outlines, electric neon glow, pure deep black background, crisp detailed subject", "neon"),
 7:  ("Blueprint", "technical blueprint drawing, white line schematic, on blue paper", "blueprint"),
 8:  ("Black & white woodcut", "black and white woodcut print, linocut, bold carved lines, high contrast engraving", "woodcut"),
 9:  ("Pop art", "pop art, Roy Lichtenstein style, bold black outlines, flat bright colors, ben-day dots", "popart"),
 10: ("Art deco", "art deco poster, symmetrical geometric design, gold and black, elegant 1920s", None),
 11: ("Claymation", "claymation plasticine clay figure, stop motion, soft studio lighting, cute", None),
 12: ("Old newspaper halftone", "old newspaper photo, halftone dots, grayscale print, aged yellow paper", "halftone"),
}


def prompt_for(group, name):
    s = STYLES[group]
    return f"{name}, {s[1]}{COMMON}"


def _pixel(im, out):
    small = im.resize((64, 64), Image.BOX).quantize(colors=24).convert("RGB")
    return small.resize((out, out), Image.NEAREST)


def _woodcut(im, out):
    g = ImageOps.autocontrast(im.convert("L"), cutoff=2)
    return g.point(lambda v: 255 if v > 125 else 0).convert("RGB")


def _blueprint(im, out):
    g = ImageOps.autocontrast(im.convert("L"))
    return ImageOps.colorize(g, black=(245, 248, 255), white=(18, 58, 140))


def _neon(im, out):
    im = ImageEnhance.Color(im).enhance(2.2)
    im = ImageEnhance.Contrast(im).enhance(1.4)
    glow = im.filter(ImageFilter.GaussianBlur(5))
    res = ImageChops.screen(im, glow)
    return res.resize((out, out), Image.LANCZOS)


def _popart(im, out):
    im = ImageEnhance.Color(im).enhance(1.7)
    return ImageOps.posterize(ImageEnhance.Contrast(im).enhance(1.3), 2)


def _mondrian(im, out):
    return ImageOps.posterize(ImageEnhance.Color(im).enhance(1.6), 2)


def _halftone(im, out, cell=6):
    g = ImageOps.autocontrast(im.convert("L"))
    w = out
    g = g.resize((w, w))
    small = g.resize((w // cell, w // cell), Image.BOX)
    canvas = Image.new("RGB", (w, w), (232, 220, 190))
    d = ImageDraw.Draw(canvas)
    px = small.load()
    for y in range(small.height):
        for x in range(small.width):
            r = (1 - px[x, y] / 255) * cell * 0.72
            cx, cy = x * cell + cell / 2, y * cell + cell / 2
            if r > 0.3:
                d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(40, 34, 28))
    return canvas


POST = {"pixel": _pixel, "woodcut": _woodcut, "blueprint": _blueprint, "neon": _neon,
        "popart": _popart, "mondrian": _mondrian, "halftone": _halftone}


def postprocess(group, im, out):
    """Ep dung phong cach bang code + resize ve kich thuoc cuoi (out x out)."""
    im = im.convert("RGB")
    fn = POST.get(STYLES[group][2])
    if fn:
        return fn(im.resize((out, out), Image.LANCZOS), out)
    return im.resize((out, out), Image.LANCZOS)
