import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Output mode for production builds (standalone for Docker)
  output: 'standalone',

  // Environment variables exposed to browser
  env: {
    NEXT_PUBLIC_GRAPHQL_URL: process.env.NEXT_PUBLIC_GRAPHQL_URL,
  },

  // Webpack configuration
  webpack: (config, { dev }) => {
    if (dev) {
      // Increase chunk load timeout in development
      config.output.chunkLoadTimeout = 120000; // 2 minutes
    }
    return config;
  },

  // Image optimization
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'www.ourcommons.ca',
        pathname: '/Content/Parliamentarians/Images/**',
      },
    ],
  },

  // Experimental features
  experimental: {
    optimizeCss: true,
  },

  // Headers for security
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin',
          },
        ],
      },
    ];
  },
};

export default withNextIntl(nextConfig);
