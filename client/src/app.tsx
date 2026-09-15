import { PropsWithChildren, useEffect } from 'react'
import { useUserStore } from '@/stores/user'
import './app.scss'

function App({ children }: PropsWithChildren) {
  useEffect(() => {
    // 启动即确保本地设备 ID 存在（匿名用户体系）
    useUserStore.getState().ensureClientId()
  }, [])

  return children
}

export default App
