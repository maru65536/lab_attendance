/** @type {import('next').NextConfig} */
const path = require('path')

const nextConfig = {
  reactStrictMode: true,
  basePath: '/lab_attendance',
  assetPrefix: '/lab_attendance',
  trailingSlash: true,
  poweredByHeader: false,
  generateEtags: false,
  compress: true,
  webpack: (config) => {
    config.resolve.alias['@'] = path.join(__dirname)
    return config
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ]
  },
}

module.exports = nextConfig