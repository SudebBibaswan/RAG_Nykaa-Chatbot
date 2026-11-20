"""Rule-based enrichment. Every derived field is parsed from the product title or
the numeric columns - nothing is generated, so nothing can be invented.
"""
from __future__ import annotations

import re

# Ordered: the first matching rule wins, so more specific phrases come first.
# (pattern, product_type, category)
TYPE_RULES: list[tuple[str, str, str]] = [
    # combos and kits first - they often contain other type words
    (r"\b(combo|duo|trio|gift set|routine kit|value pack|regime|routine)\b| \+ ", "Combo / Gift Set", "Combos & Kits"),
    (r"\bfacial kit\b", "Facial Kit", "Skin Care"),
    (r"\b(pouch|makeup bag|vanity|tote|case|organi[sz]er)\b", "Bags & Pouches", "Accessories"),
    (r"\bbronz(er|ing)\b|\bcontour\b", "Bronzer / Contour", "Makeup"),
    (r"\bice roller\b|\bface roller\b|\bgua sha\b", "Tools & Brushes", "Tools"),
    (r"\bmanicure\b|\bpedicure\b", "Nail Polish", "Nails"),
    (r"\b(matte )?ink\b(?!.*foundation)", "Lipstick", "Makeup"),
    (r"\bbaby lips\b|\blip\b", "Lip Balm", "Makeup"),
    # lips
    (r"\blip ?(balm|care|butter)\b", "Lip Balm", "Makeup"),
    (r"\blip ?gloss\b|\bgloss\b", "Lip Gloss", "Makeup"),
    (r"\blip ?liner\b|\blip pencil\b", "Lip Liner", "Makeup"),
    (r"\blip ?(crayon|cream|stain|tint|colou?r|stick)\b|\blipstick\b|\bliquid lip", "Lipstick", "Makeup"),
    # eyes
    (r"\bkajal\b|\bkohl\b", "Kajal", "Makeup"),
    (r"\beye ?liner\b|\bliner\b", "Eyeliner", "Makeup"),
    (r"\bmascara\b", "Mascara", "Makeup"),
    (r"\b(eye ?shadow|eyeshadow|palette)\b", "Eyeshadow / Palette", "Makeup"),
    (r"\bbrow\b|\beyebrow\b", "Brow", "Makeup"),
    (r"\blash(es)?\b", "False Lashes", "Makeup"),
    (r"\beye pencil\b|\bgel eye\b", "Eye Pencil", "Makeup"),
    # face makeup
    (r"\bfoundation\b|\bbb cream\b|\bcc cream\b", "Foundation / BB-CC", "Makeup"),
    (r"\bconcealer\b|\bcolou?r corrector\b", "Concealer", "Makeup"),
    (r"\bprimer\b", "Primer", "Makeup"),
    (r"\bcompact\b|\bpressed powder\b", "Compact", "Makeup"),
    (r"\bsetting (spray|powder)\b|\bfixer\b|\bloose (finishing )?powder\b|\bfinishing powder\b|\bpowder\b", "Setting Spray / Powder", "Makeup"),
    (r"\bblush\b|\bblusher\b", "Blush", "Makeup"),
    (r"\bhighlighter\b|\billuminator\b|\bstrobe\b", "Highlighter", "Makeup"),
    (r"\bbronzer\b|\bcontour\b", "Bronzer / Contour", "Makeup"),
    # nails
    (r"\bnail polish remover\b|\bremover\b", "Makeup / Nail Remover", "Makeup"),
    (r"\bnail\b|\benamel\b|\blacquer\b", "Nail Polish", "Nails"),
    # tools
    (r"\bbrush\b|\bsponge\b|\bblender\b|\bcurler\b|\bsharpener\b|\btweezer\b", "Tools & Brushes", "Tools"),
    # hair
    (r"\bshampoo\b", "Shampoo", "Hair Care"),
    (r"\bconditioner\b", "Conditioner", "Hair Care"),
    (r"\bhair (oil|tonic)\b", "Hair Oil", "Hair Care"),
    (r"\bhair (mask|spa|pack)\b", "Hair Mask", "Hair Care"),
    (r"\bhair colou?r\b|\bcasting creme\b|\bhair dye\b|\bexcellence creme\b", "Hair Colour", "Hair Care"),
    (r"\bhair serum\b|\bhair (cream|gel|spray)\b", "Hair Styling / Serum", "Hair Care"),
    # skin
    (r"\bsun ?screen\b|\bsunblock\b|\bsun (cream|lotion|gel|stick)\b|\bspf ?\d+\b.*\b(lotion|gel)\b", "Sunscreen", "Skin Care"),
    (r"\bsheet mask\b", "Sheet Mask", "Skin Care"),
    (r"\b(face|clay|peel|sleeping|mud) ?(mask|pack)\b|\bmask\b|\bface pack\b", "Face Mask / Pack", "Skin Care"),
    (r"\bface ?wash\b|\bcleanser\b|\bcleansing (foam|gel|milk|balm|oil)\b|\bfoaming\b", "Face Wash / Cleanser", "Skin Care"),
    (r"\bmicellar\b|\bmakeup remover\b", "Micellar / Makeup Remover", "Skin Care"),
    (r"\bscrub\b|\bexfoliat", "Scrub / Exfoliator", "Skin Care"),
    (r"\btoner\b|\bmist\b|\bessence\b", "Toner / Mist", "Skin Care"),
    (r"\bserum\b|\bampoule\b", "Face Serum", "Skin Care"),
    (r"\beye cream\b|\bunder eye\b", "Eye Cream", "Skin Care"),
    (r"\bnight cream\b", "Night Cream", "Skin Care"),
    (r"\bday cream\b", "Day Cream", "Skin Care"),
    (r"\bmoisturi[sz]", "Moisturiser", "Skin Care"),
    (r"\bemulsion\b|\bwater ?(cream|creme|bomb)\b", "Moisturiser", "Skin Care"),
    (r"\bface (cream|gel|oil)\b|\bmassage cream\b|\bcream\b|\bcreme\b", "Face Cream", "Skin Care"),
    (r"\bmasque\b|\bpeeling\b|\bpolish\b", "Face Mask / Pack", "Skin Care"),
    (r"pencil\b", "Eye Pencil", "Makeup"),
    (r"\bwipes?\b|\bcotton pads?\b", "Wipes & Pads", "Skin Care"),
    (r"\bmousse\b|\bdeep cleansing\b", "Face Wash / Cleanser", "Skin Care"),
    (r"\bafter ?shave\b|\bshaving\b", "Shaving", "Men's Grooming"),
    (r"\bspot patch\b|\bpimple patch\b", "Spot Patch", "Skin Care"),
    (r"\bsindoor\b", "Sindoor", "Makeup"),
    (r"\bshimmer\b", "Shimmer / Highlighter", "Makeup"),
    (r"\btoothpaste\b", "Oral Care", "Bath & Body"),
    (r"\bhair wrap\b", "Hair Accessories", "Hair Care"),
    (r"\bfoot ?cream\b|\bheels?\b", "Hand & Foot Care", "Bath & Body"),
    # bath and body
    (r"\bbody lotion\b|\bbody milk\b|\blotion\b", "Body Lotion", "Bath & Body"),
    (r"\bbody wash\b|\bshower gel\b|\bshower\b", "Body Wash / Shower Gel", "Bath & Body"),
    (r"\bsoap\b|\bbathing bar\b|\bbath bar\b", "Soap", "Bath & Body"),
    (r"\bbody butter\b|\bbody (oil|scrub|cream)\b", "Body Care", "Bath & Body"),
    (r"\bhand (cream|wash)\b|\bfoot\b", "Hand & Foot Care", "Bath & Body"),
    (r"\bdeo(dorant)?\b|\broll[- ]on\b|\bantiperspirant\b", "Deodorant", "Bath & Body"),
    (r"\bhair removal\b|\bwax strips?\b", "Hair Removal", "Bath & Body"),
    # fragrance
    (r"\bperfume\b|\beau de\b|\bfragrance\b|\bbody mist\b|\bedp\b|\bedt\b", "Fragrance", "Fragrance"),
    # generic fallbacks
    (r"\bgel\b", "Gel", "Skin Care"),
    (r"\boil\b", "Oil", "Skin Care"),
    (r"\bkit\b|\bset\b", "Kit / Set", "Combos & Kits"),
]
_COMPILED = [(re.compile(p, re.I), t, c) for p, t, c in TYPE_RULES]

