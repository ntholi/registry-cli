def _parse_module_code_and_name(module_text: str) -> tuple[str, str]:
    parts = module_text.split()
    if len(parts) < 2:
        return module_text, ""

    code_parts = []
    name_parts = []

    if parts[0].isalnum():
        code_parts.append(parts[0])
    else:
        return "", module_text

    if len(parts) > 1 and parts[1].isdigit():
        code_parts.append(parts[1])
        name_parts = parts[2:] if len(parts) > 2 else []
    else:
        name_parts = parts[1:]

    code = " ".join(code_parts)
    name = " ".join(name_parts)

    return code, name


test_cases = [
    "BROD 110 Media & Society",
    "BDSC1236 Computer Graphics",
    "BDDCS 1214 Introduction to Computer Design",
    "BROD 110 Media & Society:",
    "CADD101 Computer Aided Design & Drafting 1",
    "BSDC1212 Java Programming 2",
    "SETD304 Set & Stage Design Studio 3",
    "AIDA213 2D Animation",
    "DIAN2112 2D Animation 2",
]

expected_results = [
    ("BROD 110", "Media & Society"),
    ("BDSC1236", "Computer Graphics"),
    ("BDDCS 1214", "Introduction to Computer Design"),
    ("BROD 110", "Media & Society:"),
    ("CADD101", "Computer Aided Design & Drafting 1"),
    ("BSDC1212", "Java Programming 2"),
    ("SETD304", "Set & Stage Design Studio 3"),
    ("AIDA213", "2D Animation"),
    ("DIAN2112", "2D Animation 2"),
]

print("Testing _parse_module_code_and_name function:")
print("=" * 60)

for i, test_case in enumerate(test_cases):
    code, name = _parse_module_code_and_name(test_case)
    expected_code, expected_name = expected_results[i]

    print(f"Input: {test_case}")
    print(f"Expected: Code='{expected_code}', Name='{expected_name}'")
    print(f"Actual:   Code='{code}', Name='{name}'")

    is_correct = (code == expected_code) and (name == expected_name)
    print(f"Result: {'✓ PASS' if is_correct else '✗ FAIL'}")
    print("-" * 60)
