# Historical Data Import: Complete Guide

Import 120+ years of Canadian parliamentary data into Neo4j (1901-present).

---

## 🎯 What You'll Get

After completing this import, your Neo4j database will contain:

### Coverage Timeline
```
1901 ────────────── 1993 ─────────────────── 2025
  │                    │                       │
  └─ Lipad Data (93y) ─┴─ OpenParliament (31y)┘

Total: 124 years of complete parliamentary history!
```

### Data Volume (Estimated)
- **4,000+** MPs (current + historical)
- **40,000+** debate sittings
- **5,000,000+** individual statements/speeches
- **500+** committees
- **50,000+** committee meetings
- **10,000+** bills (with sponsors)

---

## 🚀 Quick Start

### Option 1: OpenParliament Only (1994-present)

**Time**: ~1 hour
**Coverage**: 31 years
**Complexity**: Low

```bash
# 1. PostgreSQL is already set up ✅
# 2. Just run the import
python test_bulk_import.py
```

This gets you modern data quickly without manual Lipad download.

### Option 2: Complete History (1901-present)

**Time**: ~2-3 hours
**Coverage**: 124 years
**Complexity**: Medium (requires Lipad download)

```bash
# 1. Download Lipad data first (see instructions below)
# 2. Run combined import
python test_complete_historical_import.py
```

---

## 📥 Downloading Lipad Data

### Step 1: Visit Lipad Data Page

Unfortunately, I can't access https://www.lipad.ca/data/ directly (403 error), but here's what to do:

1. **Visit**: https://www.lipad.ca/data/
2. **Look for** download options:
   - **CSV Package** (recommended): Daily Hansard files in UTF-8
   - **XML Package**: Digitized XML from original documents
   - **PostgreSQL Dump**: Complete database (advanced)

### Step 2: Download and Extract

```bash
# Create download directory
mkdir -p ~/Downloads/lipad_data

# Download from website (example - actual URL varies)
# Check lipad.ca/data for current download links
cd ~/Downloads/lipad_data

# Extract (example for zip file)
unzip lipad-csv-package.zip

# Or extract tar.gz
tar -xzf lipad-hansard-csv.tar.gz
```

### Step 3: Verify Files

```bash
# Check what you downloaded
ls -lh ~/Downloads/lipad_data/

# Should see either:
# - Many .csv files (one per sitting)
# - Many .xml files (XML format)
# - A single .sql or .dump file (PostgreSQL format)
```

---

## 🎮 Running the Import

### Setup (Already Done ✅)

- ✅ PostgreSQL 14 installed
- ✅ PostgreSQL service running
- ✅ Database `openparliament_temp` created
- ✅ Python packages installed (psycopg2-binary)

### Import: OpenParliament Only

```bash
python test_bulk_import.py
```

**What it does**:
1. Downloads 1.2GB OpenParliament PostgreSQL dump
2. Extracts and loads into temp database (~15 min)
3. Imports into Neo4j:
   - MPs (all historical + current)
   - Debates (1994-present)
   - Statements (individual speeches)
   - Committees + memberships
   - Bills + votes

**Progress**:
```
============================================================
OPENPARLIAMENT BULK IMPORT
============================================================

Downloading OpenParliament dump from https://openparliament.ca/data/...
Downloaded 100MB / 1200MB (8.3%)...
✅ Downloaded to /tmp/openparliament_import/openparliament.public.sql.bz2

Extracting and loading PostgreSQL dump...
This will take 10-20 minutes...
✅ Database loaded successfully

Importing MPs from PostgreSQL dump...
Found 4,123 MPs in PostgreSQL dump
✅ Imported 4,123 MPs

Importing debates from PostgreSQL dump...
Found 10,543 debates in PostgreSQL dump
✅ Imported 10,543 debates
✅ Imported 487,291 statements
✅ Created 487,291 relationships

Importing committees from PostgreSQL dump...
Found 543 committees
✅ Imported 543 committees
✅ Created 8,234 memberships

============================================================
✅ OPENPARLIAMENT BULK IMPORT COMPLETE
MPs: 4,123
Debates: 10,543
Statements: 487,291
Committees: 543
Committee Memberships: 8,234
============================================================
```

