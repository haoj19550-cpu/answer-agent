import { Image } from '@tarojs/components'

/** 吉祥物「闯闯」（prototype2 原创 SVG 移植，data-URI 双端兼容） */

const MZ_BASE =
  '<ellipse cx="60" cy="112" rx="30" ry="5" fill="#101A2E" opacity=".08"/>' +
  '<circle cx="60" cy="64" r="40" fill="#4C6FFF"/>' +
  '<path d="M60 24a40 40 0 0 1 40 40H20a40 40 0 0 1 40-40z" fill="#6E86FF" opacity=".5"/>' +
  '<ellipse cx="60" cy="80" rx="25" ry="18" fill="#EAEFFF"/>' +
  '<circle cx="46" cy="56" r="11" fill="#fff"/><circle cx="74" cy="56" r="11" fill="#fff"/>' +
  '<circle cx="48" cy="57" r="5" fill="#101A2E"/><circle cx="72" cy="57" r="5" fill="#101A2E"/>' +
  '<circle cx="50" cy="55" r="1.8" fill="#fff"/><circle cx="74" cy="55" r="1.8" fill="#fff"/>' +
  '<circle cx="34" cy="68" r="5" fill="#FF9E9E" opacity=".85"/><circle cx="86" cy="68" r="5" fill="#FF9E9E" opacity=".85"/>' +
  '<path d="M52 70q8 8 16 0" fill="none" stroke="#101A2E" stroke-width="3" stroke-linecap="round"/>' +
  '<path d="M60 24V14" stroke="#1E3AD1" stroke-width="4" stroke-linecap="round"/>' +
  '<path d="M60 3l3 6.4 6.6 1-4.8 4.7 1.1 6.6-5.9-3.1-5.9 3.1 1.1-6.6-4.8-4.7 6.6-1z" fill="#FFD84D"/>' +
  '<ellipse cx="46" cy="105" rx="10" ry="6" fill="#1E3AD1"/><ellipse cx="74" cy="105" rx="10" ry="6" fill="#1E3AD1"/>'

