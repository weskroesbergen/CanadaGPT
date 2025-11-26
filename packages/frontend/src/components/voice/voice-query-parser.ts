/**
 * Voice Query Parser for CanadaGPT
 * =================================
 * Converts natural language voice queries into Neo4j Cypher queries
 * Context-aware based on current page (MP, Bill, Debate)
 */

interface QueryContext {
  type?: 'mp' | 'bill' | 'debate' | 'general';
  mpId?: string;
  billId?: string;
  debateId?: string;
  mpName?: string;
  billNumber?: string;
}

interface ParsedQuery {
  intent: string;
  entities: {
    mps?: string[];
    bills?: string[];
    parties?: string[];
    topics?: string[];
    dates?: string[];
  };
  cypher: string;
  description: string;
}

/**
 * Parse natural language query into Cypher
 */
export function parseVoiceQuery(query: string, context?: QueryContext): ParsedQuery {
  const normalizedQuery = query.toLowerCase().trim();

  // Detect intent based on keywords
  const intent = detectIntent(normalizedQuery);

  // Extract entities
  const entities = extractEntities(normalizedQuery);

  // Generate Cypher based on intent and context
  const cypher = generateCypher(intent, entities, normalizedQuery, context);

  // Generate human-readable description
  const description = generateDescription(intent, entities, context);

  return {
    intent,
    entities,
    cypher,
    description,
  };
}

/**
 * Detect user intent from query
 */
function detectIntent(query: string): string {
  const intents = [
    { pattern: /show|find|search|get|give me|tell me about/i, intent: 'search' },
    { pattern: /how many|count|number of/i, intent: 'count' },
    { pattern: /compare|difference|versus|vs/i, intent: 'compare' },
    { pattern: /vote|voted|voting/i, intent: 'votes' },
    { pattern: /speech|said|spoke|statement/i, intent: 'speeches' },
    { pattern: /bill|legislation/i, intent: 'bills' },
    { pattern: /expense|spending|spent|cost/i, intent: 'expenses' },
    { pattern: /committee|meeting/i, intent: 'committees' },
    { pattern: /party|liberal|conservative|ndp|bloc|green/i, intent: 'party' },
  ];

  for (const { pattern, intent } of intents) {
    if (pattern.test(query)) {
      return intent;
    }
  }

  return 'search';
}

/**
 * Extract entities from query
 */
function extractEntities(query: string): ParsedQuery['entities'] {
  const entities: ParsedQuery['entities'] = {};

  // Extract MP names (common Canadian politician names)
  const mpPatterns = [
    'trudeau', 'poilievre', 'singh', 'blanchet', 'may',
    'freeland', 'carney', 'joly', 'duclos', 'anand',
  ];

  entities.mps = mpPatterns.filter((name) => query.includes(name.toLowerCase()));

  // Extract bill numbers
  const billMatch = query.match(/bill\s+[cs]-?\d+/gi);
  if (billMatch) {
    entities.bills = billMatch.map((b) => b.replace(/\s+/g, ' ').toUpperCase());
  }

  // Extract parties
  const partyPatterns = {
    liberal: /liberal/i,
    conservative: /conservative|tory/i,
    ndp: /ndp|new democratic/i,
    bloc: /bloc|bloc québécois/i,
    green: /green/i,
  };

  entities.parties = Object.entries(partyPatterns)
    .filter(([_, pattern]) => pattern.test(query))
    .map(([party]) => party.charAt(0).toUpperCase() + party.slice(1));

  // Extract topics
  const topicPatterns = [
    'climate', 'housing', 'healthcare', 'carbon tax', 'immigration',
    'economy', 'education', 'defense', 'energy', 'environment',
  ];

  entities.topics = topicPatterns.filter((topic) =>
    query.includes(topic.toLowerCase())
  );

  // Extract dates (simple patterns)
  const dateMatch = query.match(/\b\d{4}\b|\bthis (week|month|year)\b|\blast (week|month|year)\b/gi);
  if (dateMatch) {
    entities.dates = dateMatch;
  }

  return entities;
}

