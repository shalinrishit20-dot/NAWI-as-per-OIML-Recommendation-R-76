import type { NextConfig } from 'next';

const backendOrigin = (
  process.env.NAWI_BACKEND_ORIGIN ?? 'http://127.0.0.1:5000'
).replace(/\/+$/, '');

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: '/api/:path*', destination: `${backendOrigin}/api/:path*` },
      { source: '/media/:path*', destination: `${backendOrigin}/media/:path*` },
    ];
  },
};

export default nextConfig;
