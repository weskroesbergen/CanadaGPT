# Recent Data Import (2022-Present)

Quick, lightweight import for current/recent parliamentary data without bulk downloads.

---

## 🎯 Overview

Instead of importing 30+ years of historical data, this imports only recent data (2022-present) using the API directly.

### Advantages

✅ **No PostgreSQL needed** - Direct API to Neo4j
✅ **Fast** - Completes in 15-20 minutes
✅ **Small** - Only ~3 GB disk space
✅ **Current** - All MPs, bills, committees
✅ **Recent** - 3 years of debates/votes

### What You Get

- **All current MPs** (343)
- **All current bills** (111 from LEGISinfo)
- **Debates since 2022** (~300-500 sittings)
- **Statements since 2022** (~50,000 speeches)
- **Votes since 2022** (~500 votes)
- **All committees** (~25 active)
- **Recent expenses** (2023-present)

---

## 🚀 Quick Start

### Prerequisites

- ✅ Neo4j running (you already have this)
- ✅ Python environment (you already have this)
- ✅ No PostgreSQL needed!

### Run Import

```bash
python test_recent_import.py
```

**That's it!** No setup, no downloads, no PostgreSQL.

---

## 📊 Size Comparison

| Approach | Disk Space | Time | Data Range |
|----------|-----------|------|------------|
| **Recent Import** | 3 GB | 20 min | 2022-present |
| **Modern Bulk** | 40 GB | 60 min | 1994-present |
| **Complete History** | 100 GB | 2-3 hours | 1901-present |

---

## ⚙️ Customization

### Change Date Range

Edit `test_recent_import.py`:

```python
importer = RecentDataImporter(
    neo4j,
    start_date="2020-01-01"  # Change this!
)
```

**Options**:
- `"2024-01-01"` - Only this year (~5 min)
- `"2022-01-01"` - Last 3 years (~20 min, recommended)
- `"2020-01-01"` - Last 5 years (~40 min)
- `"2015-01-01"` - Last 10 years (~80 min)

**Rule of thumb**: Each year ≈ 100-150 debates, 15,000 statements, 6-7 minutes

### Skip Components

Edit `recent_import.py` to comment out what you don't need:

```python
# stats["debates"] = self.import_recent_debates(batch_size)  # Skip debates
# stats["votes"] = self.import_recent_votes(batch_size)  # Skip votes
```

---

## 📈 Data Volume by Year

| Year | Debates | Statements | Votes | Size |
|------|---------|------------|-------|------|
| 2024 | ~100 | ~12,000 | ~150 | ~500 MB |
| 2023 | ~150 | ~18,000 | ~200 | ~750 MB |
| 2022 | ~120 | ~14,000 | ~180 | ~600 MB |
| **Total 2022-present** | **~370** | **~44,000** | **~530** | **~2 GB** |

Add MPs, bills, committees: **+500 MB**
Add expenses: **+200 MB**
Add indexes: **+300 MB**

**Total: ~3 GB**

---

## 🔍 What's Missing vs Bulk Import

### You Get
- ✅ All current MPs
- ✅ All current bills
- ✅ All committees
- ✅ Recent debates (2022+)
- ✅ Recent votes (2022+)
- ✅ Current expenses

### You Don't Get
- ❌ Historical MPs (pre-2022)
- ❌ Historical debates (pre-2022)
- ❌ Historical bills (pre-2022)
- ❌ Historical votes (pre-2022)

**But**: For most use cases (current affairs, MP tracking, recent legislation), 2022-present is sufficient!

---

## 💡 When to Use Each Approach

### Use Recent Import If:
- Building a current affairs app
- Tracking current MPs/bills
- Prototyping/testing
- Limited disk space
- Need it working quickly

### Use Bulk Import If:
- Need historical analysis
- Academic research
- Long-term trends
- "What did MPs say in 2005?"
- Complete legislative history

### Use Both If:
- Start with recent (quick setup)
- Add bulk later (when needed)
- They work together seamlessly!

---

## 🎮 Example Usage

### After Import

```cypher
// Check what you have
MATCH (d:Debate)
WHERE d.date >= '2022-01-01'
RETURN count(d) AS recent_debates

// Find MP speeches in 2024
MATCH (m:MP)-[:SPOKE]->(s:Statement)-[:IN_DEBATE]->(d:Debate)
WHERE d.date >= '2024-01-01'
RETURN m.name, count(s) AS speeches_2024
ORDER BY speeches_2024 DESC
LIMIT 10

// Committee activity
MATCH (c:Committee)<-[:MEMBER_OF]-(m:MP)
RETURN c.name, count(m) AS members
ORDER BY members DESC

// Recent bills
MATCH (b:Bill)
WHERE b.session = '45-1'
RETURN b.number, b.title, b.status
ORDER BY b.number
```

---

## 🔄 Incremental Updates

After initial import, run weekly/monthly to stay current:

```bash
# Update script
python test_recent_import.py
```

**What it does**:
- Fetches new debates since last run
- Adds new bills
- Updates MP info
- Merges (no duplicates)

**Time**: 2-5 minutes for weekly update

---

## 🧹 Cleanup

If you want to reset and re-import:

```cypher
// Delete recent data only
MATCH (d:Debate)
WHERE d.date >= '2022-01-01'
DETACH DELETE d

// Or delete everything
MATCH (n)
DETACH DELETE n
```

Then re-run import.

---

## ⚡ Performance

### Import Speed
- MPs: ~30 seconds (343 records)
- Bills: ~2 seconds (111 records)
- Debates: ~10-12 minutes (300-500 debates)
- Votes: ~3-4 minutes (500 votes)
- Committees: ~10 seconds (25 records)

**Total: 15-20 minutes**

### Query Performance
Same as bulk import - fully indexed and optimized.

---

## 🎯 Bottom Line

**Recent import is the recommended starting point** for most users:

- ✅ Fast setup (20 min vs 2-3 hours)
- ✅ Small footprint (3 GB vs 100 GB)
- ✅ No PostgreSQL needed
- ✅ Covers all current/recent data
- ✅ Can add historical later if needed

**Run it now**:
```bash
python test_recent_import.py
```

You'll have a working system in 20 minutes! 🎉