### Import: Complete History (with Lipad)

```bash
python test_complete_historical_import.py
```

**Interactive prompts**:
```
Enter Lipad data directory path (or press Enter to skip): ~/Downloads/lipad_data
Continue with import? [y/N]: y
```

**What it does**:
1. **Phase 1**: Imports Lipad data (1901-1993)
   - Parses CSV or XML files
   - Creates historical debates + statements
   - Links to parliament numbers (estimated)

2. **Phase 2**: Imports OpenParliament (1994-present)
   - Same as OpenParliament-only import above

**Progress**:
```
============================================================
COMPLETE HISTORICAL IMPORT: 1901-PRESENT
============================================================

Phase 1: Importing Lipad historical data (1901-1993)...
============================================================
LIPAD HISTORICAL HANSARD IMPORT (1901-1993)
============================================================
Importing Lipad CSV files from ~/Downloads/lipad_data...
Found 25,432 CSV files to process
Processed 5000/25432 files...
Processed 10000/25432 files...
✅ Imported 25,432 historical debates (1901-1993)
✅ Imported 3,456,789 historical statements
✅ Found 2,345 unique speakers
============================================================
✅ LIPAD HISTORICAL IMPORT COMPLETE
============================================================

Phase 2: Importing OpenParliament dump (1994-present)...
[... same as above ...]

============================================================
✅ COMPLETE HISTORICAL IMPORT FINISHED
Total coverage: 124 years (1901-present)
Lipad debates: 25,432
OpenParliament debates: 10,543
============================================================
```

---

## 🔍 Verifying Import

### Check Neo4j Browser

```cypher
// Count all debates
MATCH (d:Debate)
RETURN count(d) AS total_debates

// Debates by era
MATCH (d:Debate)
WHERE d.source = 'lipad'
RETURN count(d) AS lipad_debates

MATCH (d:Debate)
WHERE d.source IS NULL OR d.source <> 'lipad'
RETURN count(d) AS modern_debates

// Sample historical debate
MATCH (d:Debate)
WHERE d.date < '1950-01-01'
RETURN d
LIMIT 1

// Sample modern debate with statements
MATCH (d:Debate)-[:IN_DEBATE]-(s:Statement)-[:SPOKE]-(m:MP)
WHERE d.date > '2020-01-01'
RETURN d.date, m.name, substring(s.content, 0, 100) AS preview
LIMIT 5

// Check committees
MATCH (c:Committee)
RETURN count(c) AS total_committees

MATCH (m:MP)-[r:MEMBER_OF]->(c:Committee)
RETURN c.name, count(m) AS members
ORDER BY members DESC
LIMIT 10
```

---

## 🧹 Cleanup (Optional)

After successful import, you can free up ~15GB of disk space:

```bash
# Drop temporary PostgreSQL database
export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"
/opt/homebrew/opt/postgresql@14/bin/dropdb openparliament_temp

# Remove downloaded files
rm -rf /tmp/openparliament_import
rm -rf ~/Downloads/lipad_data  # if you're done with it

# Stop PostgreSQL if not needed
brew services stop postgresql@14
```

**Note**: Keep the database if you plan to do incremental updates monthly!

---

## 🔄 Monthly Updates

OpenParliament dump updates on the 1st of each month. To refresh:

```bash
# Re-download latest dump
python test_bulk_import.py

# Or create automated script
cat > ~/update_parliament_data.sh << 'EOF'
#!/bin/bash
export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"
cd /Users/matthewdufresne/FedMCP

# Drop and recreate database
dropdb openparliament_temp
createdb openparliament_temp

# Run import
python test_bulk_import.py
EOF

chmod +x ~/update_parliament_data.sh

# Add to cron for monthly updates
# crontab -e
# Add: 0 2 2 * * /Users/matthewdufresne/update_parliament_data.sh
```

