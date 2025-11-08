# Historical MP Expense Data Sources (Pre-2020)

## Executive Summary

**YES, historical MP expense data before 2020 EXISTS**, but it's in different formats requiring manual access. Here's where to find Pierre Poilievre's complete 21-year expense history (2004-2025).

---

## Data Availability Timeline

| Period | Format | Source | FedMCP Support | Notes |
|--------|--------|--------|----------------|-------|
| 2001-2009 | PDF | House of Commons / CBC | ❌ No | Annual reports only |
| 2009-2020 | Various | Parliament site | ❌ No | Different system |
| Jul 2020+ | CSV | Proactive Disclosure | ✅ **YES** | Current system |

---

## 1. FedMCP (Automated) - 2020 to Present

**Period Covered:** July 2020 (FY 2020-2021 Q2) to present  
**Format:** Machine-readable CSV via web scraping  
**Update Frequency:** Quarterly (within 30 days of quarter end)

**Access:**
```python
from fedmcp import MPExpenditureClient

client = MPExpenditureClient()
expenses = client.get_quarterly_summary(fiscal_year=2024, quarter=1)
```

**Pros:**
- ✅ Fully automated via FedMCP
- ✅ Machine-readable format
- ✅ Quarterly granularity
- ✅ Detailed breakdown by category

**Cons:**
- ❌ Only covers last 4.5 years (since July 2020)
- ❌ Missing April-June 2020 (transition period)

---

## 2. CBC News Database - 2001 to 2010

**URL:** https://www.cbc.ca/news2/interactives/database-mp-expenses/  
**Period Covered:** Fiscal years 2001-2002 through 2009-2010  
**Format:** Online database (Caspio application)

**What's Available:**
- Annual expense summaries dating back to 2001-2002
- 2008-2009 data converted to spreadsheet format by CBC
- Searchable by MP name (includes Pierre Poilievre from 2004)

**Access Method:**
1. Visit CBC database
2. Use dropdown menu to select "Pierre Poilievre"
3. View/export data for available fiscal years

**Pros:**
- ✅ Covers Poilievre's first 6 years as MP (2004-2010)
- ✅ Free public access
- ✅ Some data in spreadsheet format (2008-2009)

**Cons:**
- ❌ Manual access only (no API)
- ❌ Most data still in PDF format
- ❌ Annual summaries only (not quarterly)
- ❌ Limited to 2001-2010 range

**Historical Value:**
- Covers 6 of Poilievre's 21 years as MP
- Period includes his rise from backbencher to parliamentary roles
- Pre-financial crisis through to majority government era

---

## 3. House of Commons Board of Internal Economy - 2000 to ~2019

**Base URL:** https://www.ourcommons.ca/content/boie/pdf/  
**Period Covered:** Fiscal years 2000-2001 to approximately 2018-2019  
**Format:** Annual PDF reports

**File Naming Pattern:**
```
MembersExpenses-{YEAR}-{YEAR+1}-e.pdf

Examples:
- MembersExpenses-2004-2005-e.pdf (Poilievre's first year)
- MembersExpenses-2010-2011-e.pdf
- MembersExpenses-2015-2016-e.pdf
```

