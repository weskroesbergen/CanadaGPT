"""Unit tests for bill full text extraction."""
import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "fedmcp" / "src"))

from fedmcp_pipeline.ingest.bill_full_text_extractor import (
    extract_continuous_text,
    validate_extracted_text,
    _format_section,
    _format_subsection,
    _format_paragraph,
    _format_subparagraph,
    _int_to_roman,
)
from fedmcp.clients.bill_text_xml import (
    ParsedBill,
    BillPart,
    BillSection,
    BillSubsection,
    BillParagraph,
    BillSubparagraph,
    BillStage,
)


def test_int_to_roman():
    """Test integer to Roman numeral conversion."""
    assert _int_to_roman(1) == "I"
    assert _int_to_roman(2) == "II"
    assert _int_to_roman(3) == "III"
    assert _int_to_roman(4) == "IV"
    assert _int_to_roman(5) == "V"
    assert _int_to_roman(9) == "IX"
    assert _int_to_roman(10) == "X"
    assert _int_to_roman(45) == "XLV"
    assert _int_to_roman(99) == "XCIX"


def test_format_subparagraph():
    """Test formatting of a subparagraph."""
    subpara = BillSubparagraph(
        id="test:s1.1.a.i",
        anchor_id="test:s1.1.a.i",
        sequence=1,
        numeral="i",
        text_en="the Minister of Health",
        text_fr="le ministre de la Santé",
    )

    # English
    text_en = _format_subparagraph(subpara, 'en')
    assert text_en == "(i) the Minister of Health"

    # French
    text_fr = _format_subparagraph(subpara, 'fr')
    assert text_fr == "(i) le ministre de la Santé"


def test_format_paragraph():
    """Test formatting of a paragraph with subparagraphs."""
    paragraph = BillParagraph(
        id="test:s1.1.a",
        anchor_id="test:s1.1.a",
        sequence=1,
        letter="a",
        text_en='"minister" means',
        text_fr='"ministre" s\'entend',
        subparagraphs=[
            BillSubparagraph(
                id="test:s1.1.a.i",
                anchor_id="test:s1.1.a.i",
                sequence=1,
                numeral="i",
                text_en="the Minister of Health",
                text_fr="le ministre de la Santé",
            ),
            BillSubparagraph(
                id="test:s1.1.a.ii",
                anchor_id="test:s1.1.a.ii",
                sequence=2,
                numeral="ii",
                text_en="the Minister of Environment",
                text_fr="le ministre de l'Environnement",
            ),
        ],
    )

    # English
    text_en = _format_paragraph(paragraph, 'en')
    assert '(a) "minister" means' in text_en
    assert "  (i) the Minister of Health" in text_en  # Indented
    assert "  (ii) the Minister of Environment" in text_en

    # French
    text_fr = _format_paragraph(paragraph, 'fr')
    assert '(a) "ministre" s\'entend' in text_fr
    assert "  (i) le ministre de la Santé" in text_fr


def test_format_subsection():
    """Test formatting of a subsection with paragraphs."""
    subsection = BillSubsection(
        id="test:s1.1",
        anchor_id="test:s1.1",
        sequence=1,
        number="1",
        text_en="The following definitions apply in this Act.",
        text_fr="Les définitions qui suivent s'appliquent à la présente loi.",
        paragraphs=[
            BillParagraph(
                id="test:s1.1.a",
                anchor_id="test:s1.1.a",
                sequence=1,
                letter="a",
                text_en='"minister" means the Minister of Health',
                text_fr='"ministre" s\'entend du ministre de la Santé',
            ),
            BillParagraph(
                id="test:s1.1.b",
                anchor_id="test:s1.1.b",
                sequence=2,
                letter="b",
                text_en='"regulation" means a regulation made under this Act',
                text_fr='"règlement" s\'entend d\'un règlement pris en vertu de la présente loi',
            ),
        ],
    )

    # English
    text_en = _format_subsection(subsection, 'en')
    assert "(1) The following definitions apply" in text_en
    assert '(a) "minister" means' in text_en
    assert '(b) "regulation" means' in text_en

    # French
    text_fr = _format_subsection(subsection, 'fr')
    assert "(1) Les définitions qui suivent" in text_fr
    assert '(a) "ministre"' in text_fr
    assert '(b) "règlement"' in text_fr


