/**
 * API配置文件
 * 包含统一API前缀和各模块的接口入口
 */

export const apiConfig = {
  // 后端基础地址
  baseURL: 'http://127.0.0.1:8000',
  // 全局统一版本前缀
  apiPrefix: '/api/v1',
  modules: {
    home: '/home',
    papers: '/papers',
    reader: '/reader',
    analysis: '/analysis',
    compare: '/compare',
    review: '/review',
    chat: '/chat',
    user: '/user',
    favorite: '/favorite',
    history: '/history'
  }
}

export const buildApiUrl = (module, path = '') => {
  const modulePath = apiConfig.modules[module] || ''
  return `${apiConfig.baseURL}${apiConfig.apiPrefix}${modulePath}${path}`
}
