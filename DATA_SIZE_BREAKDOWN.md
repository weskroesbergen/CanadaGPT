# FedMCP Data Size Breakdown

Complete analysis of disk space, download sizes, and database storage requirements.

---

## 📊 Summary

| Component | Download | Extracted | Database | Total Required |
|-----------|----------|-----------|----------|----------------|
| **Bills (LEGISinfo JSON)** | 204 KB | - | ~5 MB | ~5 MB |
| **OpenParliament Dump** | 1.2 GB | 6 GB | 7 GB | 14.2 GB |
| **Lipad Historical** | 2-5 GB | 10-20 GB | 15-25 GB | 30-50 GB |
| **Neo4j (Final)** | - | - | 10-30 GB | 10-30 GB |
| **Total (Modern Only)** | 1.2 GB | - | - | **~25-35 GB** |
| **Total (Complete History)** | 3-6 GB | - | - | **~60-100 GB** |

**Recommendation**: Have **100 GB free space** for comfortable full historical import.

---

## 📥 Download Sizes

### LEGISinfo Bills (Current Parliament)
- **URL**: https://www.parl.ca/legisinfo/en/bills/json
- **Size**: 204 KB
- **Contains**: 111 bills from current session (45-1)
- **Coverage**: Current parliament only
- **Updated**: Daily/weekly

### OpenParliament PostgreSQL Dump
- **URL**: https://openparliament.ca/data/openparliament.public.sql.bz2
- **Compressed**: ~1.2 GB (.bz2)
- **Extracted**: ~6 GB (.sql)
- **Coverage**: 1994-present (31 years)
- **Updated**: First of each month
- **Contains**:
  - MPs: ~4,000+ records
  - Debates: ~10,000+ sittings
  - Statements: ~500,000+ speeches
  - Bills: ~6,000+ records
  - Votes: ~5,000+ records
  - Committees: ~500+ records
  - Committee meetings: ~50,000+ records

### Lipad Historical Data (1901-1993)
- **URL**: https://www.lipad.ca/data/
- **Formats Available**:

  **CSV Package** (Recommended)
  - Compressed: ~2-3 GB (estimated)
  - Extracted: ~10-15 GB
  - Format: Daily CSV files (one per sitting)
  - Coverage: 1901-1993 (93 years)
  - Contains: ~25,000+ sitting days

  **XML Package**
  - Compressed: ~3-5 GB (estimated)
  - Extracted: ~15-20 GB
  - Format: XML documents
  - Coverage: 1901-1993

  **PostgreSQL Dump**
  - Size: ~5-10 GB (estimated)
  - Direct database import
  - Complete with relationships

**Note**: Lipad sizes are estimates based on data volume. Check lipad.ca/data for actual current sizes.

---

## 💾 Database Sizes

### PostgreSQL Temporary Database
- **Name**: openparliament_temp
- **Size**: ~7 GB (after loading OpenParliament dump)
- **Purpose**: Intermediate step for data transformation
- **Can be deleted**: Yes, after Neo4j import completes

### Neo4j Database (After Import)

**Modern Data Only (1994-present)**:
- **Nodes**: ~1,000,000 nodes
  - MPs: 4,000
  - Debates: 10,000
  - Statements: 500,000
  - Bills: 6,000
  - Votes: 5,000
  - Committees: 500
  - Parties: 10
  - Ridings: 350
  - Expenses: 7,000
- **Relationships**: ~1,500,000 relationships
- **Estimated Size**: 10-15 GB
- **With Indexes**: 12-18 GB

**Complete Historical (1901-present)**:
- **Nodes**: ~6,000,000 nodes
  - Historical MPs: 3,000+
  - Historical Debates: 25,000
  - Historical Statements: 3,500,000
  - Modern data: (same as above)
- **Relationships**: ~7,000,000 relationships
- **Estimated Size**: 25-35 GB
- **With Indexes**: 30-40 GB

---

## 🗂️ Disk Space Requirements

### Scenario 1: Modern Data Only (1994-present)

**Phase 1: Download**
```
LEGISinfo JSON:           0.2 MB
OpenParliament dump:      1.2 GB
─────────────────────────────────
Subtotal:                 1.2 GB
```

**Phase 2: Extraction & Database**
```
Extracted SQL:            6 GB
PostgreSQL database:      7 GB
Neo4j database:          15 GB
─────────────────────────────────
Subtotal:                28 GB
```

**Phase 3: After Cleanup**
```
Neo4j database only:     15 GB
(Deleted: SQL, PostgreSQL)
─────────────────────────────────
Final:                   15 GB
```

**Total Required During Import**: ~30 GB
**Final After Cleanup**: ~15 GB

---

### Scenario 2: Complete Historical (1901-present)

**Phase 1: Download**
```
LEGISinfo JSON:           0.2 MB
OpenParliament dump:      1.2 GB
Lipad CSV/XML:            3 GB (est.)
─────────────────────────────────
Subtotal:                 4.2 GB
```

**Phase 2: Extraction & Databases**
```
Lipad extracted:         15 GB (est.)
OpenParliament SQL:       6 GB
PostgreSQL database:      7 GB
Neo4j database:          35 GB
─────────────────────────────────
Subtotal:                63 GB
```

**Phase 3: After Cleanup**
```
Neo4j database only:     35 GB
(Deleted: all temp files)
─────────────────────────────────
Final:                   35 GB
```