**Known Available Reports:**
- 2000-2001 ✅
- 2003-2004 ✅
- 2004-2005 ✅ (Poilievre's first full year)
- 2008-2009 ✅
- ... (likely many others)

**Access Method:**
1. Construct PDF URL using pattern above
2. Download PDF
3. Extract data manually or via PDF parsing tools

**Pros:**
- ✅ Official government source
- ✅ Comprehensive annual reports
- ✅ Available for 18+ years of history

**Cons:**
- ❌ PDF format (not machine-readable)
- ❌ Annual summaries only
- ❌ Requires manual download per year
- ❌ Some URLs may be broken (404 errors)

**Historical Value:**
- Covers 16 of Poilievre's 21 years as MP (2004-2020)
- Includes key career milestones:
  - Backbencher (2004-2006)
  - Harper government minister (2013-2015)
  - Opposition critic roles (2015-2022)
  - Conservative leadership race (2022)

---

## 4. ParlInfo Library System

**URL:** https://lop.parl.ca/sites/ParlInfo/default/en_CA/SiteInformation/atoz  
**Period Covered:** Historical records dating back decades  
**Format:** Reference links to reports

**What's Available:**
- Lists of Individual Members' Expenditures reports under "Annual Reports - House of Commons"
- Index of archived expense reports
- May include links to PDF reports from #3 above

**Access Method:**
1. Visit ParlInfo A-Z index
2. Navigate to "Annual Reports - House of Commons"
3. Look for "Individual Members' Expenditures"
4. Follow links to archived reports

**Pros:**
- ✅ Centralized index of all reports
- ✅ Official parliamentary library resource
- ✅ Comprehensive historical coverage

**Cons:**
- ❌ Index only (not direct data access)
- ❌ Still links to PDFs
- ❌ Navigation can be complex

---

## 5. Open Government Portal - Federal Institutions

**URL:** https://open.canada.ca/data/en/dataset/009f9a49-c2d9-4d29-a6d4-1a228da335ce  
**Period Covered:** Varies by department  
**Format:** CSV datasets

**What's Available:**
- Proactive disclosure of travel expenses from federal institutions
- May include Parliamentary travel but focus is on public service
- Machine-readable datasets

**Access Method:**
1. Visit Open Government Portal
2. Search for travel expense datasets
3. Download CSV files

**Pros:**
- ✅ Machine-readable format
- ✅ Structured data
- ✅ Downloadable bulk datasets

**Cons:**
- ❌ Primarily covers public service, not MPs
- ❌ Different reporting structure than MP expenses
- ❌ May not include individual MP office budgets

**Note:** This source is likely NOT useful for Poilievre MP expenses specifically, but included for completeness.

---

## Complete Data Access Strategy for Pierre Poilievre (2004-2025)

### To Get Full 21-Year History:

**2004-2010 (6 years):**
- Use **CBC Database** (#2) for searchable access
- Download annual summaries manually

**2010-2020 (10 years):**
- Use **Board of Internal Economy PDFs** (#3)
- Download files: `MembersExpenses-2010-2011-e.pdf` through `MembersExpenses-2019-2020-e.pdf`
- Consider PDF parsing tools to extract data programmatically

**July 2020-2025 (4.5 years):**
- Use **FedMCP** (#1) - fully automated!
```python
from fedmcp import MPExpenditureClient

client = MPExpenditureClient()

# Get all available quarters
for fy in range(2021, 2027):  # FY 2020-2021 through 2026-2027
    for q in range(1, 5):
        try:
            expenses = client.search_by_name("Poilievre", fiscal_year=fy, quarter=q)
            if expenses:
                exp = expenses[0]
                print(f"FY {fy} Q{q}: Total ${exp.total:,.2f} (Travel: ${exp.travel:,.2f})")
        except:
            continue
```

---

## Future FedMCP Enhancement Possibilities

### Potential Phase 9: Historical Data Integration

**Option A: PDF Parsing**
- Create client to download Board of Internal Economy PDFs
- Parse annual reports using PDF extraction tools (e.g., pdfplumber, tabula-py)
- Convert to structured data format
- Extend expense data back to 2000

**Option B: CBC Database Integration**
- Reverse-engineer CBC Caspio database API
- Scrape or download historical summaries
- Integrate 2001-2010 data into FedMCP

**Option C: Hybrid Approach**
- Use CBC for 2001-2010
- Parse PDFs for 2010-2020
- Current system for 2020+
- Present unified 25-year expense history

**Challenges:**
- PDF parsing reliability varies by report format
- Annual vs. quarterly data reconciliation
- Category definitions may have changed over time
- Significant development effort required

**Value:**
- Complete 25-year expense history for all MPs
- Historical trend analysis
- Long-term accountability tracking
- Comparative analysis across parliamentary sessions

---

## Summary Table: Coverage by Source

| Fiscal Year | Pierre Poilievre Status | Available Sources | Format |
|-------------|------------------------|-------------------|--------|
| 2004-2005 | First year as MP | CBC + Board PDF | PDF |
| 2005-2010 | Backbencher | CBC + Board PDF | PDF/Database |
| 2010-2013 | Opposition | Board PDF | PDF |
| 2013-2015 | Minister (Harper govt) | Board PDF | PDF |
| 2015-2020 | Opposition critic | Board PDF | PDF |
| 2020 Q2-Q4 | COVID Parliament | **FedMCP** | CSV (automated) |
| 2021-2022 | Conservative leadership | **FedMCP** | CSV (automated) |
| 2022-2025 | Leader of Opposition | **FedMCP** | CSV (automated) |
| 2025 Aug+ | Battle River–Crowfoot | **FedMCP** | CSV (automated) |

**Total Coverage:**
- **Manual access required:** 16 years (2004-2020) - 76% of career
- **FedMCP automated:** 4.5 years (July 2020-2025) - 21% of career
- **Missing:** ~3% (April-June 2020 transition quarter)

---

**Document Created:** November 2, 2025  
**FedMCP Version:** 0.1.0  
**Research Status:** Complete - All known sources documented