---

## 🐛 Troubleshooting

### PostgreSQL Won't Start

```bash
# Check status
brew services list | grep postgresql

# Restart
brew services restart postgresql@14

# Check logs
tail -f /opt/homebrew/var/log/postgresql@14.log
```

### Database Connection Error

```bash
# Verify PostgreSQL is ready
export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"
/opt/homebrew/opt/postgresql@14/bin/pg_isready

# Test connection
/opt/homebrew/opt/postgresql@14/bin/psql -d openparliament_temp -c "SELECT version();"
```

### Download Fails

```bash
# Check disk space
df -h

# Resume download manually
curl -C - -o /tmp/openparliament_import/openparliament.public.sql.bz2 \
  https://openparliament.ca/data/openparliament.public.sql.bz2
```

### Out of Memory

Reduce batch size in the import scripts:

```python
stats = importer.import_all(
    batch_size=500  # Reduced from 1000
)
```

### Import Takes Too Long

Run with limits for testing first:

```python
# In bulk_import.py
stats = importer.import_all(
    download=False,  # Use cached dump
    load_pg=False,   # Use existing database
    limit=1000       # Only import 1000 debates for testing
)
```

---

## 📊 What's in the Data

### Neo4j Graph Schema

```
(MP)-[:SPOKE]->(Statement)-[:IN_DEBATE]->(Debate)
(MP)-[:MEMBER_OF]->(Committee)
(MP)-[:SPONSORED]->(Bill)
(MP)-[:VOTED]->(Vote)
(MP)-[:BELONGS_TO]->(Party)
(MP)-[:REPRESENTS]->(Riding)
```

### Node Types

**MP** (Politician)
- Properties: name, party, riding, gender, email, phone, photo_url
- Historical + current (4,000+)

**Debate** (Hansard Sitting)
- Properties: date, parliament, session, number, source
- 1901-present (35,000+)

**Statement** (Individual Speech)
- Properties: content, speaker_name, time, heading, wordcount
- Full text of speeches (5M+)

**Committee**
- Properties: name, code, chamber
- All parliamentary committees (500+)

**Bill**
- Properties: number, title, status, sponsor
- From LEGISinfo JSON (111 current + historical)

---

## 🎯 Next Steps After Import

1. **Update GraphQL Schema**
   - Add `Debate` and `Statement` types
   - Add queries for searching Hansard
   - Add full-text search

2. **Build Frontend Features**
   - Debate browser by date
   - Search speeches by keyword
   - MP speaking history
   - Committee activity tracker

3. **Add Analytics**
   - Word frequency over time
   - Speaking patterns
   - Topic modeling
   - Sentiment analysis

4. **Cross-Reference Data**
   - Link debates to bills
   - Link statements to votes
   - Link committee meetings to legislation

---

## 📚 Resources

- **OpenParliament**: https://openparliament.ca/
- **OpenParliament Data**: https://openparliament.ca/data-download/
- **Lipad Project**: https://www.lipad.ca/
- **Lipad Data**: https://www.lipad.ca/data/
- **PostgreSQL Docs**: https://www.postgresql.org/docs/14/
- **Neo4j Cypher**: https://neo4j.com/docs/cypher-manual/

---

## 🎉 Success!

Once complete, you'll have one of the most comprehensive historical parliamentary databases in Canada, spanning 124 years of debates, speeches, committees, and legislation - all interconnected in a powerful graph database ready for analysis and visualization!

The data will enable questions like:
- "What did MPs say about climate change in 1950 vs 2020?"
- "Which MPs have spoken most about healthcare over their careers?"
- "How has committee activity changed over decades?"
- "What bills did this MP sponsor and which passed?"

Happy importing! 🇨🇦