def test_format_section_simple():
    """Test formatting of a simple section with text only."""
    section = BillSection(
        id="test:s1",
        anchor_id="test:s1",
        sequence=1,
        number="1",
        marginal_note_en="Short title",
        marginal_note_fr="Titre abrégé",
        text_en="This Act may be cited as the Test Act.",
        text_fr="Loi abrégée : Loi test.",
    )

    # English
    text_en = _format_section(section, 'en')
    assert "1. Short title" in text_en
    assert "This Act may be cited as the Test Act." in text_en

    # French
    text_fr = _format_section(section, 'fr')
    assert "1. Titre abrégé" in text_fr
    assert "Loi abrégée : Loi test." in text_fr


def test_format_section_with_subsections():
    """Test formatting of a section with subsections."""
    section = BillSection(
        id="test:s2",
        anchor_id="test:s2",
        sequence=2,
        number="2",
        marginal_note_en="Definitions",
        text_en="",
        subsections=[
            BillSubsection(
                id="test:s2.1",
                anchor_id="test:s2.1",
                sequence=1,
                number="1",
                text_en="The following definitions apply in this Act.",
                paragraphs=[
                    BillParagraph(
                        id="test:s2.1.a",
                        anchor_id="test:s2.1.a",
                        sequence=1,
                        letter="a",
                        text_en='"minister" means the Minister of Health',
                    ),
                ],
            ),
        ],
    )

    text_en = _format_section(section, 'en')
    assert "2. Definitions" in text_en
    assert "(1) The following definitions apply" in text_en
    assert '(a) "minister" means' in text_en


def test_extract_simple_bill():
    """Test extraction of a simple bill with one section."""
    bill = ParsedBill(
        bill_number="C-1",
        parliament=45,
        session=1,
        session_str="45-1",
        stage=BillStage.FIRST_READING,
        version_number=1,
        title_en="An Act respecting tests",
        title_fr="Loi concernant les tests",
        short_title_en="Test Act",
        short_title_fr="Loi test",
        sponsor_name=None,
        sponsor_riding=None,
        summary_en=None,
        summary_fr=None,
        preamble_en=None,
        preamble_fr=None,
        enacting_clause_en="Her Majesty, by and with the advice and consent of the Senate and House of Commons of Canada, enacts as follows:",
        enacting_clause_fr="Sa Majesté, sur l'avis et avec le consentement du Sénat et de la Chambre des communes du Canada, édicte:",
        parts=[],
        sections=[
            BillSection(
                id="test:s1",
                anchor_id="test:s1",
                sequence=1,
                number="1",
                marginal_note_en="Short title",
                marginal_note_fr="Titre abrégé",
                text_en="This Act may be cited as the Test Act.",
                text_fr="Loi abrégée : Loi test.",
            ),
        ],
        definitions=[],
    )

    # English
    text_en = extract_continuous_text(bill, 'en')
    assert "Her Majesty, by and with the advice" in text_en
    assert "1. Short title" in text_en
    assert "This Act may be cited as the Test Act." in text_en

    # French
    text_fr = extract_continuous_text(bill, 'fr')
    assert "Sa Majesté, sur l'avis" in text_fr
    assert "1. Titre abrégé" in text_fr
    assert "Loi abrégée : Loi test." in text_fr


def test_extract_bill_with_preamble():
    """Test extraction of a bill with preamble."""
    bill = ParsedBill(
        bill_number="C-2",
        parliament=45,
        session=1,
        session_str="45-1",
        stage=BillStage.FIRST_READING,
        version_number=1,
        title_en="An Act respecting tests",
        title_fr="Loi concernant les tests",
        short_title_en="Test Act",
        short_title_fr=None,
        sponsor_name=None,
        sponsor_riding=None,
        summary_en=None,
        summary_fr=None,
        preamble_en="Whereas the Parliament of Canada recognizes the importance of testing;",
        preamble_fr="Attendu que le Parlement du Canada reconnaît l'importance des tests;",
        enacting_clause_en="Now, therefore, Her Majesty enacts as follows:",
        enacting_clause_fr="Sa Majesté édicte:",
        parts=[],
        sections=[
            BillSection(
                id="test:s1",
                anchor_id="test:s1",
                sequence=1,
                number="1",
                marginal_note_en="Purpose",
                text_en="The purpose of this Act is to test.",
            ),
        ],
        definitions=[],
    )

    # English
    text_en = extract_continuous_text(bill, 'en')
    assert "PREAMBLE" in text_en
    assert "Whereas the Parliament of Canada recognizes" in text_en
    assert "Now, therefore, Her Majesty enacts" in text_en
    assert "1. Purpose" in text_en

    # French
    text_fr = extract_continuous_text(bill, 'fr')
    assert "PREAMBLE" in text_fr
    assert "Attendu que le Parlement du Canada reconnaît" in text_fr