/**
 * Generate Cypher query based on intent and entities
 */
function generateCypher(
  intent: string,
  entities: ParsedQuery['entities'],
  query: string,
  context?: QueryContext
): string {
  // Context-aware queries
  if (context?.type === 'mp' && context.mpId) {
    return generateMPContextQuery(intent, entities, context.mpId);
  }

  if (context?.type === 'bill' && context.billId) {
    return generateBillContextQuery(intent, entities, context.billId);
  }

  if (context?.type === 'debate' && context.debateId) {
    return generateDebateContextQuery(intent, entities, context.debateId);
  }

  // General queries
  switch (intent) {
    case 'search':
      if (entities.mps && entities.mps.length > 0) {
        return `MATCH (mp:MP) WHERE toLower(mp.name) CONTAINS "${entities.mps[0]}" RETURN mp LIMIT 10`;
      }
      if (entities.bills && entities.bills.length > 0) {
        return `MATCH (b:Bill) WHERE b.number = "${entities.bills[0]}" RETURN b`;
      }
      return `MATCH (mp:MP) RETURN mp LIMIT 10`;

    case 'votes':
      if (entities.mps && entities.mps.length > 0) {
        return `
          MATCH (mp:MP)-[v:VOTED]->(vote:Vote)
          WHERE toLower(mp.name) CONTAINS "${entities.mps[0]}"
          RETURN mp.name, vote.description, v.position, vote.date
          ORDER BY vote.date DESC
          LIMIT 20
        `;
      }
      if (entities.bills && entities.bills.length > 0) {
        return `
          MATCH (vote:Vote)-[:CONCERNS]->(bill:Bill)
          WHERE bill.number = "${entities.bills[0]}"
          RETURN vote, bill
          ORDER BY vote.date DESC
        `;
      }
      return `MATCH (v:Vote) RETURN v ORDER BY v.date DESC LIMIT 20`;

    case 'speeches':
      if (entities.mps && entities.mps.length > 0 && entities.topics && entities.topics.length > 0) {
        return `
          MATCH (mp:MP)-[:MADE_BY]-(s:Statement)
          WHERE toLower(mp.name) CONTAINS "${entities.mps[0]}"
            AND toLower(s.content_en) CONTAINS "${entities.topics[0]}"
          RETURN mp.name, s.content_en, s.time, s.h2_en
          ORDER BY s.time DESC
          LIMIT 20
        `;
      }
      if (entities.mps && entities.mps.length > 0) {
        return `
          MATCH (mp:MP)-[:MADE_BY]-(s:Statement)
          WHERE toLower(mp.name) CONTAINS "${entities.mps[0]}"
          RETURN mp.name, s.content_en, s.time, s.h2_en
          ORDER BY s.time DESC
          LIMIT 20
        `;
      }
      return `MATCH (s:Statement) RETURN s ORDER BY s.time DESC LIMIT 20`;

    case 'bills':
      if (entities.topics && entities.topics.length > 0) {
        return `
          MATCH (b:Bill)
          WHERE toLower(b.title) CONTAINS "${entities.topics[0]}"
             OR toLower(b.summary) CONTAINS "${entities.topics[0]}"
          RETURN b
          ORDER BY b.introduced_date DESC
          LIMIT 20
        `;
      }
      return `MATCH (b:Bill) RETURN b ORDER BY b.introduced_date DESC LIMIT 20`;

    case 'expenses':
      if (entities.mps && entities.mps.length > 0) {
        return `
          MATCH (mp:MP)-[:HAS_EXPENSE]->(e:Expense)
          WHERE toLower(mp.name) CONTAINS "${entities.mps[0]}"
          RETURN mp.name, e.fiscal_year, e.quarter, e.category, e.amount
          ORDER BY e.fiscal_year DESC, e.quarter DESC
        `;
      }
      return `
        MATCH (mp:MP)-[:HAS_EXPENSE]->(e:Expense)
        RETURN mp.name, SUM(e.amount) as total
        ORDER BY total DESC
        LIMIT 20
      `;

    case 'committees':
      return `
        MATCH (c:Committee)
        RETURN c.name, c.code, c.mandate
        LIMIT 20
      `;

    case 'compare':
      if (entities.mps && entities.mps.length >= 2) {
        return `
          MATCH (mp1:MP)-[v1:VOTED]->(vote:Vote)<-[v2:VOTED]-(mp2:MP)
          WHERE toLower(mp1.name) CONTAINS "${entities.mps[0]}"
            AND toLower(mp2.name) CONTAINS "${entities.mps[1]}"
          RETURN mp1.name, mp2.name, vote.description, v1.position, v2.position, vote.date
          ORDER BY vote.date DESC
          LIMIT 20
        `;
      }
      return `MATCH (mp:MP) RETURN mp LIMIT 10`;

    case 'count':
      if (entities.bills) {
        return `MATCH (b:Bill) RETURN count(b) as bill_count`;
      }
      if (entities.mps) {
        return `MATCH (mp:MP {current: true}) RETURN count(mp) as mp_count`;
      }
      return `MATCH (n) RETURN labels(n) as type, count(n) as count`;

    default:
      return `MATCH (mp:MP) RETURN mp LIMIT 10`;
  }
}

