"""Extract continuous narrative bill text from hierarchical structure.

This module converts the hierarchical bill structure (Parts → Sections → Subsections → Paragraphs)
into continuous, readable text suitable for display in a "Full Text" tab.

The output is formatted for end-to-end reading like a PDF, without structural breaks from amendments.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fedmcp.clients.bill_text_xml import ParsedBill, BillSection, BillSubsection, BillParagraph, BillSubparagraph


def extract_continuous_text(parsed_bill: ParsedBill, language: str = 'en') -> str:
    """Extract continuous narrative text from parsed bill structure.

    Assembles text in reading order:
    1. Preamble (if present)
    2. Enacting clause
    3. Body sections (Parts → Sections → Subsections → Paragraphs → Subparagraphs)

    Args:
        parsed_bill: Parsed bill structure from BillTextXMLClient
        language: 'en' for English or 'fr' for French

    Returns:
        Formatted continuous text with proper spacing

    Example output:
        PREAMBLE

        Whereas the Parliament of Canada...

        Her Majesty, by and with the advice and consent of the Senate and House of Commons...

        PART I — General Provisions

        1. Short title

        This Act may be cited as the Example Act.

        (1) The following definitions apply...
        (a) "minister" means...
        (i) the Minister of...
    """
    sections = []
    lang_suffix = f"_{language}"

    # 1. Add preamble (if present)
    preamble = getattr(parsed_bill, f"preamble{lang_suffix}", None)
    if preamble:
        sections.append("PREAMBLE\n\n" + preamble.strip())

    # 2. Add enacting clause
    enacting = getattr(parsed_bill, f"enacting_clause{lang_suffix}", None)
    if enacting:
        sections.append(enacting.strip())

    # 3. Add body text (Parts with sections, then loose sections)
    if parsed_bill.parts:
        for part in parsed_bill.parts:
            part_title = getattr(part, f"title{lang_suffix}", None) or getattr(part, "title_en", "")

            # Part heading
            part_heading = f"PART {_int_to_roman(part.number)}"
            if part_title:
                part_heading += f" — {part_title}"
            sections.append(part_heading)

            # Sections within this part
            for section in part.sections:
                sections.append(_format_section(section, language))

    # Add loose sections (not in parts)
    for section in parsed_bill.sections:
        sections.append(_format_section(section, language))

    # Join all sections with double newlines for readability
    return "\n\n".join(sections)


def _format_section(section: BillSection, language: str = 'en') -> str:
    """Format a section with all nested content.

    Args:
        section: Bill section to format
        language: 'en' or 'fr'

    Returns:
        Formatted section text with numbering and structure
    """
    lang_suffix = f"_{language}"
    parts = []

    # Section number and marginal note (title)
    header = f"{section.number}."
    marginal_note = getattr(section, f"marginal_note{lang_suffix}", None)
    if marginal_note:
        header += f" {marginal_note}"
    parts.append(header)

    # Section text (if any)
    section_text = getattr(section, f"text{lang_suffix}", None)
    if section_text:
        parts.append(section_text.strip())

    # Subsections
    for subsection in section.subsections:
        subsection_text = _format_subsection(subsection, language)
        if subsection_text:
            parts.append(subsection_text)

    return "\n\n".join(parts)


def _format_subsection(subsection: BillSubsection, language: str = 'en') -> str:
    """Format a subsection with paragraphs and subparagraphs.

    Args:
        subsection: Bill subsection to format
        language: 'en' or 'fr'

    Returns:
        Formatted subsection text
    """
    lang_suffix = f"_{language}"
    parts = []

    # Subsection number and text
    text = getattr(subsection, f"text{lang_suffix}", None)
    if text:
        subsection_line = f"({subsection.number}) {text.strip()}"
        parts.append(subsection_line)

    # Paragraphs
    for paragraph in subsection.paragraphs:
        para_text = _format_paragraph(paragraph, language)
        if para_text:
            parts.append(para_text)

    return "\n\n".join(parts)


def _format_paragraph(paragraph: BillParagraph, language: str = 'en') -> str:
    """Format a paragraph with subparagraphs.

    Args:
        paragraph: Bill paragraph to format
        language: 'en' or 'fr'

    Returns:
        Formatted paragraph text
    """
    lang_suffix = f"_{language}"
    parts = []

    # Paragraph letter and text
    text = getattr(paragraph, f"text{lang_suffix}", None)
    if text:
        para_line = f"({paragraph.letter}) {text.strip()}"
        parts.append(para_line)

    # Subparagraphs (indented with 2 spaces)
    for subpara in paragraph.subparagraphs:
        subpara_text = _format_subparagraph(subpara, language)
        if subpara_text:
            parts.append("  " + subpara_text)  # Indent subparagraphs

    return "\n\n".join(parts)


def _format_subparagraph(subpara: BillSubparagraph, language: str = 'en') -> str:
    """Format a subparagraph.

    Args:
        subpara: Bill subparagraph to format
        language: 'en' or 'fr'

    Returns:
        Formatted subparagraph text
    """
    lang_suffix = f"_{language}"
    text = getattr(subpara, f"text{lang_suffix}", None)
    if text:
        return f"({subpara.numeral}) {text.strip()}"
    return ""


def _int_to_roman(num: int) -> str:
    """Convert integer to Roman numeral for Part numbering.

    Args:
        num: Integer to convert (1-99)

    Returns:
        Roman numeral string (I, II, III, IV, V, etc.)

    Examples:
        >>> _int_to_roman(1)
        'I'
        >>> _int_to_roman(4)
        'IV'
        >>> _int_to_roman(9)
        'IX'
        >>> _int_to_roman(45)
        'XLV'
    """
    val = [
        1000, 900, 500, 400,
        100, 90, 50, 40,
        10, 9, 5, 4,
        1
    ]
    syms = [
        "M", "CM", "D", "CD",
        "C", "XC", "L", "XL",
        "X", "IX", "V", "IV",
        "I"
    ]
    roman_num = ''
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman_num += syms[i]
            num -= val[i]
        i += 1
    return roman_num


def validate_extracted_text(text: str, bill: ParsedBill) -> bool:
    """Validate extracted text quality.

    Performs basic sanity checks to ensure extraction was successful:
    - Minimum length (avoid empty extractions)
    - Contains section numbers
    - Section count approximately matches expected

    Args:
        text: Extracted full text
        bill: Original parsed bill

    Returns:
        True if text passes validation, False otherwise
    """
    # Check 1: Minimum length (>100 chars for meaningful content)
    if len(text) < 100:
        return False

    # Check 2: Contains section numbers (pattern: "1." or "123.")
    if not re.search(r'\b\d+\.\s', text):
        return False

    # Check 3: Section count matches expected (±20% tolerance)
    # Count total sections in all parts + loose sections
    expected_sections = sum(len(part.sections) for part in bill.parts) + len(bill.sections)
    if expected_sections > 0:
        found_sections = len(re.findall(r'^\d+\.\s', text, re.MULTILINE))

        # Allow 80-120% of expected count (some sections may have no text)
        min_expected = int(expected_sections * 0.8)
        max_expected = int(expected_sections * 1.2)

        if not (min_expected <= found_sections <= max_expected):
            return False

    # All checks passed
    return True
