def _parse_module_code_and_name(module_text: str) -> tuple[str, str]:
    parts = module_text.split()
    if len(parts) < 2:
        return module_text, ""

    code_parts = []
    name_parts = []

    for i, part in enumerate(parts):
        if not name_parts:
            # Check if this part looks like a module code component
            is_code_part = (
                part.isdigit()  # Pure numbers like "110", "1214"
                or (
                    any(c.isdigit() for c in part)
                    and any(c.isalpha() for c in part)
                    and part.isalnum()
                )  # Alphanumeric like "BDSC1236"
                or (
                    part.isalpha() and i == 0
                )  # First part if alphabetic like "BROD", "SETD304"
            )

            if is_code_part:
                code_parts.append(part)
                # Check if we should start collecting name parts
                if i + 1 < len(parts):
                    next_part = parts[i + 1]
                    # Start name if next part is clearly a word (not a number, contains special chars, or is a long alphabetic word)
                    if (
                        next_part.startswith("&")
                        or (
                            next_part.isalpha()
                            and len(next_part) >= 3
                            and not next_part.isdigit()
                        )
                        or not next_part.isalnum()
                    ):
                        # Look ahead to see if there are more code-like parts
                        remaining_parts = parts[i + 1 :]
                        if (
                            len(remaining_parts) > 1
                            and not remaining_parts[0].isdigit()
                        ):
                            name_parts.extend(remaining_parts)
                            break
                        elif len(remaining_parts) == 1:
                            name_parts.extend(remaining_parts)
                            break
            else:
                name_parts.extend(parts[i:])
                break

    if not name_parts:
        if len(parts) >= 3:
            code_parts = parts[:2]
            name_parts = parts[2:]
        else:
            code_parts = [parts[0]]
            name_parts = parts[1:]

    code = " ".join(code_parts)
    name = " ".join(name_parts)

    return code, name


# Test cases
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