/**
 * Generate MP-context-specific queries
 */
function generateMPContextQuery(
  intent: string,
  entities: ParsedQuery['entities'],
  mpId: string
): string {
  switch (intent) {
    case 'votes':
      if (entities.bills && entities.bills.length > 0) {
        return `
          MATCH (mp:MP {id: "${mpId}"})-[v:VOTED]->(vote:Vote)-[:CONCERNS]->(bill:Bill)
          WHERE bill.number = "${entities.bills[0]}"
          RETURN vote, v.position, bill.title
        `;
      }
      return `
        MATCH (mp:MP {id: "${mpId}"})-[v:VOTED]->(vote:Vote)
        RETURN vote.description, v.position, vote.date, vote.result
        ORDER BY vote.date DESC
        LIMIT 20
      `;

    case 'speeches':
      if (entities.topics && entities.topics.length > 0) {
        return `
          MATCH (mp:MP {id: "${mpId}"})-[:MADE_BY]-(s:Statement)
          WHERE toLower(s.content_en) CONTAINS "${entities.topics[0]}"
          RETURN s.content_en, s.time, s.h2_en
          ORDER BY s.time DESC
          LIMIT 20
        `;
      }
      return `
        MATCH (mp:MP {id: "${mpId}"})-[:MADE_BY]-(s:Statement)
        RETURN s.content_en, s.time, s.h2_en
        ORDER BY s.time DESC
        LIMIT 20
      `;

    case 'bills':
      return `
        MATCH (mp:MP {id: "${mpId}"})-[:SPONSORED]->(b:Bill)
        RETURN b
        ORDER BY b.introduced_date DESC
      `;

    case 'expenses':
      return `
        MATCH (mp:MP {id: "${mpId}"})-[:HAS_EXPENSE]->(e:Expense)
        RETURN e.fiscal_year, e.quarter, e.category, e.amount
        ORDER BY e.fiscal_year DESC, e.quarter DESC
      `;

    default:
      return `MATCH (mp:MP {id: "${mpId}"}) RETURN mp`;
  }
}

/**
 * Generate Bill-context-specific queries
 */
function generateBillContextQuery(
  intent: string,
  entities: ParsedQuery['entities'],
  billId: string
): string {
  switch (intent) {
    case 'votes':
      return `
        MATCH (bill:Bill {id: "${billId}"})<-[:CONCERNS]-(vote:Vote)<-[v:VOTED]-(mp:MP)
        RETURN mp.name, mp.party, v.position
        ORDER BY mp.party, mp.name
      `;

    case 'speeches':
      return `
        MATCH (bill:Bill {id: "${billId}"})
        MATCH (s:Statement)
        WHERE toLower(s.content_en) CONTAINS toLower(bill.number)
        RETURN s.who_en, s.content_en, s.time
        ORDER BY s.time DESC
        LIMIT 20
      `;

    case 'compare':
      if (entities.parties && entities.parties.length > 0) {
        return `
          MATCH (bill:Bill {id: "${billId}"})<-[:CONCERNS]-(vote:Vote)<-[v:VOTED]-(mp:MP)
          WHERE mp.party IN [${entities.parties.map((p) => `"${p}"`).join(',')}]
          RETURN mp.party, v.position, count(*) as count
        `;
      }
      return `
        MATCH (bill:Bill {id: "${billId}"})<-[:CONCERNS]-(vote:Vote)<-[v:VOTED]-(mp:MP)
        RETURN mp.party, v.position, count(*) as count
      `;

    default:
      return `MATCH (bill:Bill {id: "${billId}"}) RETURN bill`;
  }
}

