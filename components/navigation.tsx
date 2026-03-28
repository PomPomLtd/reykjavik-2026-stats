'use client'

import Link from 'next/link'
import Image from 'next/image'

export function Navigation() {
  return (
    <nav className="relative z-50" style={{ backgroundColor: '#132F3A' }}>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <Link href="/" className="flex items-center gap-3 text-white font-bold text-xl hover:opacity-90 transition-opacity">
            <Image
              src="/favicon.svg"
              alt="Logo"
              width={32}
              height={32}
              className="w-8 h-8"
            />
            <span>Reykjavik 2026</span>
          </Link>
          <a
            href="https://lichess.org/study/lGf88qOA"
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-300 hover:text-white text-sm transition-colors"
          >
            Lichess Study
          </a>
        </div>
      </div>
    </nav>
  )
}
