import type { UserConfigExport } from '@tarojs/cli'

export default {
  mini: {},
  h5: {
    // H5 生产构建如需相对路径部署可改为 './'
    publicPath: '/',
  },
} satisfies UserConfigExport<'webpack5'>
