/** 前端运行配置 */

// H5 开发环境经 devServer 代理到后端；小程序端需配置合法域名
export const API_BASE = process.env.TARO_APP_API_BASE || ''

// 置 true 时全程使用本地 Mock 数据（无后端演示用）
export const USE_MOCK = process.env.TARO_APP_USE_MOCK === '1'

export const APP_VERSION = 'v0.1'
