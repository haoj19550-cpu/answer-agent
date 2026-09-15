import { Image } from '@tarojs/components'

/** Lucide 风格线性图标（prototype2 精灵移植，SVG data-URI 双端兼容） */

const PATHS: Record<string, string> = {
  home: '<path d="M3 10.6 12 3.2l9 7.4"/><path d="M5.4 9.4V20.8h13.2V9.4"/><path d="M9.6 20.8v-6.2h4.8v6.2"/>',
  book: '<path d="M4 4.8h6a2.6 2.6 0 0 1 2 2.6v12a2.2 2.2 0 0 0-2-2H4z"/><path d="M20 4.8h-6a2.6 2.6 0 0 0-2 2.6v12a2.2 2.2 0 0 1 2-2h6z"/>',
  user: '<circle cx="12" cy="8.2" r="3.6"/><path d="M4.8 20.2a7.2 7.2 0 0 1 14.4 0"/>',
  left: '<path d="M14.8 5.4 8.2 12l6.6 6.6"/>',
  right: '<path d="M9.2 5.4 15.8 12l-6.6 6.6"/>',
  check: '<path d="M4.8 12.6 9.6 17.4 19.2 6.8"/>',
  x: '<path d="M6.4 6.4 17.6 17.6M17.6 6.4 6.4 17.6"/>',
  clock: '<circle cx="12" cy="12" r="8.6"/><path d="M12 7.2V12l3.2 2"/>',
  flame: '<path d="M12 2.8s5.6 4 5.6 9.2A5.6 5.6 0 0 1 12 21.2a5.6 5.6 0 0 1-5.6-9.2c0-2 1.2-3.6 1.2-3.6s.4 1.8 1.8 2.4c0-3 2.6-5.4 2.6-8z"/>',
  zap: '<path d="M13.4 2.6 4.8 13.4h6L10.2 21.4l8.8-11h-6.2z"/>',
  award: '<circle cx="12" cy="9.2" r="5.6"/><path d="M8.4 14 7 21.2l5-2.6 5 2.6-1.4-7.2"/>',
  target: '<circle cx="12" cy="12" r="8.6"/><circle cx="12" cy="12" r="4.6"/><circle cx="12" cy="12" r="1"/>',
  sparkle: '<path d="M12 3.2 13.9 9 19.8 11 13.9 13 12 18.8 10.1 13 4.2 11 10.1 9z"/><path d="M18.6 16.4 19.4 18.6 21.6 19.4 19.4 20.2 18.6 22.4 17.8 20.2 15.6 19.4 17.8 18.6z"/>',
  refresh: '<path d="M20.4 11.2A8.4 8.4 0 1 0 19 16.4"/><path d="M20.8 5.6v5.6h-5.6"/>',
  share: '<path d="M12 15.6V3.8"/><path d="m8 7.4 4-3.6 4 3.6"/><path d="M4.8 13.2v5.2a1.8 1.8 0 0 0 1.8 1.8h10.8a1.8 1.8 0 0 0 1.8-1.8v-5.2"/>',
  alert: '<path d="M10.5 3.9 2.6 17.4a1.7 1.7 0 0 0 1.5 2.6h15.8a1.7 1.7 0 0 0 1.5-2.6L13.5 3.9a1.7 1.7 0 0 0-3 0z"/><path d="M12 9.4v4.2M12 17h.01"/>',
  info: '<circle cx="12" cy="12" r="8.6"/><path d="M12 11v5.2M12 7.9h.01"/>',
  upload: '<path d="M12 16.4V4.6"/><path d="m7.8 8.6 4.2-4 4.2 4"/><path d="M4.4 15v3.6a1.8 1.8 0 0 0 1.8 1.8h11.6a1.8 1.8 0 0 0 1.8-1.8V15"/>',
  file: '<path d="M13.6 3.2H7a1.8 1.8 0 0 0-1.8 1.8v14a1.8 1.8 0 0 0 1.8 1.8h10a1.8 1.8 0 0 0 1.8-1.8V8.4z"/><path d="M13.6 3.2v5.2h5.2"/>',
  link: '<path d="M10.2 13.8a4 4 0 0 0 5.7 0l2.9-2.9a4 4 0 0 0-5.7-5.7l-1.2 1.2"/><path d="M13.8 10.2a4 4 0 0 0-5.7 0l-2.9 2.9a4 4 0 0 0 5.7 5.7l1.2-1.2"/>',
  layers: '<path d="m12 3.2 8.8 4.6L12 12.4 3.2 7.8z"/><path d="m3.2 12.4 8.8 4.6 8.8-4.6"/><path d="m3.2 16.8 8.8 4.6 8.8-4.6"/>',
  shield: '<path d="M12 3.2 4.8 6v6c0 4.4 3 7.6 7.2 8.8 4.2-1.2 7.2-4.4 7.2-8.8V6z"/><path d="m9.4 12 1.8 1.8 3.4-3.6"/>',
  bookmark: '<path d="M6.4 3.8h11.2v17L12 16.6l-5.6 4.2z"/>',
  play: '<path d="M7.2 4.8 19 12 7.2 19.2z"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M12 3.4v1.8M12 18.8v1.8M3.4 12h1.8M18.8 12h1.8M6 6l1.3 1.3M16.7 16.7 18 18M6 18l1.3-1.3M16.7 7.3 18 6"/>',
  map: '<path d="m9 4.2-5.4 2.2v13.4L9 17.6l6 2.2 5.4-2.2V4.2L15 6.4z"/><path d="M9 4.2v13.4M15 6.4v13.4"/>',
  trophy: '<path d="M7.2 4h9.6v5a4.8 4.8 0 0 1-9.6 0z"/><path d="M7.2 5.6H4.4v1.6a3.2 3.2 0 0 0 3 3.2M16.8 5.6h2.8v1.6a3.2 3.2 0 0 1-3 3.2"/><path d="M12 13.8v3.4M8.8 20.4h6.4l-.8-3.2H9.6z"/>',
  dots: '<circle cx="5.6" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="18.4" cy="12" r="1.3"/>',
}

export type IconName = keyof typeof PATHS

export function iconSrc(name: IconName, color = '#5A6A85'): string {
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="${color}" ` +
    `stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">${PATHS[name]}</svg>`
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
}

interface IconProps {
  name: IconName
  size?: number
  color?: string
  style?: React.CSSProperties
}

export default function Icon({ name, size = 24, color = '#5A6A85', style }: IconProps) {
  return (
    <Image
      src={iconSrc(name, color)}
      style={{ width: `${size}px`, height: `${size}px`, flexShrink: 0, ...style }}
      mode="aspectFit"
    />
  )
}
