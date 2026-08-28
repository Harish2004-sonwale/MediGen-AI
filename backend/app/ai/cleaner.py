import re


def clean_clinical_text(text: str) -> str:
    """Normalize whitespace and formatting while preserving clinical facts, terminology, and numbers."""
    if not text:
        return ""

    # Replace carriage returns
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    # Replace non-breaking spaces and irregular unicode spaces with standard space
    normalized = re.sub(r"[\u00A0\u1680\u2000-\u200B\u202F\u205F\u3000]", " ", normalized)

    # Normalize horizontal whitespace (spaces, tabs) while keeping newlines intact
    normalized = re.sub(r"[ \t]+", " ", normalized)

    # Trim spaces from each individual line
    lines = [line.strip() for line in normalized.split("\n")]

    # Remove excessive blank lines (collapse 3+ newlines into 2)
    cleaned_lines: list[str] = []
    blank_count = 0
    for line in lines:
        if not line:
            blank_count += 1
            if blank_count <= 1:
                cleaned_lines.append("")
        else:
            blank_count = 0
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()
