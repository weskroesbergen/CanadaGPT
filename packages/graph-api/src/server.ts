/**
 * GraphQL server setup with GraphQL Yoga and @neo4j/graphql
 */

import { createYoga } from 'graphql-yoga';
import { Neo4jGraphQL } from '@neo4j/graphql';
import { createServer } from 'http';
import { typeDefs } from './schema.js';
import { getDriver } from './neo4j.js';
import { config } from './config.js';
import { fetchMPNews } from './utils/newsFetcher.js';

export interface ServerContext {
  req: Request;
}

/**
 * Create GraphQL schema with Neo4j integration
 */
export function createGraphQLSchema() {
  const driver = getDriver();

  const neoSchema = new Neo4jGraphQL({
    typeDefs,
    driver,
    resolvers: {
      Query: {
        mpNews: async (_parent: unknown, args: { mpName: string; limit?: number }) => {
          const { mpName, limit = 10 } = args;
          return await fetchMPNews(mpName, limit);
        },
      },
    },
    features: {
      authorization: {
        key: 'not-used-yet', // TODO: Add JWT auth in production
      },
    },
  });

  return neoSchema;
}

/**
 * Create GraphQL Yoga server
 */
export async function createGraphQLServer() {
  console.log('🚀 Creating GraphQL server...');

  const neoSchema = createGraphQLSchema();
  const schema = await neoSchema.getSchema();

  const yoga = createYoga<ServerContext>({
    schema,
    graphqlEndpoint: '/graphql',
    landingPage: config.graphql.playground,
    graphiql: config.graphql.playground
      ? {
          title: 'CanadaGPT GraphQL API',
          defaultQuery: `# Welcome to CanadaGPT GraphQL API
#
# Example queries:

# 1. List MPs with pagination
query ListMPs {
  mPs(options: { limit: 10, sort: [{ name: ASC }] }) {
    id
    name
    party
    riding
    current
  }
}

# 2. Get MP with relationships
query GetMP {
  mPs(where: { name: "Pierre Poilievre" }) {
    id
    name
    party
    riding
    memberOf {
      name
      code
    }
    represents {
      name
      province
    }
    sponsored {
      number
      title
      status
    }
  }
}

# 3. MP Performance Scorecard
query MPScorecard {
  mpScorecard(mpId: "pierre-poilievre") {
    mp {
      name
      party
    }
    bills_sponsored
    bills_passed
    votes_participated
    legislative_effectiveness
    lobbyist_meetings
  }
}

# 4. Top Spenders
query TopSpenders {
  topSpenders(fiscalYear: 2025, limit: 10) {
    mp {
      name
      party
    }
    total_expenses
  }
}

# 5. Bill Lobbying Activity
query BillLobbying {
  billLobbying(billNumber: "C-11", session: "44-1") {
    bill {
      title
      status
    }
    organizations_lobbying
    organizations {
      name
      industry
      lobbying_count
    }
  }
}`,
        }
      : false,
    cors: {
      origin: config.cors.origins,
      credentials: true,
    },
    maskedErrors: config.nodeEnv === 'production',
  });

  console.log('✅ GraphQL server created');
  return yoga;
}

/**
 * Start HTTP server
 */
export async function startServer() {
  const yoga = await createGraphQLServer();

  const server = createServer(yoga);

  return new Promise<typeof server>((resolve, reject) => {
    server.listen(config.server.port, config.server.host, () => {
      console.log('');
      console.log('═══════════════════════════════════════════════════════════');
      console.log('🚀 CanadaGPT GraphQL API');
      console.log('═══════════════════════════════════════════════════════════');
      console.log(`📡 Server running at http://${config.server.host}:${config.server.port}/graphql`);
      console.log(`🎮 GraphiQL: http://localhost:${config.server.port}/graphql`);
      console.log(`🌍 Environment: ${config.nodeEnv}`);
      console.log('═══════════════════════════════════════════════════════════');
      console.log('');
      resolve(server);
    });

    server.on('error', (error) => {
      console.error('❌ Server failed to start:', error);
      reject(error);
    });
  });
}