def test_extract_bill_with_parts():
    """Test extraction of a bill with Parts."""
    bill = ParsedBill(
        bill_number="C-3",
        parliament=45,
        session=1,
        session_str="45-1",
        stage=BillStage.FIRST_READING,
        version_number=1,
        title_en="An Act respecting tests",
        title_fr=None,
        short_title_en=None,
        short_title_fr=None,
        sponsor_name=None,
        sponsor_riding=None,
        summary_en=None,
        summary_fr=None,
        preamble_en=None,
        preamble_fr=None,
        enacting_clause_en="Her Majesty enacts as follows:",
        enacting_clause_fr=None,
        parts=[
            BillPart(
                id="test:part1",
                anchor_id="test:part1",
                sequence=1,
                number=1,
                title_en="General Provisions",
                title_fr="Dispositions générales",
                sections=[
                    BillSection(
                        id="test:s1",
                        anchor_id="test:s1",
                        sequence=1,
                        number="1",
                        marginal_note_en="Short title",
                        text_en="This Act may be cited as the Test Act.",
                    ),
                ],
            ),
            BillPart(
                id="test:part2",
                anchor_id="test:part2",
                sequence=2,
                number=2,
                title_en="Enforcement",
                title_fr="Exécution",
                sections=[
                    BillSection(
                        id="test:s2",
                        anchor_id="test:s2",
                        sequence=2,
                        number="2",
                        marginal_note_en="Regulations",
                        text_en="The Governor in Council may make regulations.",
                    ),
                ],
            ),
        ],
        sections=[],
        definitions=[],
    )

    # English
    text_en = extract_continuous_text(bill, 'en')
    assert "PART I — General Provisions" in text_en
    assert "1. Short title" in text_en
    assert "PART II — Enforcement" in text_en
    assert "2. Regulations" in text_en

    # French (Part headings should use French titles)
    text_fr = extract_continuous_text(bill, 'fr')
    assert "PART I — Dispositions générales" in text_fr
    assert "PART II — Exécution" in text_fr


def test_validate_extracted_text():
    """Test validation of extracted text."""
    # Create a bill with 5 sections
    bill = ParsedBill(
        bill_number="C-1",
        parliament=45,
        session=1,
        session_str="45-1",
        stage=BillStage.FIRST_READING,
        version_number=1,
        title_en="Test",
        title_fr=None,
        short_title_en=None,
        short_title_fr=None,
        sponsor_name=None,
        sponsor_riding=None,
        summary_en=None,
        summary_fr=None,
        preamble_en=None,
        preamble_fr=None,
        enacting_clause_en=None,
        enacting_clause_fr=None,
        parts=[],
        sections=[
            BillSection(
                id=f"test:s{i}",
                anchor_id=f"test:s{i}",
                sequence=i,
                number=str(i),
                marginal_note_en=f"Section {i}",
                text_en=f"This is section {i}.",
            )
            for i in range(1, 6)
        ],
        definitions=[],
    )

    # Valid text (5 sections found)
    valid_text = """1. Section 1

This is section 1.

2. Section 2

This is section 2.

3. Section 3

This is section 3.

4. Section 4

This is section 4.

5. Section 5

This is section 5."""

    assert validate_extracted_text(valid_text, bill) == True

    # Too short
    assert validate_extracted_text("Short", bill) == False

    # No section numbers
    assert validate_extracted_text("This is just text without section numbers.", bill) == False

    # Too few sections (only 2 found, expected 5, below 80% threshold)
    few_sections = """1. Section 1

This is section 1.

2. Section 2

This is section 2."""

    assert validate_extracted_text(few_sections, bill) == False


if __name__ == "__main__":
    # Run tests
    test_int_to_roman()
    print("✅ test_int_to_roman passed")

    test_format_subparagraph()
    print("✅ test_format_subparagraph passed")

    test_format_paragraph()
    print("✅ test_format_paragraph passed")

    test_format_subsection()
    print("✅ test_format_subsection passed")

    test_format_section_simple()
    print("✅ test_format_section_simple passed")

    test_format_section_with_subsections()
    print("✅ test_format_section_with_subsections passed")

    test_extract_simple_bill()
    print("✅ test_extract_simple_bill passed")

    test_extract_bill_with_preamble()
    print("✅ test_extract_bill_with_preamble passed")

    test_extract_bill_with_parts()
    print("✅ test_extract_bill_with_parts passed")

    test_validate_extracted_text()
    print("✅ test_validate_extracted_text passed")

    print("\n🎉 All tests passed!")
