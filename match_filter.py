import operator
import re
import fnmatch

"""
Matches `value` against `pattern` using shell-style wildcards.
- `*` matches any number of characters
- `?` matches a single character
"""
def wildcard_match(value: str, pattern: str, ignore_case: bool = True) -> bool:
    if ignore_case:
        value, pattern = value.lower(), pattern.lower()
    return fnmatch.fnmatchcase(value.strip(), pattern.strip())

def parse_numeric_filter(expr):
    ops = {
        ">=": operator.ge,
        "<=": operator.le,
        ">": operator.gt,
        "<": operator.lt,
        "==": operator.eq
    }
    for op_str, op_func in ops.items():
        if expr.strip().startswith(op_str):
            try:
                value = float(expr[len(op_str):].strip())
                return op_func, value
            except ValueError:
                return None, None
    return None, None

def match_filter(value, pattern, column=None):
    numeric_columns = {"gpu_ram", "cpu_ram", "dph_total", "score", "reliability", "disk_space"}
    is_numeric = isinstance(value, (int, float))

    if is_numeric or column in numeric_columns:
        for p in pattern.split(','):
            p = p.strip()
            if re.match(r'^\s*(>=|<=|==|<|>)', p):
                op_func, ref_val = parse_numeric_filter(p)
                if op_func and op_func(value, ref_val):
                    return True
        return False

    if isinstance(value, str) and isinstance(pattern, str):
        return wildcard_match(value, pattern)

    return False
