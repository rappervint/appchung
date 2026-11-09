import re
import unicodedata

def remove_accents(input_str):
    if not input_str:
        return ""
    s = unicodedata.normalize('NFD', input_str)
    s = "".join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.replace('đ', 'd').replace('Đ', 'D')

def parse_price_str(val_str):
    s = remove_accents(val_str).lower().replace(' ', '')
    # 7tr5, 3tr5, 9tr5, 7.5tr, 7,5tr
    m_tr_split = re.search(r'(\d+)\s*(?:tr|trieu)\s*(\d+)', s)
    if m_tr_split:
        main_v = int(m_tr_split.group(1))
        dec_v = int(m_tr_split.group(2))
        num = main_v + dec_v / (10 ** len(m_tr_split.group(2)))
        return f"{int(round(num * 1_000_000)):,} đ"
    m_tr = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:tr|trieu)', s)
    if m_tr:
        num = float(m_tr.group(1).replace(',', '.'))
        return f"{int(round(num * 1_000_000)):,} đ"
    m_k = re.search(r'(\d+)\s*k', s)
    if m_k:
        num = int(m_k.group(1))
        return f"{num * 1_000:,} đ"
    m_d = re.search(r'(\d+)', s)
    if m_d:
        num = int(m_d.group(1))
        if num < 100:
            return f"{num * 1_000_000:,} đ"
        return f"{num:,} đ"
    return val_str.strip()

for test_p in ["6tr", "7tr5", "12tr", "3tr5", "9tr5", "+1tr"]:
    print(f"{test_p} -> {parse_price_str(test_p)}")

