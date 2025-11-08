/**
 * CanadaGPT GraphQL API
 *
 * Entry point for the GraphQL server.
 * Connects to Neo4j and serves GraphQL API for government accountability data.
 */

import { validateConfig } from './config.js';
import { initializeDriver, testConnection, closeDriver, getDatabaseStats } from './neo4j.js';
import { startServer } from './server.js';

async function main() {
  try {
    console.log('');
    console.log('═══════════════════════════════════════════════════════════');
    console.log('🇨🇦 CanadaGPT GraphQL API');
    console.log('═══════════════════════════════════════════════════════════');
    console.log('');

    // 1. Validate configuration
    validateConfig();
    console.log('');

    // 2. Initialize Neo4j driver
    initializeDriver();

    // 3. Test Neo4j connection
    await testConnection();

    // 4. Get database stats
    const stats = await getDatabaseStats();
    console.log('');
    console.log('📊 Database Statistics:');
    console.log(`   Nodes: ${stats.nodeCount.toLocaleString()}`);
    console.log(`   Relationships: ${stats.relationshipCount.toLocaleString()}`);
    console.log(`   Node Types: ${stats.labels.length}`);
    console.log(`   Relationship Types: ${stats.relationshipTypes.length}`);
    console.log('');

    // 5. Start GraphQL server
    const server = await startServer();

    // 6. Graceful shutdown
    const shutdown = async () => {
      console.log('');
      console.log('⚠️  Shutting down gracefully...');

      server.close(() => {
        console.log('✅ HTTP server closed');
      });

      await closeDriver();
      console.log('✅ Shutdown complete');
      process.exit(0);
    };

    process.on('SIGTERM', shutdown);
    process.on('SIGINT', shutdown);

  } catch (error) {
    console.error('');
    console.error('❌ Failed to start server:', error);
    console.error('');

    // Try to close driver if it was initialized
    try {
      await closeDriver();
    } catch (closeError) {
      // Ignore errors during cleanup
    }

    process.exit(1);
  }
}

// Start the server
main();
