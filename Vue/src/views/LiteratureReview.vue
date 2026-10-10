<template>
  <div class="platform-page review-page">
    <van-nav-bar title="文献综述" fixed />

    <div class="page-shell">
      <section class="hero-card">
        <div>
          <span class="eyebrow">Literature Synthesis</span>
          <h1>文献综述</h1>
          <p>从多篇论文中提炼研究脉络、方法差异与未来方向。</p>
        </div>
        <span class="selected-count">已选 {{ selectedIds.length }} 篇</span>
      </section>

      <section class="panel setup-panel">
        <div class="panel-header">
          <div>
            <h2>选择参考文献</h2>
            <p>选择 2 至 6 篇相关论文，AI 将基于论文内容生成结构化综述。</p>
          </div>
          <span class="library-status">我的文献库</span>
        </div>

        <div v-if="isLoadingPapers" class="state-text">正在加载已上传论文...</div>
        <div v-else-if="!papers.length" class="state-text">暂无已上传论文，请先到「我的文献」上传。</div>
        <div v-else class="paper-list">
          <label v-for="paper in papers" :key="paper.id" class="paper-option" :class="{ checked: selectedIds.includes(paper.id) }">
            <input v-model="selectedIds" type="checkbox" :value="paper.id" />
            <span class="checkmark">✓</span>
            <span class="paper-info">
              <strong>{{ paper.title }}</strong>
              <small>{{ paper.authors }} · {{ paper.status }}</small>
            </span>
          </label>
        </div>

        <label class="topic-field">
          <span>综述主题</span>
          <input v-model="topic" type="text" placeholder="例如：Transformer 在目标检测中的应用" />
        </label>

        <div class="setup-footer">
          <span v-if="selectionError" class="error-text">{{ selectionError }}</span>
          <span v-else class="hint-text">{{ selectedIds.length ? '已准备好生成综述' : '请先选择参考文献' }}</span>
          <button class="primary-btn" :disabled="isGenerating" @click="generateReview">
            {{ isGenerating ? '正在生成...' : '生成文献综述' }}
          </button>
        </div>
      </section>

      <section v-if="reviewHistory.length" class="panel history-panel">
        <div class="panel-header">
          <div>
            <h2>历史综述</h2>
            <p>已保存到数据库的综述，点击查看。</p>
          </div>
        </div>
        <div class="history-list">
          <div v-for="r in reviewHistory" :key="r.id" class="history-item" @click="loadReview(r.id)">
            <strong>{{ r.topic }}</strong>
            <small>{{ formatTime(r.created_at) }} · {{ r.paper_ids?.length || 0 }} 篇文献</small>
          </div>
        </div>
      </section>

      <section v-if="reviewResult" class="panel result-panel">
        <div class="result-heading">
          <div>
            <span class="eyebrow">AI Generated Review</span>
            <h2>AI文献综述</h2>
          </div>
          <span class="result-badge">{{ reviewResult.paper_ids?.length || selectedIds.length }} 篇参考文献</span>
        </div>

        <div class="review-content markdown-body" v-html="renderMarkdown(reviewResult.content)"></div>
      </section>
    </div>

    <tab-bar />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { showToast } from 'vant'
import * as marked from 'marked'
import DOMPurify from 'dompurify'
import TabBar from '../components/TabBar.vue'
import { buildApiUrl } from '../config/api'
import { useUserStore } from '../store/user'

const userStore = useUserStore()

const isLoadingPapers = ref(true)
const isGenerating = ref(false)
const selectedIds = ref([])
const topic = ref('')
const selectionError = ref('')
const papers = ref([])
const reviewResult = ref(null)
const reviewHistory = ref([])

const formatTime = (iso) => (iso ? new Date(iso).toLocaleString('zh-CN') : '')

const renderMarkdown = (content) => {
  if (!content) return ''
  return DOMPurify.sanitize(marked.parse(content))
}

const normalizePapers = (payload) => {
  const source = payload.data || payload.papers || payload
  if (!Array.isArray(source)) return []
  return source.map((paper) => ({
    id: String(paper.id || paper.paper_id),
    title: paper.title || paper.name || '未命名论文',
    authors: Array.isArray(paper.authors) ? paper.authors.join(', ') : paper.authors || '作者未知',
    status: paper.status || '已上传'
  })).filter((paper) => paper.id !== 'undefined')
}

