import re
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_BIDI = True
except ImportError:
    HAS_BIDI = False

def is_rtl(text: str) -> bool:
    """Check if the text contains RTL characters (Arabic, Hebrew, Persian, etc.)."""
    if not text:
        return False
    # Range of Arabic, Hebrew, Persian, etc. characters
    rtl_pattern = re.compile(r'[\u0590-\u08FF\uFB1D-\uFDFD\uFE70-\uFEFC]')
    return bool(rtl_pattern.search(text))

def apply_bidi(text: str) -> str:
    """Apply Arabic reshaping and BiDi algorithm for correct RTL display."""
    if not text or not is_rtl(text) or not HAS_BIDI:
        return text
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text