const VARIANTS: Record<string, string> = {
  hi: MZ_BASE +
    '<path d="M98 66q14-10 12-26" fill="none" stroke="#1E3AD1" stroke-width="9" stroke-linecap="round"/>' +
    '<circle cx="110" cy="38" r="7" fill="#4C6FFF"/>' +
    '<path d="M22 70q-8 8-6 18" fill="none" stroke="#1E3AD1" stroke-width="9" stroke-linecap="round"/>' +
    '<circle cx="16" cy="90" r="7" fill="#4C6FFF"/>',
  yay: MZ_BASE +
    '<path d="M96 62q12-14 8-28M24 62q-12-14-8-28" stroke="#1E3AD1" stroke-width="9" fill="none" stroke-linecap="round"/>' +
    '<circle cx="104" cy="30" r="7" fill="#4C6FFF"/><circle cx="16" cy="30" r="7" fill="#4C6FFF"/>' +
    '<rect x="6" y="10" width="6" height="11" rx="2" fill="#FFD84D" transform="rotate(-20 9 15)"/>' +
    '<rect x="106" y="6" width="6" height="11" rx="2" fill="#00D3A7" transform="rotate(18 109 11)"/>' +
    '<rect x="28" y="2" width="6" height="11" rx="2" fill="#FF5C5C" transform="rotate(10 31 7)"/>',
  think: MZ_BASE +
    '<path d="M96 70q-4 14-20 16" stroke="#1E3AD1" stroke-width="9" fill="none" stroke-linecap="round"/>' +
    '<circle cx="74" cy="88" r="7" fill="#4C6FFF"/>' +
    '<rect x="84" y="4" width="32" height="27" rx="10" fill="#fff" stroke="#E6EAF1"/>' +
    '<path d="M92 30l4 9 6-9z" fill="#fff"/>' +
    '<text x="100" y="24" text-anchor="middle" font-size="18" font-weight="800" fill="#7C3AED" font-family="sans-serif">?</text>',
  pat: MZ_BASE +
    '<path d="M26 72q6 14 20 16M94 72q-6 14-20 16" stroke="#1E3AD1" stroke-width="9" fill="none" stroke-linecap="round"/>' +
    '<path d="M60 100c-9-7-15-11-15-17a8 8 0 0 1 15-5 8 8 0 0 1 15 5c0 6-6 10-15 17z" fill="#FF5C5C"/>',
  read: MZ_BASE +
    '<path d="M26 82h30v24H32a6 6 0 0 1-6-6z" fill="#fff" stroke="#1E3AD1" stroke-width="3"/>' +
    '<path d="M94 82H64v24h24a6 6 0 0 0 6-6z" fill="#fff" stroke="#1E3AD1" stroke-width="3"/>' +
    '<path d="M56 82q4-4 8 0v24q-4-4-8 0z" fill="#EAEFFF" stroke="#1E3AD1" stroke-width="3"/>' +
    '<path d="M33 91h16M33 98h16M71 91h16M71 98h16" stroke="#8A97AC" stroke-width="2.5" stroke-linecap="round"/>',
  zzz: MZ_BASE +
    '<circle cx="46" cy="56" r="11.5" fill="#4C6FFF"/><circle cx="74" cy="56" r="11.5" fill="#4C6FFF"/>' +
    '<path d="M38 56q8 7 16 0M66 56q8 7 16 0" stroke="#101A2E" stroke-width="3" fill="none" stroke-linecap="round"/>' +
    '<text x="96" y="34" font-size="22" font-weight="800" fill="#8A97AC" font-family="sans-serif">z</text>' +
    '<text x="108" y="20" font-size="15" font-weight="800" fill="#C3CBD9" font-family="sans-serif">z</text>',
  wrench: MZ_BASE +
    '<circle cx="46" cy="56" r="11.5" fill="#4C6FFF"/><circle cx="74" cy="56" r="11.5" fill="#4C6FFF"/>' +
    '<path d="M40 52q6-6 12 0M68 52q6-6 12 0" stroke="#101A2E" stroke-width="3" fill="none" stroke-linecap="round"/>' +
    '<circle cx="48" cy="59" r="4" fill="#101A2E"/><circle cx="72" cy="59" r="4" fill="#101A2E"/>' +
    '<path d="M54 73q6-5 12 0" fill="none" stroke="#101A2E" stroke-width="3" stroke-linecap="round"/>' +
    '<path d="M96 74q10-6 12-18" stroke="#1E3AD1" stroke-width="9" fill="none" stroke-linecap="round"/>' +
    '<g transform="rotate(24 106 44)"><path d="M99 33a10 10 0 1 0 13 13l-7-2-2-7z" fill="#8A97AC"/>' +
    '<rect x="104" y="44" width="9" height="22" rx="4.5" fill="#8A97AC"/></g>',
  cap: MZ_BASE +
    '<circle cx="60" cy="18" r="11" fill="#4C6FFF"/>' +
    '<path d="M60 10 18 27l42 17 42-17z" fill="#1E3AD1"/>' +
    '<path d="M36 33v11c0 6 11 10 24 10s24-4 24-10V33" fill="#4C6FFF"/>' +
    '<path d="M102 27v19" stroke="#FFD84D" stroke-width="3"/><circle cx="102" cy="48" r="4.5" fill="#FFD84D"/>',
}

export type MascotVariant = keyof typeof VARIANTS

interface MascotProps {
  variant: MascotVariant
  size?: number
  bob?: boolean
  style?: React.CSSProperties
}

export default function Mascot({ variant, size = 64, bob = true, style }: MascotProps) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">${VARIANTS[variant]}</svg>`
  const src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
  return (
    <Image
      src={src}
      className={bob ? 'mz' : ''}
      style={{ width: `${size}px`, height: `${size}px`, display: 'block', flexShrink: 0, ...style }}
      mode="aspectFit"
    />
  )
}
