import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // Pôsteres vêm do TMDB (poster_url da API)
    remotePatterns: [
      { protocol: "https", hostname: "image.tmdb.org", pathname: "/t/p/**" },
    ],
  },
};

export default nextConfig;
