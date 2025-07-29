/** @type {import('next').NextConfig} */
const path = require('path')

const nextConfig = {
  reactStrictMode: true,
  webpack: (config) => {
    config.resolve.alias['@'] = path.join(__dirname)
    return config
  },
  // nginx でAPIプロキシを処理するため、Next.jsのrewriteは無効化
}

module.exports = nextConfig