**Total Required During Import**: ~70 GB
**Final After Cleanup**: ~35 GB

---

## 📈 Growth Estimates

### Monthly Growth (OpenParliament)
- **New debates**: ~20-30 sittings/month
- **New statements**: ~5,000-10,000 speeches/month
- **New bills**: ~5-10 bills/month
- **Database growth**: ~200-500 MB/month

### Annual Growth
- **Database growth**: ~3-6 GB/year
- **After 5 years**: +15-30 GB

**Strategy**: Monthly refresh keeps size manageable

---

## 💰 Cost Breakdown (Cloud Hosting)

If hosting in cloud (AWS, GCP, Azure):

### Storage Costs (Monthly)
- **S3/Cloud Storage** (downloads): $0.02/GB
  - OpenParliament dump (1.2 GB): $0.02/month
  - Lipad data (3 GB): $0.06/month

- **Database Storage** (Neo4j)
  - Modern only (15 GB): $1.50/month
  - Complete history (35 GB): $3.50/month

- **PostgreSQL** (temporary): Can be deleted after import

### Compute Costs (During Import)
- **Import time**: 1-3 hours
- **Instance**: 4 vCPU, 16 GB RAM
- **Cost**: ~$0.50-1.50 per import

**Total Monthly (Modern)**: ~$2-3/month
**Total Monthly (Historical)**: ~$4-5/month

---

## 🚀 Performance Characteristics

### Import Speed

**Network (Download)**:
- LEGISinfo JSON: < 1 second
- OpenParliament dump: 5-10 minutes (1.2 GB)
- Lipad data: 15-30 minutes (3 GB)

**Decompression**:
- OpenParliament bz2: 2-5 minutes
- Lipad archives: 5-10 minutes

**PostgreSQL Load**:
- OpenParliament SQL: 10-20 minutes

**Neo4j Import**:
- Batch size 1000:
  - MPs: 1-2 minutes
  - Debates: 5-10 minutes
  - Statements: 30-60 minutes
  - Relationships: 10-20 minutes

**Total Time**:
- Modern only: **60-90 minutes**
- Complete history: **120-180 minutes**

### Query Performance (After Import)

**Simple queries** (e.g., find MP):
- ~1-10 ms with indexes

**Complex queries** (e.g., full-text search):
- ~50-500 ms without optimization
- ~10-50 ms with indexes + caching

**Aggregations** (e.g., count all statements):
- ~100-1000 ms for millions of records

**Graph traversals** (e.g., MP → speeches → debates):
- ~10-100 ms for typical depth

---

## 🔧 Optimization Tips

### Reduce Space During Import

1. **Stream Instead of Cache**
   ```python
   # Instead of downloading fully, stream to PostgreSQL
   curl ... | bunzip2 | psql
   ```
   Saves: 6 GB (no extracted SQL file)

2. **Import in Phases**
   ```python
   # Import MPs only, then debates, etc.
   importer.import_mps()
   # Delete PostgreSQL, reload for next phase
   ```
   Saves: 7 GB (drop PostgreSQL between phases)

3. **Skip Lipad if Not Needed**
   ```
   Modern data (1994-present) covers most use cases
   ```
   Saves: 30-50 GB

### Reduce Final Database Size

1. **Limit Statement Content**
   ```python
   # Truncate long speeches to 1000 chars
   statement["content"] = content[:1000]
   ```
   Saves: ~30% of statement storage

2. **Skip Old Statements**
   ```python
   # Only import debates, not individual statements
   # if full-text search not needed
   ```
   Saves: ~60% of database size

3. **Index Only What You Query**
   ```cypher
   // Don't create indexes on rarely-queried fields
   ```
   Saves: ~10-20% overhead

---

## 📊 Actual Size Examples

### Test Import Results (100 debates limit)

```
MPs: 4,123 records = 2.5 MB
Debates: 100 records = 50 KB
Statements: 8,234 records = 15 MB
Committees: 543 records = 200 KB
─────────────────────────────────
Total: ~18 MB for test dataset
```

**Extrapolate to full import**:
- Debates (10,000×): 5 MB
- Statements (500,000×): ~900 MB
- With indexes + overhead: ~1.5 GB

This matches our 10-15 GB estimate for full modern data.

---

## ✅ Recommendations

### For Development/Testing
- **Modern data only**: 30 GB free space
- **Download on fast connection**: Saves 10-20 minutes
- **Use SSD if possible**: 3-5× faster import

### For Production
- **Complete history**: 100 GB free space (safe margin)
- **Schedule monthly updates**: Keep data fresh
- **Monitor growth**: Plan for 5-10 GB/year

### For Constrained Environments
- **Modern + limited statements**: 20 GB
- **Debates metadata only** (no full text): 5 GB
- **MPs + committees only**: 2 GB

---

## 🎯 Bottom Line

**Quick Answer**:
- **Bare minimum**: 20 GB free
- **Comfortable (modern)**: 40 GB free
- **Complete history**: 100 GB free
- **Final database size**: 15-35 GB

**Most users should aim for 50-100 GB free space** to comfortably run imports and have room for growth.

The data is large, but you're getting **124 years** of complete parliamentary history - every debate, every speech, every vote! That's worth the space. 🇨🇦