const loadPapers = async () => {
  try {
    const response = await fetch(buildApiUrl('papers'), {
      headers: { Authorization: userStore.token }
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const result = normalizePapers(await response.json())
    papers.value = result
    selectedIds.value = result.slice(0, 4).map((paper) => paper.id)
  } catch {
    papers.value = []
  } finally {
    isLoadingPapers.value = false
  }
}

const loadReviews = async () => {
  try {
    const response = await fetch(buildApiUrl('review'), {
      headers: { Authorization: userStore.token }
    })
    if (!response.ok) return
    const payload = await response.json()
    reviewHistory.value = Array.isArray(payload.data) ? payload.data : []
  } catch {
    // 历史加载失败不影响生成
  }
}

const loadReview = async (id) => {
  try {
    const response = await fetch(buildApiUrl('review', `/${id}`), {
      headers: { Authorization: userStore.token }
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const payload = await response.json()
    const data = payload.data || payload
    reviewResult.value = data
    topic.value = data.topic || ''
    selectedIds.value = (data.paper_ids || []).map(String)
  } catch (error) {
    showToast(`加载综述失败：${error.message}`)
  }
}

const generateReview = async () => {
  selectionError.value = ''
  if (selectedIds.value.length < 2) {
    selectionError.value = '请至少选择 2 篇参考文献。'
    return
  }
  if (!topic.value.trim()) {
    selectionError.value = '请填写综述主题。'
    return
  }
  if (!userStore.token) {
    showToast('请先登录')
    return
  }

  isGenerating.value = true
  try {
    // 生成耗时较长（多文献检索 + LLM），同步等待
    const response = await fetch(buildApiUrl('review'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: userStore.token
      },
      body: JSON.stringify({ paper_ids: selectedIds.value.map(Number), topic: topic.value.trim() })
    })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) {
      const detail = Array.isArray(payload.detail) ? '请求参数错误' : payload.detail
      throw new Error(detail || `HTTP ${response.status}`)
    }
    reviewResult.value = payload.data || payload
    loadReviews()
    showToast('文献综述已生成并保存')
  } catch (error) {
    showToast(`生成失败：${error.message || '请稍后再试'}`)
  } finally {
    isGenerating.value = false
  }
}

onMounted(() => {
  loadPapers()
  loadReviews()
})
</script>

<style scoped>
.platform-page { min-height: 100vh; padding-top: 46px; padding-bottom: 62px; background: linear-gradient(180deg, #eefcf8 0%, #f8fafc 45%, #f7f8fa 100%); }
.page-shell { max-width: 1120px; margin: 0 auto; padding: 18px 16px; }
.hero-card, .panel { background: rgba(255,255,255,0.94); border: 1px solid rgba(148,163,184,0.14); border-radius: 18px; box-shadow: 0 12px 30px rgba(15, 23, 42, 0.05); }
.hero-card { display: flex; justify-content: space-between; align-items: center; gap: 18px; padding: 24px; }
.eyebrow { display: inline-block; color: #0f766e; font-size: 11px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 8px; }
.hero-card h1 { margin: 0 0 8px; color: #0f172a; font-size: 30px; }
.hero-card p { margin: 0; color: #64748b; line-height: 1.7; }
.selected-count, .library-status, .result-badge { padding: 7px 10px; border-radius: 999px; color: #0f766e; background: #ccfbf1; font-size: 12px; font-weight: 700; white-space: nowrap; }
.panel { margin-top: 18px; padding: 20px; }
.panel-header, .result-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.panel-header h2, .result-heading h2 { margin: 0; color: #0f172a; font-size: 20px; }
.panel-header p { margin: 7px 0 0; color: #64748b; font-size: 13px; }
.state-text { padding: 24px 0; color: #64748b; }
.paper-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 20px; }
.paper-option { display: flex; align-items: center; gap: 12px; padding: 15px; border: 1px solid #e2e8f0; border-radius: 14px; cursor: pointer; transition: 0.2s ease; }
.paper-option:hover, .paper-option.checked { border-color: #5eead4; background: #f0fdfa; }
.paper-option input { position: absolute; opacity: 0; pointer-events: none; }
.checkmark { display: grid; place-items: center; flex: 0 0 22px; width: 22px; height: 22px; border: 1px solid #cbd5e1; border-radius: 6px; color: transparent; background: #fff; font-size: 14px; font-weight: 700; }
.paper-option.checked .checkmark { border-color: #0f766e; color: #fff; background: #0f766e; }
.paper-info { display: flex; min-width: 0; flex-direction: column; gap: 6px; }
.paper-info strong { color: #0f172a; line-height: 1.45; }
.paper-info small { color: #64748b; font-size: 12px; }
.topic-field { display: flex; flex-direction: column; gap: 8px; margin-top: 20px; color: #334155; font-size: 14px; font-weight: 700; }
.topic-field input { padding: 13px 14px; border: 1px solid #dbe5e1; border-radius: 10px; outline: none; color: #0f172a; background: #f8fafc; font: inherit; font-weight: 400; }
.topic-field input:focus { border-color: #2dd4bf; box-shadow: 0 0 0 3px rgba(45, 212, 191, 0.12); }
.setup-footer { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-top: 18px; }
.hint-text { color: #64748b; font-size: 13px; }
.error-text { color: #b91c1c; font-size: 13px; }
.primary-btn { border: none; border-radius: 10px; padding: 11px 18px; background: linear-gradient(135deg, #0f766e 0%, #115e59 100%); color: #fff; cursor: pointer; font: inherit; font-weight: 700; }
.primary-btn:disabled { opacity: 0.55; cursor: not-allowed; }
.result-panel { background: linear-gradient(135deg, #f0fdfa 0%, #fff 48%); }
.review-content { display: flex; flex-direction: column; gap: 14px; margin-top: 22px; }
.review-section { display: grid; grid-template-columns: 44px 1fr; gap: 14px; padding: 18px; border: 1px solid #ccfbf1; border-radius: 14px; background: rgba(255,255,255,0.84); }
.section-number { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 10px; color: #0f766e; background: #ccfbf1; font-size: 12px; font-weight: 700; }
.review-section h3 { margin: 0 0 8px; color: #0f172a; font-size: 17px; }
.review-section p { margin: 0; color: #475569; line-height: 1.9; }

/* 历史综述 */
.history-list { display: flex; flex-direction: column; gap: 10px; margin-top: 16px; }
.history-item { padding: 13px 16px; border: 1px solid #e2e8f0; border-radius: 12px; cursor: pointer; background: #f8fafc; }
.history-item:hover { border-color: #5eead4; background: #f0fdfa; }
.history-item strong { display: block; color: #0f172a; margin-bottom: 5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.history-item small { color: #64748b; font-size: 12px; }

/* 综述 Markdown 渲染 */
.markdown-body { line-height: 1.9; color: #334155; }
.markdown-body :deep(h1) { font-size: 22px; color: #0f172a; margin: 6px 0 14px; }
.markdown-body :deep(h2) { font-size: 18px; color: #0f172a; margin: 22px 0 10px; padding-bottom: 8px; border-bottom: 1px solid #e2e8f0; }
.markdown-body :deep(h3) { font-size: 16px; color: #0f172a; margin: 16px 0 8px; }
.markdown-body :deep(p) { margin: 8px 0; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { padding-left: 22px; margin: 8px 0; }
.markdown-body :deep(li) { margin: 4px 0; }
.markdown-body :deep(table) { border-collapse: collapse; margin: 12px 0; width: 100%; }
.markdown-body :deep(th), .markdown-body :deep(td) { border: 1px solid #e2e8f0; padding: 8px 12px; text-align: left; }
.markdown-body :deep(th) { background: #f8fafc; color: #0f172a; }

@media (max-width: 760px) { .hero-card, .panel-header, .result-heading, .setup-footer { flex-direction: column; align-items: flex-start; } .paper-list { grid-template-columns: 1fr; } .setup-footer .primary-btn { width: 100%; } .hero-card h1 { font-size: 26px; } }
</style>
