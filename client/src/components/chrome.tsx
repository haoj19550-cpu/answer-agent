import Taro from '@tarojs/taro'
import { Text, View } from '@tarojs/components'
import Icon from './Icon'

/** 页面骨架：导航栏 / TabBar（模块识别色只染外壳） */

interface NavBarProps {
  title: string
  back?: boolean
  onBack?: () => void
}

export function NavBar({ title, back = false, onBack }: NavBarProps) {
  const handleBack = () => {
    if (onBack) {
      onBack()
      return
    }
    Taro.navigateBack({ fail: () => Taro.reLaunch({ url: '/pages/home/index' }) })
  }
  return (
    <View className="nb">
      {back ? (
        <View className="nb-b" onClick={handleBack}>
          <Icon name="left" size={20} color="#101A2E" />
        </View>
      ) : (
        <Text className="nb-t">{title}</Text>
      )}
      {back && <Text className="nb-c">{title}</Text>}
    </View>
  )
}

type TabKey = 'home' | 'history' | 'profile'

const TABS: Array<{ key: TabKey; label: string; icon: 'home' | 'book' | 'user'; url: string }> = [
  { key: 'home', label: '首页', icon: 'home', url: '/pages/home/index' },
  { key: 'history', label: '学习记录', icon: 'book', url: '/pages/history/index' },
  { key: 'profile', label: '我的', icon: 'user', url: '/pages/profile/index' },
]

export function TabBar({ active }: { active: TabKey }) {
  return (
    <View className="tb">
      {TABS.map((tab) => (
        <View
          key={tab.key}
          className={`tb-i ${active === tab.key ? 'on' : ''}`}
          onClick={() => {
            if (tab.key !== active) Taro.reLaunch({ url: tab.url })
          }}
        >
          <Icon name={tab.icon} size={20} color={active === tab.key ? '#2B4EFF' : '#8A97AC'} />
          <Text>{tab.label}</Text>
        </View>
      ))}
    </View>
  )
}

interface PageProps {
  module?: 'in' | 'ai' | 'quiz' | 'data' | 'err'
  children: React.ReactNode
}

/** 页面容器：pg 类承载模块识别色变量 */
export function Page({ module = 'in', children }: PageProps) {
  return <View className={`pg ${module === 'in' ? '' : `m-${module}`}`}>{children}</View>
}
