import re

_ones = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

def _num_to_words(n: int) -> str:
    if n == 0: return "zero"
    if n < 20: return _ones[n]
    if n < 100: return _tens[n // 10] + (" " + _ones[n % 10] if n % 10 != 0 else "")
    if n < 1000: return _ones[n // 100] + " hundred" + (" " + _num_to_words(n % 100) if n % 100 != 0 else "")
    return str(n)

def _currency_replacer(match):
    num_str = match.group(1).replace(",", "")
    try:
        val = int(num_str)
        if val < 1000:
            return f"{_num_to_words(val)} rupees"
    except ValueError:
        pass
    return f"{num_str} rupees"

def _acronym_replacer(match):
    # Only hyphenate if it's purely letters
    word = match.group(1)
    return "-".join(list(word))

def normalize_for_tts(text: str) -> str:
    if not text:
        return text
    # 1. Replace code blocks
    text = re.sub(r'```.*?```', 'Here is the code', text, flags=re.DOTALL)
    
    # 2. Strip markdown (bold, italic)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'#+\s*(.*?)\n', r'\1\n', text)
    
    # 3. Normalize Indian currencies (₹500 -> five hundred rupees)
    text = re.sub(r'₹\s*([0-9,]+)', _currency_replacer, text)
    
    # 4. Normalize acronyms (API -> A-P-I)
    text = re.sub(r'\b([A-Z]{2,})\b', _acronym_replacer, text)
    
    return text.strip()
