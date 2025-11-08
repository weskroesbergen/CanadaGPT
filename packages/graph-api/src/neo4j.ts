/**
 * Neo4j driver initialization and connection management
 */

import neo4j, { Driver, Session } from 'neo4j-driver';
import { config } from './config.js';

let driver: Driver | null = null;

/**
 * Initialize Neo4j driver
 */
export function initializeDriver(): Driver {
  if (driver) {
    return driver;
  }

  console.log('🔌 Connecting to Neo4j...');
  console.log(`URI: ${config.neo4j.uri}`);

  driver = neo4j.driver(
    config.neo4j.uri,
    neo4j.auth.basic(config.neo4j.user, config.neo4j.password),
    {
      maxConnectionLifetime: 3 * 60 * 60 * 1000, // 3 hours
      maxConnectionPoolSize: 50,
      connectionAcquisitionTimeout: 2 * 60 * 1000, // 2 minutes
      encrypted: config.neo4j.uri.startsWith('bolt://') ? false : true,
    }
  );

  return driver;
}

/**
 * Get existing driver or throw error
 */
export function getDriver(): Driver {
  if (!driver) {
    throw new Error('Neo4j driver not initialized. Call initializeDriver() first.');
  }
  return driver;
}

/**
 * Test Neo4j connection
 */
export async function testConnection(): Promise<void> {
  const driver = getDriver();

  try {
    const session: Session = driver.session();
    const result = await session.run(
      'CALL dbms.components() YIELD name, versions, edition RETURN name, versions[0] AS version, edition'
    );

    const record = result.records[0];
    const name = record.get('name');
    const version = record.get('version');
    const edition = record.get('edition');

    console.log(`✅ Connected to ${name} ${version} (${edition})`);

    await session.close();
  } catch (error) {
    console.error('❌ Neo4j connection failed:', error);
    throw error;
  }
}

/**
 * Close Neo4j driver
 */
export async function closeDriver(): Promise<void> {
  if (driver) {
    console.log('🔌 Closing Neo4j connection...');
    await driver.close();
    driver = null;
    console.log('✅ Neo4j connection closed');
  }
}

/**
 * Get database statistics
 */
export async function getDatabaseStats(): Promise<{
  nodeCount: number;
  relationshipCount: number;
  labels: string[];
  relationshipTypes: string[];
}> {
  const driver = getDriver();
  const session = driver.session();

  try {
    // Get node count by label
    const labelResult = await session.run('MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count');
    const labels = labelResult.records.map((r) => r.get('label'));
    const nodeCount = labelResult.records.reduce((sum, r) => sum + r.get('count').toNumber(), 0);

    // Get relationship count by type
    const relResult = await session.run('MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count');
    const relationshipTypes = relResult.records.map((r) => r.get('type'));
    const relationshipCount = relResult.records.reduce((sum, r) => sum + r.get('count').toNumber(), 0);

    return {
      nodeCount,
      relationshipCount,
      labels,
      relationshipTypes,
    };
  } finally {
    await session.close();
  }
}