# Claims we accept only if the title literally states them.
CLAIM_RULES: list[tuple[str, str]] = [
    (r"\bspf ?(\d+)", "SPF {0}"),
    (r"\bpa\+{2,4}", "PA rated"),
    (r"paraben[- ]?free|no paraben|paraben (and|&) sul", "Paraben free"),
    (r"sulph?ate[- ]?free|no sulph?ates?|sulph?ate (and|&)|and sulph?ate", "Sulphate free"),
    (r"\bwaterproof\b", "Waterproof"),
    (r"\bsmudge ?proof\b", "Smudge proof"),
    (r"\btransfer ?proof\b", "Transfer proof"),
    (r"\blong ?(wear|lasting|stay)\b|\b\d+ ?h(r|rs|our)?\b", "Long wear"),
    (r"\bmatte\b", "Matte finish"),
    (r"\bvegan\b", "Vegan"),
    (r"\bcruelty[- ]free\b", "Cruelty free"),
    (r"\bvitamin ?c\b", "Vitamin C"),
    (r"\bniacinamide\b", "Niacinamide"),
    (r"\bhyaluronic\b", "Hyaluronic acid"),
    (r"\bretinol\b", "Retinol"),
    (r"\bsalicylic\b", "Salicylic acid"),
    (r"\banti[- ]?(ageing|aging)\b", "Anti-ageing"),
    (r"\banti[- ]?dandruff\b", "Anti-dandruff"),
    (r"\banti[- ]?hair ?fall\b|\bhair ?fall\b", "Hair-fall control"),
    (r"\bhair growth\b", "Hair growth"),
    (r"\bacne\b|\bpimple\b|\bblemish\b", "Acne / blemish"),
    (r"\bbrighten|\bglow|\bradian", "Glow / brightening"),
    (r"\bhydrat|\bmoisturi[sz]", "Hydrating"),
    (r"\bmini\b|\btravel size\b", "Mini size"),
]
_CLAIMS = [(re.compile(p, re.I), label) for p, label in CLAIM_RULES]

