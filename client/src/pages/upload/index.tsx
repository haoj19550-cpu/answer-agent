import { useState } from 'react'
import Taro from '@tarojs/taro'
import { Text, Textarea, View } from '@tarojs/components'
import { Page, NavBar } from '@/components/chrome'
import Icon from '@/components/Icon'
import Mascot from '@/components/Mascot'
import { useQuizStore } from '@/stores/quiz'
import { useUserStore } from '@/stores/user'
import { createMaterial, uploadPdf } from '@/services/api'
import { RequestError } from '@/services/request'

const MAX_CHARS = 20000

interface PickedFile {
  name: string
  size: string
  path: string
}

function formatSize(bytes: number): string {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`
}

export default function UploadPage() {
  const [file, setFile] = useState<PickedFile | null>(null)
  const [fileError, setFileError] = useState('')
  const [text, setText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const { setMaterial, setInput, reset } = useQuizStore()
  const { clientId } = useUserStore()

  const pickFile = () => {
    if (process.env.TARO_ENV !== 'weapp') {
      Taro.showToast({ title: 'H5 预览请直接粘贴文字', icon: 'none' })
      return
    }
    Taro.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['pdf'],
      success: async (res) => {
        const f = res.tempFiles[0]
        setFileError('')
        setSubmitting(true)
        try {
          const material = await uploadPdf(clientId, f.path)
          setMaterial(material.material_id, material.title)
          setFile({ name: f.name, size: formatSize(f.size), path: f.path })
          Taro.showToast({ title: '解析成功', icon: 'success' })
        } catch (err) {
          const e = err as RequestError
          setFile({ name: f.name, size: formatSize(f.size), path: f.path })
          setFileError(
            e.code === 'PDF_PARSE_FAILED'
              ? e.message
              : e.message || '上传失败，请重试',
          )
        } finally {
          setSubmitting(false)
        }
      },
    })
  }

  const submit = async () => {
    if (submitting) return
    // PDF 已解析成功 → 直接进入生成
    if (file && !fileError && useQuizStore.getState().materialId) {
      reset()
      Taro.navigateTo({ url: '/pages/generating/index?phase=extract' })
      return
    }
    const value = text.trim()
    if (!value) {
      Taro.showToast({ title: '先选择 PDF 或粘贴文字', icon: 'none' })
      return
    }
    setSubmitting(true)
    try {
      const material = await createMaterial(clientId, 'text', value)
      reset()
      setMaterial(material.material_id, material.title)
      setInput(value.slice(0, 30))
      Taro.navigateTo({ url: '/pages/generating/index?phase=extract' })
    } catch (err) {
      const e = err as RequestError
      Taro.showToast({ title: e.message || '提交失败', icon: 'none' })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Page module="in">
      <NavBar title="上传资料" back />
      <View className="bd">
        {/* 上传区 */}
        <View
          className="card stack g6"
          style={{ alignItems: 'center', textAlign: 'center', padding: '28px 20px', borderStyle: 'dashed' }}
        >
          <Mascot variant="read" size={88} />
          <Text className="ct" style={{ fontSize: '16px' }}>把 PDF 发给闯闯，或点选文件</Text>
          <Text className="cs">支持文本型 PDF，单个不超过 10MB、50 页</Text>
          <View className="btn btn-s btn-sm mt8" style={{ width: 'auto', padding: '0 20px' }} onClick={pickFile}>
            选择文件
          </View>
        </View>

        {/* 已选文件 */}
        {file && (
          <View className="card mt12">
            <View className="row g10">
              <View
                className="icon-btn"
                style={{
                  color: fileError ? 'var(--coral)' : 'var(--mint)',
                  background: fileError ? 'var(--coral-soft)' : 'var(--mint-soft)',
                  borderColor: 'transparent',
                }}
              >
                <Icon name="file" size={20} color={fileError ? '#FF5C5C' : '#00B18D'} />
              </View>
              <View className="grow stack g4">
                <Text className="txt-m txt-s">{file.name}</Text>
                <Text className="txt-xs txt-faint">{file.size}{fileError ? '' : ' ｜ 解析成功'}</Text>
              </View>
              <View
                className="icon-btn"
                style={{ width: '32px', height: '32px' }}
                onClick={() => { setFile(null); setFileError('') }}
              >
                <Icon name="x" size={16} color="#2C3A52" />
              </View>
            </View>
            {fileError && (
              <View
                className="row g8 mt12"
                style={{ alignItems: 'flex-start', background: 'var(--coral-soft)', borderRadius: 'var(--r-sm)', padding: '10px 12px' }}
              >
                <Icon name="alert" size={16} color="#FF5C5C" style={{ marginTop: '2px' }} />
                <Text className="txt-xs" style={{ color: '#B32B2B', lineHeight: 1.6 }}>
                  {fileError} 可以换成文本型 PDF，或直接把内容粘贴到下面的输入框。
                </Text>
              </View>
            )}
          </View>
        )}

        {/* 粘贴文字 */}
        <View className="card mt12">
          <View className="row bt">
            <Text className="ct" style={{ fontSize: '15px' }}>或直接粘贴文字</Text>
            <Text className="txt-xs txt-faint">{text.length} / {MAX_CHARS}</Text>
          </View>
          <Textarea
            className="field area mt12"
            style={{ minHeight: '150px' }}
            placeholder="把学习资料粘贴到这里，AI 会提取知识点并出题…"
            value={text}
            maxlength={MAX_CHARS}
            onInput={(e) => setText(e.detail.value)}
          />
        </View>
      </View>
      <View className="act">
        <View className={`btn btn-p ${submitting ? 'dis' : ''}`} onClick={submit}>
          {submitting ? '解析中…' : '解析并生成闯关'}
        </View>
      </View>
    </Page>
  )
}
