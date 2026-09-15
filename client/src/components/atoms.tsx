import { Text, View } from '@tarojs/components'
import Icon, { type IconName } from './Icon'

/** 原子组件：Chip / Ring / Bar / Seg / Nodes / Option / Stage */

type ChipTone = 'default' | 'br' | 'mt' | 'am' | 'co' | 'gd' | 'gh' | 'pick' | 'sc'

const CHIP_COLORS: Record<ChipTone, string> = {
  default: '#5A6A85',
  br: '#2B4EFF',
  mt: '#00775F',
  am: '#8A6100',
  co: '#B32B2B',
  gd: '#7A6200',
  gh: '#5A6A85',
  pick: '#FFFFFF',
  sc: '#B4530F',
}

export function Chip({
  tone = 'default',
  icon,
  iconColor,
  children,
  onClick,
  style,
}: {
  tone?: ChipTone
  icon?: IconName
  iconColor?: string
  children?: React.ReactNode
  onClick?: () => void
  style?: React.CSSProperties
}) {
  return (
    <View className={`chip ${tone === 'default' ? '' : tone}`} onClick={onClick} style={style}>
      {icon && <Icon name={icon} size={14} color={iconColor || CHIP_COLORS[tone]} />}
      <Text>{children}</Text>
    </View>
  )
}

export function Ring({
  percent,
  color = '#2B4EFF',
  small = false,
  label,
}: {
  percent: number
  color?: string
  small?: boolean
  label?: string
}) {
  return (
    <View
      className={`ring ${small ? 'sm' : ''}`}
      style={{ ['--p' as string]: String(percent), ['--rc' as string]: color }}
    >
      <View className="ring-i" />
      <View className="rv">
        <Text className="rv-b">{percent}</Text>
        {label && <Text className="rv-s">{label}</Text>}
      </View>
    </View>
  )
}

export function Bar({ percent, tone, large = false }: { percent: number; tone?: 'mt' | 'am' | 'co'; large?: boolean }) {
  return (
    <View className={`bar ${tone || ''} ${large ? 'lg' : ''}`}>
      <View className="bar-i" style={{ width: `${percent}%` }} />
    </View>
  )
}

export function Seg<T extends string | number>({
  options,
  value,
  onChange,
  square = false,
}: {
  options: Array<{ value: T; label: string }>
  value: T
  onChange: (v: T) => void
  square?: boolean
}) {
  return (
    <View className={`seg ${square ? 'sq' : ''}`}>
      {options.map((opt) => (
        <View
          key={String(opt.value)}
          className={`seg-i ${value === opt.value ? 'on' : ''}`}
          onClick={() => onChange(opt.value)}
        >
          {opt.label}
        </View>
      ))}
    </View>
  )
}

export type NodeState = 'todo' | 'done' | 'now' | 'miss'

export function Nodes({ states }: { states: NodeState[] }) {
  return (
    <View className="nodes">
      {states.map((s, i) => (
        <View key={i} style={{ display: 'contents' }}>
          {i > 0 && <View className={`lk ${states[i - 1] === 'done' ? 'done' : ''}`} />}
          <View className={`nd ${s === 'todo' ? '' : s}`}>
            {s === 'done' ? (
              <Icon name="check" size={14} color="#06302A" />
            ) : s === 'miss' ? (
              <Icon name="x" size={14} color="#FFFFFF" />
            ) : (
              <Text>{i + 1}</Text>
            )}
          </View>
        </View>
      ))}
    </View>
  )
}

export type OptionState = 'idle' | 'sel' | 'ok' | 'bad' | 'dim'

export function Option({
  letter,
  text,
  state = 'idle',
  onClick,
}: {
  letter: string
  text: string
  state?: OptionState
  onClick?: () => void
}) {
  return (
    <View className={`opt ${state === 'idle' ? '' : state}`} onClick={onClick}>
      <View className="k">{letter}</View>
      <Text className="tx">{text}</Text>
    </View>
  )
}

export type StageStatus = 'todo' | 'now' | 'done'

export function StageItem({
  icon,
  title,
  sub,
  status,
}: {
  icon: IconName
  title: string
  sub: string
  status: StageStatus
}) {
  return (
    <View className={`stage ${status === 'todo' ? '' : status}`}>
      <View className="ic-wrap">
        {status === 'done' ? (
          <Icon name="check" size={14} color="#06302A" />
        ) : status === 'now' ? (
          <View className="spin" />
        ) : (
          <Icon name={icon} size={14} color="#8A97AC" />
        )}
      </View>
      <View className="grow">
        <View className="st-t">{title}</View>
        <View className="st-s">{sub}</View>
      </View>
    </View>
  )
}