SKIN_HAIR_RULES: list[tuple[str, str]] = [
    (r"\boily\b", "Oily skin"),
    (r"\bdry skin\b|\bvery dry\b", "Dry skin"),
    (r"\bsensitive\b", "Sensitive skin"),
    (r"\bnormal\b", "Normal skin"),
    (r"\ball skin types?\b", "All skin types"),
    (r"\bcombination\b", "Combination skin"),
    (r"\bdry (and|&) damaged hair\b|\bdamaged hair\b", "Damaged hair"),
    (r"\bfrizz", "Frizzy hair"),
    (r"\bcolou?r(ed)?[- ]treated\b", "Colour-treated hair"),
    (r"\bmen\b|\bfor men\b", "For men"),
    (r"\bkids?\b|\bbaby\b|\bdisney\b", "For kids"),
]
_SKIN_HAIR = [(re.compile(p, re.I), label) for p, label in SKIN_HAIR_RULES]

SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s?(ml|g|gm|kg|l|pcs?|pieces)\b", re.I)
PACK_RE = re.compile(r"\bpack of (\d+)\b|\b(\d+)\s?pcs?\b", re.I)


def product_type(title: str) -> tuple[str, str]:
    for rx, ptype, cat in _COMPILED:
        if rx.search(title):
            return ptype, cat
    return "Other", "Other"


def claims(title: str) -> list[str]:
    out: list[str] = []
    for rx, label in _CLAIMS:
        m = rx.search(title)
        if m:
            text = label.format(*m.groups()) if "{0}" in label else label
            if text not in out:
                out.append(text)
    return out


def suitability(title: str) -> list[str]:
    return [label for rx, label in _SKIN_HAIR if rx.search(title)]


def variant(title: str, brand: str) -> str:
    """Shade or variant: the text after the last ' - ' in a title, when it is short."""
    if " - " not in title:
        return ""
    tail = title.rsplit(" - ", 1)[1].strip()
    # long tails are usually a second product name in a combo, not a shade
    if len(tail) > 40 or tail.lower().startswith(brand.lower().split()[0]):
        return ""
    return tail


def base_name(title: str, var: str) -> str:
    if var and title.endswith(var):
        return title[: -len(var)].rstrip(" -")
    return title


def size(title: str) -> str:
    m = SIZE_RE.search(title)
    return f"{m.group(1)} {m.group(2).lower()}" if m else ""


def price_band(price: float) -> str:
    if price < 250:
        return "under ₹250"
    if price < 500:
        return "₹250–499"
    if price < 1000:
        return "₹500–999"
    if price < 2000:
        return "₹1,000–1,999"
    return "₹2,000 and above"


def discount_pct(price: float, mrp: float) -> int:
    if mrp <= 0 or price >= mrp:
        return 0
    return round((mrp - price) / mrp * 100)
