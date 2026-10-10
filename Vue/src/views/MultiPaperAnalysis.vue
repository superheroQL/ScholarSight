<template>
  <div class="platform-page compare-page">
    <van-nav-bar title="多论文分析" fixed />

    <div class="page-shell">
      <section class="hero-card">
        <div>
          <span class="eyebrow">Comparative Intelligence</span>
          <h1>多论文分析</h1>
          <p>选择多篇已上传论文，比较它们的问题、方法、证据与研究边界。</p>
        </div>
        <span class="selected-count">已选 {{ selectedIds.length }} 篇</span>
      </section>

      <section class="panel selection-panel">
        <div class="panel-header">
          <div>
            <h2>请选择论文</h2>
            <p>建议选择 2 至 4 篇论文进行横向分析</p>
          </div>
          <span class="library-status">我的文献库</span>
        </div>

        <div v-if="isLoadingPapers" class="state-text">正在加载已上传论文...</div>
        <div v-else-if="!papers.length" class="state-text">暂无已上传论文，请先到「我的文献」上传。</div>
        <div v-else class="paper-selection-list">
          <label v-for="paper in papers" :key="paper.id" class="paper-checkbox" :class="{ checked: selectedIds.includes(paper.id) }">
            <input v-model="selectedIds" type="checkbox" :value="paper.id" />
            <span class="checkmark">✓</span>
            <span class="paper-info">
              <strong>{{ paper.title }}</strong>
              <small>{{ paper.authors }} · {{ paper.status }}</small>
            </span>
          </label>
        </div>

        <div class="selection-footer">
          <span v-if="selectionError" class="selection-error">{{ selectionError }}</span>
          <span v-else class="selection-hint">至少选择 2 篇论文</span>
          <button class="primary-btn" :disabled="isComparing" @click="startCompare">
            {{ isComparing ? '正在分析...' : '开始对比' }}
          </button>
        </div>
      </section>

      <div v-if="isComparing" class="panel state-text analyzing-text">
        正在对多篇论文进行综合分析（向量检索 + 大模型 12 维分析），约需 1~2 分钟，请勿关闭页面...
      </div>
      <div v-if="compareError" class="panel state-text error-text-panel">{{ compareError }}</div>

      <section v-if="hasCompared" class="panel matrix-panel">
        <div class="panel-header">
          <div>
            <span class="eyebrow">Comparison Matrix</span>
            <h2>论文对比结果</h2>
          </div>
          <span class="result-meta">{{ selectedIds.length }} 篇论文 · {{ comparisonRows.length }} 个维度</span>
        </div>

        <div class="matrix-wrap">
          <table>
            <thead>
              <tr>
                <th>分析维度</th>
                <th v-for="paper in selectedPapers" :key="paper.id">{{ paper.shortTitle }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in comparisonRows" :key="row.dimension">
                <th>{{ row.dimension }}</th>
                <td v-for="paper in selectedPapers" :key="paper.id">{{ row.values[paper.id] }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-if="hasCompared" class="ai-summary panel">
        <div class="summary-heading">
          <div>
            <span class="eyebrow">AI Synthesis</span>
            <h2>AI综合分析</h2>
          </div>
          <span class="summary-badge">关联分析</span>
        </div>
        <p>{{ synthesis.overview }}</p>
        <div class="synthesis-points">
          <div v-for="point in synthesis.points" :key="point.title" class="synthesis-point">
            <strong>{{ point.title }}</strong>
            <span>{{ point.content }}</span>
          </div>
        </div>
      </section>
    </div>

    <tab-bar />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { showToast } from 'vant'
import TabBar from '../components/TabBar.vue'
import { buildApiUrl } from '../config/api'
import { useUserStore } from '../store/user'

const userStore = useUserStore()

const isLoadingPapers = ref(true)
const isComparing = ref(false)
const hasCompared = ref(false)
const selectionError = ref('')
const selectedIds = ref([])
const compareError = ref('')

const papers = ref([])
const selectedPapers = computed(() => papers.value.filter((paper) => selectedIds.value.includes(paper.id)))
const comparisonRows = ref([])
const synthesis = ref({ overview: '', points: [] })

const normalizePapers = (payload) => {
  const source = payload.data || payload.papers || payload
  if (!Array.isArray(source)) return []
  return source.map((paper) => ({
    ...paper,
    id: String(paper.id || paper.paper_id),
    title: paper.title || paper.name || '未命名论文',
    shortTitle: paper.short_title || paper.shortTitle || paper.title || paper.name || '论文',
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
    selectedIds.value = result.slice(0, 3).map((paper) => paper.id)
  } catch {
    papers.value = []
  } finally {
    isLoadingPapers.value = false
  }
}

const startCompare = async () => {
  selectionError.value = ''
  compareError.value = ''
  if (selectedIds.value.length < 2) {
    selectionError.value = '请至少选择 2 篇论文后再开始对比。'
    return
  }
  if (!userStore.token) {
    showToast('请先登录')
    return
  }

  isComparing.value = true
  hasCompared.value = false
  try {
    // 分析耗时较长（多文献检索 + 大模型），同步等待
    const response = await fetch(buildApiUrl('compare'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: userStore.token
      },
      body: JSON.stringify({ paper_ids: selectedIds.value.map(Number) })
    })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) {
      const detail = Array.isArray(payload.detail) ? '请求参数错误' : payload.detail
      throw new Error(detail || `HTTP ${response.status}`)
    }
    const data = payload.data || payload
    comparisonRows.value = data.matrix || []
    synthesis.value = data.synthesis || { overview: '', points: [] }
    hasCompared.value = true
    showToast('对比分析已生成并保存')
  } catch (error) {
    compareError.value = error.message || '分析失败，请稍后再试'
  } finally {
    isComparing.value = false
  }
}

onMounted(loadPapers)
</script>

<style scoped>
.platform-page { min-height: 100vh; padding-top: 46px; padding-bottom: 62px; background: linear-gradient(180deg, #fff7ed 0%, #f8fafc 42%, #f7f8fa 100%); }
.page-shell { max-width: 1240px; margin: 0 auto; padding: 18px 16px; }
.hero-card, .panel { background: rgba(255,255,255,0.94); border: 1px solid rgba(148,163,184,0.15); border-radius: 18px; box-shadow: 0 12px 30px rgba(15, 23, 42, 0.05); }
.hero-card { display: flex; justify-content: space-between; align-items: center; gap: 18px; padding: 24px; }
.eyebrow { display: inline-block; color: #c2410c; font-size: 11px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 8px; }
.hero-card h1 { margin: 0 0 8px; color: #0f172a; font-size: 30px; }
.hero-card p { margin: 0; color: #64748b; line-height: 1.7; }
.selected-count, .library-status, .result-meta, .summary-badge { padding: 7px 10px; border-radius: 999px; color: #9a3412; background: #ffedd5; font-size: 12px; font-weight: 700; white-space: nowrap; }
.panel { margin-top: 18px; padding: 20px; }
.panel-header, .summary-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.panel-header h2, .summary-heading h2 { margin: 0; color: #0f172a; font-size: 20px; }
.panel-header p { margin: 7px 0 0; color: #64748b; font-size: 13px; }
.state-text { padding: 24px 0; color: #64748b; }
.analyzing-text { text-align: center; color: #9a3412; }
.error-text-panel { color: #b91c1c; }
.paper-selection-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 20px; }
.paper-checkbox { display: flex; align-items: center; gap: 12px; padding: 15px; border: 1px solid #e2e8f0; border-radius: 14px; cursor: pointer; transition: 0.2s ease; }
.paper-checkbox:hover, .paper-checkbox.checked { border-color: #fdba74; background: #fff7ed; }
.paper-checkbox input { position: absolute; opacity: 0; pointer-events: none; }
.checkmark { display: grid; place-items: center; flex: 0 0 22px; width: 22px; height: 22px; border: 1px solid #cbd5e1; border-radius: 6px; color: transparent; background: #fff; font-size: 14px; font-weight: 700; }
.paper-checkbox.checked .checkmark { border-color: #ea580c; color: #fff; background: #ea580c; }
.paper-info { display: flex; min-width: 0; flex-direction: column; gap: 6px; }
.paper-info strong { color: #0f172a; line-height: 1.45; }
.paper-info small { color: #64748b; font-size: 12px; }
.selection-footer { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-top: 18px; }
.selection-hint { color: #64748b; font-size: 13px; }
.selection-error { color: #b91c1c; font-size: 13px; }
.primary-btn { border: none; border-radius: 10px; padding: 11px 18px; background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%); color: #fff; cursor: pointer; font: inherit; font-weight: 700; }
.primary-btn:disabled { opacity: 0.55; cursor: not-allowed; }
.matrix-wrap { overflow-x: auto; margin-top: 18px; }
table { width: 100%; min-width: 900px; border-collapse: collapse; }
th, td { padding: 15px 13px; border-bottom: 1px solid #edf2f7; text-align: left; vertical-align: top; color: #475569; line-height: 1.65; }
thead th { color: #9a3412; background: #fff7ed; font-size: 13px; }
tbody th { width: 120px; color: #0f172a; background: #f8fafc; white-space: nowrap; }
.ai-summary { background: linear-gradient(135deg, #fff7ed 0%, #fff 55%); }
.summary-heading { align-items: center; }
.ai-summary > p { margin: 18px 0; color: #334155; line-height: 1.9; font-size: 15px; }
.synthesis-points { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.synthesis-point { padding: 15px; border: 1px solid #fed7aa; border-radius: 12px; background: rgba(255,255,255,0.8); }
.synthesis-point strong, .synthesis-point span { display: block; }
.synthesis-point strong { margin-bottom: 8px; color: #9a3412; }
.synthesis-point span { color: #475569; line-height: 1.75; font-size: 13px; }
@media (max-width: 760px) { .hero-card, .panel-header, .summary-heading, .selection-footer { flex-direction: column; align-items: flex-start; } .paper-selection-list, .synthesis-points { grid-template-columns: 1fr; } .hero-card h1 { font-size: 26px; } .selection-footer .primary-btn { width: 100%; } }
</style>
