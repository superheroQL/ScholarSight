<template>
  <div class="platform-page paper-page">
    <van-nav-bar title="我的文献" fixed />

    <div class="page-shell">
      <section class="header-bar">
        <div class="title-block">
          <span class="eyebrow">Papers</span>
          <h1>我的文献</h1>
        </div>
        <button class="primary-btn" @click="openFilePicker">上传论文</button>
        <input ref="fileInput" class="file-input" type="file" accept="application/pdf,.pdf" @change="handleFileSelected" />
      </section>

      <section class="toolbar-row">
        <div class="search-wrap">
          <span class="label">搜索论文</span>
          <input v-model="searchQuery" type="text" placeholder="请输入论文名称或作者" />
        </div>
        <button class="search-btn" @click="loadPapers">搜索</button>
      </section>

      <section class="table-card">
        <div v-if="isLoading" class="state-text">正在加载论文...</div>
        <table v-else>
          <thead>
            <tr>
              <th>论文名称</th>
              <th>作者</th>
              <th>上传时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="paper in filteredPapers" :key="paper.id">
              <td>{{ paper.title }}</td>
              <td>{{ paper.author }}</td>
              <td>{{ paper.uploadedAt }}</td>
              <td class="action-cell">
                <router-link class="action-btn" :to="`/read/${paper.id}`">阅读</router-link>
                <router-link class="action-btn analysis-action" :to="`/analysis/${paper.id}`">分析</router-link>
                <button class="action-btn delete-action" @click="deletePaper(paper)">删除</button>
              </td>
            </tr>
            <tr v-if="!filteredPapers.length">
              <td colspan="4" class="empty-cell">暂无文献，点击右上角「上传论文」开始添加</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>

    <tab-bar />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { showDialog, showToast } from 'vant'
import TabBar from '../components/TabBar.vue'
import { buildApiUrl } from '../config/api'
import { useUserStore } from '../store/user'

const fileInput = ref(null)
const isLoading = ref(true)
const isUploading = ref(false)
const searchQuery = ref('')
const userStore = useUserStore()

const papers = ref([])

const filteredPapers = computed(() => papers.value.filter((paper) => {
  const query = searchQuery.value.trim().toLowerCase()
  return !query || `${paper.title} ${paper.author}`.toLowerCase().includes(query)
}))

const normalizePaper = (paper) => ({
  id: paper.id,
  title: paper.title || paper.file_name || '未命名论文',
  author: Array.isArray(paper.authors) ? paper.authors.join(', ') : paper.authors || '作者未知',
  uploadedAt: paper.created_at ? paper.created_at.slice(0, 10) : '刚刚'
})

const loadPapers = async () => {
  isLoading.value = true
  try {
    const response = await fetch(buildApiUrl('papers'), {
      headers: { Authorization: userStore.token }
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const payload = await response.json()
    const source = payload.data || payload.papers || payload
    papers.value = Array.isArray(source) ? source.map(normalizePaper) : []
  } catch {
    papers.value = []
  } finally {
    isLoading.value = false
  }
}

const openFilePicker = () => fileInput.value?.click()

const handleFileSelected = async (event) => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
    showToast('请选择 PDF 文件')
    return
  }

  if (!userStore.token) {
    showToast('请先登录')
    return
  }

  const formData = new FormData()
  formData.append('file', file)
  isUploading.value = true
  try {
    const response = await fetch(buildApiUrl('papers', '/upload'), {
      method: 'POST',
      headers: { Authorization: userStore.token },
      body: formData
    })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) {
      const detail = Array.isArray(payload.detail) ? '请求参数错误' : payload.detail
      throw new Error(detail || '上传失败')
    }
    papers.value.unshift(normalizePaper(payload.data))
    showToast('论文上传成功')
  } catch (error) {
    showToast(error.message || '上传失败，请检查后端服务')
  } finally {
    isUploading.value = false
  }
}

// 删除论文：同时删除 MySQL 记录、向量库分片和 PDF 文件
const deletePaper = async (paper) => {
  let confirmed = false
  try {
    await showDialog({
      title: '删除论文',
      message: `确定删除「${paper.title}」吗？将同时删除数据库记录和向量库中的相关内容，此操作不可恢复。`,
      showCancelButton: true,
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      confirmButtonColor: '#ef4444'
    })
    confirmed = true
  } catch {
    // 用户取消
  }
  if (!confirmed) return

  try {
    const response = await fetch(buildApiUrl('papers', `/${paper.id}`), {
      method: 'DELETE',
      headers: { Authorization: userStore.token }
    })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) {
      const detail = Array.isArray(payload.detail) ? '请求参数错误' : payload.detail
      throw new Error(detail || `HTTP ${response.status}`)
    }
    papers.value = papers.value.filter((p) => p.id !== paper.id)
    showToast('论文已删除')
  } catch (error) {
    showToast(`删除失败：${error.message || '请稍后再试'}`)
  }
}

onMounted(loadPapers)
</script>

<style scoped>
.platform-page { min-height: 100vh; padding-top: 46px; padding-bottom: 62px; background: linear-gradient(180deg, #f4f7ff 0%, #f7f8fa 100%); }
.page-shell { max-width: 1200px; margin: 0 auto; padding: 16px; }
.header-bar, .toolbar-row, .table-card { background: rgba(255,255,255,0.92); border: 1px solid rgba(148,163,184,0.14); border-radius: 18px; box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04); }
.header-bar { display: flex; justify-content: space-between; align-items: center; padding: 20px 18px; }
.title-block h1 { margin: 6px 0 0; font-size: 30px; color: #0f172a; }
.eyebrow { display: inline-block; color: #4f46e5; font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; }
.primary-btn, .search-btn, .action-btn { border: none; cursor: pointer; font: inherit; }
.primary-btn { background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%); color: #fff; padding: 10px 18px; border-radius: 10px; font-weight: 600; }
.file-input { display: none; }
.toolbar-row { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 18px; margin-top: 18px; }
.search-wrap { flex: 1; display: flex; align-items: center; gap: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 10px 14px; }
.label { color: #475569; font-size: 14px; white-space: nowrap; }
.search-wrap input { flex: 1; border: none; outline: none; background: transparent; font-size: 14px; color: #0f172a; }
.search-btn { background: #e2e8f0; color: #0f172a; padding: 12px 18px; border-radius: 10px; font-weight: 600; }
.table-card { margin-top: 18px; overflow: hidden; }
.state-text, .empty-cell { padding: 30px; color: #64748b; text-align: center; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 16px 18px; text-align: left; border-bottom: 1px solid #edf2f7; color: #334155; }
th { background: #f8fafc; color: #64748b; font-size: 12px; letter-spacing: 0.04em; text-transform: uppercase; }
tbody tr:hover { background: #f8fbff; }
.action-cell { white-space: nowrap; }
.action-btn { display: inline-flex; background: #eff6ff; color: #2563eb; padding: 7px 12px; border-radius: 8px; font-weight: 600; text-decoration: none; }
.analysis-action { margin-left: 8px; background: #ecfdf5; color: #047857; }
.delete-action { margin-left: 8px; background: #fee2e2; color: #b91c1c; }
@media (max-width: 760px) { .header-bar, .toolbar-row { flex-direction: column; align-items: stretch; } .search-wrap { width: 100%; } .table-card { overflow-x: auto; } table { min-width: 700px; } }
</style>