/**
 * Generate Debate-context-specific queries
 */
function generateDebateContextQuery(
  intent: string,
  entities: ParsedQuery['entities'],
  debateId: string
): string {
  switch (intent) {
    case 'speeches':
      if (entities.mps && entities.mps.length > 0) {
        return `
          MATCH (d:Document {id: "${debateId}"})<-[:PART_OF]-(s:Statement)-[:MADE_BY]->(mp:MP)
          WHERE toLower(mp.name) CONTAINS "${entities.mps[0]}"
          RETURN s.content_en, s.time, mp.name
          ORDER BY s.time
        `;
      }
      if (entities.parties && entities.parties.length > 0) {
        return `
          MATCH (d:Document {id: "${debateId}"})<-[:PART_OF]-(s:Statement)-[:MADE_BY]->(mp:MP)
          WHERE mp.party = "${entities.parties[0]}"
          RETURN s.content_en, s.time, mp.name
          ORDER BY s.time
        `;
      }
      return `
        MATCH (d:Document {id: "${debateId}"})<-[:PART_OF]-(s:Statement)
        RETURN s.who_en, s.content_en, s.time
        ORDER BY s.time
      `;

    case 'count':
      return `
        MATCH (d:Document {id: "${debateId}"})<-[:PART_OF]-(s:Statement)
        RETURN count(DISTINCT s.who_en) as speaker_count,
               count(s) as statement_count
      `;

    default:
      return `MATCH (d:Document {id: "${debateId}"}) RETURN d`;
  }
}

/**
 * Generate human-readable description
 */
function generateDescription(
  intent: string,
  entities: ParsedQuery['entities'],
  context?: QueryContext
): string {
  if (context?.type === 'mp' && context.mpName) {
    switch (intent) {
      case 'votes':
        return `Finding ${context.mpName}'s voting record`;
      case 'speeches':
        return `Searching ${context.mpName}'s speeches`;
      case 'bills':
        return `Showing bills sponsored by ${context.mpName}`;
      default:
        return `Searching for information about ${context.mpName}`;
    }
  }

  if (context?.type === 'bill' && context.billNumber) {
    switch (intent) {
      case 'votes':
        return `Finding votes on ${context.billNumber}`;
      case 'speeches':
        return `Finding speeches about ${context.billNumber}`;
      default:
        return `Searching for information about ${context.billNumber}`;
    }
  }

  // General descriptions
  if (entities.mps && entities.mps.length > 0) {
    return `Searching for ${entities.mps.join(' and ')}`;
  }

  if (entities.bills && entities.bills.length > 0) {
    return `Finding information about ${entities.bills.join(' and ')}`;
  }

  if (entities.topics && entities.topics.length > 0) {
    return `Searching for ${entities.topics.join(', ')}`;
  }

  return 'Performing search...';
}

/**
 * Example usage:
 *
 * // General query
 * const result = parseVoiceQuery("Show me Pierre Poilievre's votes on Bill C-21");
 *
 * // MP page context
 * const mpResult = parseVoiceQuery("What has he said about carbon tax?", {
 *   type: 'mp',
 *   mpId: 'pierre-poilievre',
 *   mpName: 'Pierre Poilievre'
 * });
 *
 * // Bill page context
 * const billResult = parseVoiceQuery("How did Liberals vote?", {
 *   type: 'bill',
 *   billId: '45-1-c-21',
 *   billNumber: 'Bill C-21'
 * });
 */
