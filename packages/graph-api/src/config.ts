/**
 * Configuration management for GraphQL API
 */

import { config as loadEnv } from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

// Load .env file
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
loadEnv({ path: join(__dirname, '../.env') });

export interface Config {
  neo4j: {
    uri: string;
    user: string;
    password: string;
  };
  server: {
    port: number;
    host: string;
  };
  graphql: {
    introspection: boolean;
    playground: boolean;
  };
  cors: {
    origins: string[];
  };
  nodeEnv: string;
}

function getRequiredEnv(key: string): string {
  const value = process.env[key];
  if (!value) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value;
}

function getEnv(key: string, defaultValue: string): string {
  return process.env[key] || defaultValue;
}

export const config: Config = {
  neo4j: {
    uri: getRequiredEnv('NEO4J_URI'),
    user: getEnv('NEO4J_USER', 'neo4j'),
    password: getRequiredEnv('NEO4J_PASSWORD'),
  },
  server: {
    port: parseInt(getEnv('PORT', '4000'), 10),
    host: getEnv('HOST', '0.0.0.0'),
  },
  graphql: {
    introspection: getEnv('GRAPHQL_INTROSPECTION', 'true') === 'true',
    playground: getEnv('GRAPHQL_PLAYGROUND', 'true') === 'true',
  },
  cors: {
    origins: getEnv('CORS_ORIGINS', 'http://localhost:3000').split(','),
  },
  nodeEnv: getEnv('NODE_ENV', 'development'),
};

export function validateConfig(): void {
  console.log('🔍 Validating configuration...');
  console.log(`Neo4j URI: ${config.neo4j.uri}`);
  console.log(`Server Port: ${config.server.port}`);
  console.log(`CORS Origins: ${config.cors.origins.join(', ')}`);
  console.log(`Environment: ${config.nodeEnv}`);
  console.log('✅ Configuration valid');
}
