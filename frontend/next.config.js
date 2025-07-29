/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://3.115.30.125:8000/api/:path*', // 本番環境のAPI URL
      },
    ]
  },
}

module.exports = nextConfig