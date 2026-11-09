import sys
sys.path.insert(0, '.')
import gemini_engine

caption = "Chị Trân - 0328583344 - giảm 10%"
name, phone = gemini_engine.extract_customer_and_phone_from_caption(caption)
print(f"Extracted name: '{name}', phone: '{phone}'")

disc_k, is_pct, pct_val = gemini_engine.parse_discount_expression(caption, 4500)
print(f"Discount: {disc_k}k, is_pct: {is_pct}, pct_val: {pct_val}%")

