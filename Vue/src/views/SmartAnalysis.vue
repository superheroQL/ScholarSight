<template>
  <div class="platform-page analysis-page">
    <van-nav-bar :title="`论文智能分析 · #${paperId}`" fixed />

    <div class="page-shell">
      <div v-if="isLoading" class="state-panel">正在加载论文分析...</div>

      <div v-else-if="isAnalyzing" class="state-panel analyzing">
        <span class="spinner"></span>
        <strong>正在生成论文分析</strong>
        <span>基于向量库检索论文片段，按 8 个任务结构化抽取，约需 1~3 分钟，请勿关闭页面...</span>
      </div>

      <div v-else-if="!hasAnalysis" class="state-panel empty-analysis">
        <strong>该论文还没有分析结果</strong>
        <span>点击下方按钮，基于 RAG + LLM 对论文进行结构化智能分析。</span>
        <div class="state-actions">
          <button class="primary-btn" @click="openPaperPicker">选择论文</button>
          <button class="primary-btn" @click="runAnalysis">开始智能分析</button>
        </div>
      </div>

      <div v-else class="analysis-content">
        <section class="hero-card">
          <div>
            <span class="eyebrow">Paper Intelligence · #{{ paperId }}</span>
            <h1>论文智能分析</h1>
            <h2>{{ paperTitle }}</h2>
            <p v-if="analysisMeta.model_name">模型：{{ analysisMeta.model_name }} · 更新时间：{{ formatTime(analysisMeta.updated_at) }}</p>
          </div>
          <div class="hero-actions">
            <button class="secondary-btn" @click="openPaperPicker">选择论文</button>
            <button class="primary-btn" @click="runAnalysis">重新分析</button>
          </div>
        </section>

        <!-- 1. 研究问题 -->
        <section class="analysis-grid">
          <article class="analysis-card card-01">
            <div class="card-heading"><span class="card-index">01</span><h3>研究问题</h3></div>
            <div v-if="analysis.research_question" class="kv-block">
              <div class="kv-item"><label>研究背景</label><p>{{ analysis.research_question.background || '—' }}</p></div>
              <div class="kv-item"><label>现存问题</label><p>{{ analysis.research_question.problem || '—' }}</p></div>
              <div class="kv-item"><label>研究目标</label><p>{{ analysis.research_question.objective || '—' }}</p></div>
            </div>
            <p v-else class="card-empty">暂无内容</p>
          </article>

          <!-- 2. 核心方法 -->
          <article class="analysis-card card-02">
            <div class="card-heading"><span class="card-index">02</span><h3>核心方法</h3></div>
            <div v-if="analysis.core_method" class="kv-block">
              <div class="kv-item"><label>方法名称</label><p>{{ analysis.core_method.name || '—' }}</p></div>
              <div class="kv-item"><label>整体框架</label><p>{{ analysis.core_method.overview || '—' }}</p></div>
              <div v-if="analysis.core_method.components?.length" class="kv-item">
                <label>核心模块</label>
                <ul class="plain-list">
                  <li v-for="(c, i) in analysis.core_method.components" :key="i">
                    <strong>{{ c.name }}</strong><span v-if="c.description">：{{ c.description }}</span>
                  </li>
                </ul>
              </div>
              <div class="kv-item"><label>技术创新</label><p>{{ analysis.core_method.innovation || '—' }}</p></div>
            </div>
            <p v-else class="card-empty">暂无内容</p>
          </article>

          <!-- 3. 数据集 -->
          <article class="analysis-card card-03">
            <div class="card-heading"><span class="card-index">03</span><h3>数据集</h3></div>
            <div v-if="analysis.datasets?.length" class="dataset-list">
              <div v-for="(d, i) in analysis.datasets" :key="i" class="dataset-item">
                <div class="dataset-name">{{ d.name || '未命名数据集' }}</div>
                <div class="dataset-meta">
                  <span v-if="d.source">来源：{{ d.source }}</span>
                  <span v-if="d.scale">规模：{{ d.scale }}</span>
                  <span v-if="d.split">划分：{{ d.split }}</span>
                  <span v-if="d.task">任务：{{ d.task }}</span>
                </div>
              </div>
            </div>
            <p v-else class="card-empty">暂无内容</p>
          </article>

          <!-- 4. 实验结果 -->
          <article class="analysis-card card-04">
            <div class="card-heading"><span class="card-index">04</span><h3>实验结果</h3></div>
            <div v-if="analysis.experimental_results" class="kv-block">
              <div v-if="analysis.experimental_results.tasks?.length">
                <div v-for="(t, i) in analysis.experimental_results.tasks" :key="i" class="result-row">
                  <strong>{{ t.task || `任务 ${i + 1}` }}</strong>
                  <span v-if="t.metrics">指标：{{ t.metrics }}</span>
                  <span v-if="t.comparison">对比：{{ t.comparison }}</span>
                  <span v-if="t.result">结果：{{ t.result }}</span>
                </div>
              </div>
              <div v-if="analysis.experimental_results.main_findings" class="kv-item">
                <label>主要发现</label><p>{{ analysis.experimental_results.main_findings }}</p>
              </div>
            </div>
            <p v-else class="card-empty">暂无内容</p>
          </article>

          <!-- 5. 核心结论 -->
          <article class="analysis-card card-05">
            <div class="card-heading"><span class="card-index">05</span><h3>核心结论</h3></div>
            <div v-if="analysis.core_conclusion" class="kv-block">
              <div class="kv-item"><label>总结</label><p>{{ analysis.core_conclusion.summary || '—' }}</p></div>
              <div v-if="analysis.core_conclusion.key_points?.length" class="kv-item">
                <label>关键要点</label>
                <ul class="plain-list"><li v-for="(p, i) in analysis.core_conclusion.key_points" :key="i">{{ p }}</li></ul>
              </div>
            </div>
            <p v-else class="card-empty">暂无内容</p>
          </article>

          <!-- 6. 局限与启示 -->
          <article class="analysis-card card-06">
            <div class="card-heading"><span class="card-index">06</span><h3>局限与启示</h3></div>
            <div v-if="analysis.limitations_and_insights" class="kv-block">
              <div v-if="analysis.limitations_and_insights.limitations?.length" class="kv-item">
                <label>局限</label>
                <ul class="plain-list"><li v-for="(l, i) in analysis.limitations_and_insights.limitations" :key="i">{{ l }}</li></ul>
              </div>
              <div v-if="analysis.limitations_and_insights.research_insights?.length" class="kv-item">
                <label>研究启示</label>
                <ul class="plain-list"><li v-for="(r, i) in analysis.limitations_and_insights.research_insights" :key="i">{{ r }}</li></ul>
              </div>
            </div>
            <p v-else class="card-empty">暂无内容</p>
          </article>
        </section>

        <!-- 7. 证据与研究启示 -->
        <section class="support-panel evidence-panel">
          <div class="section-heading">
            <div>
              <span class="eyebrow">Evidence Map</span>
              <h3>证据与研究启示</h3>
            </div>
          </div>
          <div v-if="analysis.evidence_and_implications?.length" class="evidence-list">
            <div v-for="(e, i) in analysis.evidence_and_implications" :key="i" class="evidence-item">
              <strong class="evidence-claim">{{ e.claim }}</strong>
              <blockquote v-if="e.evidence" class="evidence-quote">「{{ e.evidence }}」</blockquote>
              <div class="evidence-source">
                <span v-if="e.source?.chunk_id">chunk: {{ e.source.chunk_id }}</span>
                <span v-if="e.source?.section">章节: {{ e.source.section }}</span>
                <span v-if="e.source?.page">页码: {{ e.source.page }}</span>
              </div>
              <p v-if="e.implication" class="evidence-implication">启示：{{ e.implication }}</p>
            </div>
          </div>
          <p v-else class="card-empty">暂无内容</p>
        </section>

        <!-- 8. 值得继续追问 -->
        <section class="support-panel">
          <div class="section-heading">
            <div>
              <span class="eyebrow">Next Questions</span>
              <h3>值得继续追问</h3>
            </div>
          </div>
          <div v-if="analysis.further_questions?.length" class="question-list">
            <div v-for="(q, i) in analysis.further_questions" :key="i" class="question-item">
              <strong>Q{{ i + 1 }}. {{ q.question }}</strong>
              <p v-if="q.reason">{{ q.reason }}</p>
            </div>
          </div>
          <p v-else class="card-empty">暂无内容</p>
        </section>
      </div>
    </div>

    <!-- 论文选择弹窗 -->
    <div v-if="isPaperPickerOpen" class="picker-overlay" @click.self="isPaperPickerOpen = false">
      <section class="paper-picker" role="dialog" aria-modal="true">
        <div class="picker-header">
          <div>
            <span class="eyebrow">Paper Library</span>
            <h2>选择已上传论文</h2>
          </div>
          <button class="close-btn" aria-label="关闭" @click="isPaperPickerOpen = false">×</button>
        </div>
        <div v-if="isLoadingPapers" class="picker-state">正在加载已上传论文...</div>
        <div v-else-if="!uploadedPapers.length" class="picker-state">暂无已上传论文，请先到「我的文献」上传</div>
        <div v-else class="paper-options">
          <button
            v-for="paper in uploadedPapers"
            :key="paper.id"
            class="paper-option"
            :class="{ selected: paper.id === paperId }"
            @click="selectPaper(paper.id)"
          >
            <span class="paper-option-icon">{{ paper.id === paperId ? '✓' : '文' }}</span>
            <span class="paper-option-content">
              <strong>{{ paper.title }}</strong>
              <small>{{ paper.authors }}</small>
            </span>
            <span class="paper-option-arrow">›</span>
          </button>
        </div>
      </section>
    </div>

    <tab-bar />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { showToast } from 'vant'
import { useRoute, useRouter } from 'vue-router'
import TabBar from '../components/TabBar.vue'
import { buildApiUrl } from '../config/api'
import { useUserStore } from '../store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const paperId = computed(() => String(route.params.id || '1'))
const isLoading = ref(true)
const isAnalyzing = ref(false)
const isPaperPickerOpen = ref(false)
const isLoadingPapers = ref(false)
const hasAnalysis = ref(false)
const paperTitle = ref('')
const analysisMeta = ref({ model_name: '', updated_at: '' })

// 8 个分析结果字段
const analysis = ref({
  research_question: null,
  core_method: null,
  datasets: null,
  experimental_results: null,
  core_conclusion: null,
  limitations_and_insights: null,
  evidence_and_implications: null,
  further_questions: null
})

const uploadedPapers = ref([])

const formatTime = (iso) => (iso ? new Date(iso).toLocaleString('zh-CN') : '')

const loadUploadedPapers = async () => {
  isLoadingPapers.value = true
  try {
    const response = await fetch(buildApiUrl('papers'), {
      headers: { Authorization: userStore.token }
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const payload = await response.json()
    const source = payload.data || payload.papers || payload
    uploadedPapers.value = (Array.isArray(source) ? source : []).map((paper) => ({
      id: String(paper.id || paper.paper_id),
      title: paper.title || '未命名论文',
      authors: paper.authors || '作者未知'
    })).filter((paper) => paper.id !== 'undefined')
  } catch {
    uploadedPapers.value = []
  } finally {
    isLoadingPapers.value = false
  }
}

const openPaperPicker = () => {
  isPaperPickerOpen.value = true
  loadUploadedPapers()
}

const selectPaper = (id) => {
  isPaperPickerOpen.value = false
  if (String(id) !== paperId.value) router.push(`/analysis/${id}`)
}

const applyData = (payload) => {
  const data = payload.data || payload
  paperTitle.value = data.paper_title || analysisTitle(data) || ''
  analysisMeta.value = {
    model_name: data.model_name || '',
    updated_at: data.updated_at || ''
  }
  analysis.value = {
    research_question: data.research_question || null,
    core_method: data.core_method || null,
    datasets: data.datasets || null,
    experimental_results: data.experimental_results || null,
    core_conclusion: data.core_conclusion || null,
    limitations_and_insights: data.limitations_and_insights || null,
    evidence_and_implications: data.evidence_and_implications || null,
    further_questions: data.further_questions || null
  }
  hasAnalysis.value = true
}

// 从分析结果里猜一个论文标题（后端没有返回标题时用）
const analysisTitle = (data) => {
  const methodName = data?.core_method?.name
  return methodName ? `${methodName} 论文分析` : `论文 #${paperId.value}`
}

const loadAnalysis = async () => {
  isLoading.value = true
  hasAnalysis.value = false
  try {
    const response = await fetch(buildApiUrl('analysis', `/${encodeURIComponent(paperId.value)}`), {
      headers: { Authorization: userStore.token }
    })
    if (response.status === 404) {
      hasAnalysis.value = false
      loadPaperTitle()
      return
    }
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    applyData(await response.json())
  } catch (error) {
    hasAnalysis.value = false
    showToast(`加载分析失败：${error.message}`)
  } finally {
    isLoading.value = false
  }
}

// 没有分析结果时，拉论文标题用于展示
const loadPaperTitle = async () => {
  try {
    const response = await fetch(buildApiUrl('papers', `/${encodeURIComponent(paperId.value)}`), {
      headers: { Authorization: userStore.token }
    })
    if (!response.ok) return
    const payload = await response.json()
    paperTitle.value = payload.data?.title || ''
  } catch { /* 忽略 */ }
}

const runAnalysis = async () => {
  if (isAnalyzing.value) return
  if (!userStore.token) {
    showToast('请先登录')
    return
  }
  isAnalyzing.value = true
  hasAnalysis.value = false
  try {
    // 分析耗时较长（多次检索 + 8 个任务的模型调用），同步等待
    const response = await fetch(buildApiUrl('analysis', `/${encodeURIComponent(paperId.value)}`), {
      method: 'POST',
      headers: { Authorization: userStore.token }
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    applyData(await response.json())
    showToast('分析完成')
  } catch (error) {
    showToast(`分析失败：${error.message || '请稍后再试'}`)
  } finally {
    isAnalyzing.value = false
  }
}

watch(() => route.params.id, loadAnalysis)
onMounted(loadAnalysis)
</script>

<style scoped>
.platform-page { min-height: 100vh; padding-top: 46px; padding-bottom: 62px; background: linear-gradient(180deg, #f4f7ff 0%, #f7f8fa 100%); }
.page-shell { max-width: 1180px; margin: 0 auto; padding: 18px 16px; }
.state-panel, .hero-card, .analysis-card, .support-panel { background: rgba(255,255,255,0.94); border: 1px solid rgba(148,163,184,0.14); border-radius: 18px; box-shadow: 0 12px 30px rgba(15, 23, 42, 0.05); }
.state-panel { padding: 28px 20px; color: #475569; display: flex; flex-direction: column; align-items: flex-start; gap: 12px; }
.state-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.state-panel strong { color: #0f172a; font-size: 18px; }
.analyzing { align-items: center; text-align: center; padding: 48px 20px; }
.spinner { width: 34px; height: 34px; border: 3px solid #e2e8f0; border-top-color: #4f46e5; border-radius: 50%; animation: spin 0.9s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.hero-card { padding: 24px; display: flex; justify-content: space-between; align-items: center; gap: 18px; }
.eyebrow { display: inline-block; color: #4f46e5; font-size: 11px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 8px; }
.hero-card h1 { margin: 0 0 8px; color: #0f172a; font-size: 30px; }
.hero-card h2 { margin: 0 0 8px; color: #334155; font-size: 18px; font-weight: 600; }
.hero-card p { margin: 0; color: #64748b; font-size: 13px; }
.hero-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.primary-btn, .secondary-btn { border: none; border-radius: 10px; padding: 11px 16px; cursor: pointer; font: inherit; font-weight: 600; white-space: nowrap; }
.primary-btn { background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%); color: #fff; }
.secondary-btn { background: #eef2ff; color: #4f46e5; border: 1px solid #c7d2fe; }
.analysis-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-top: 18px; }
.analysis-card { padding: 20px; min-height: 180px; border-top: 3px solid #4f46e5; }
.card-heading { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.card-index { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 10px; background: #eef2ff; color: #4f46e5; font-size: 12px; font-weight: 700; }
.card-heading h3 { margin: 0; color: #0f172a; font-size: 19px; }
.card-empty { margin: 0; color: #94a3b8; }
.kv-block { display: flex; flex-direction: column; gap: 12px; }
.kv-item label { display: block; margin-bottom: 4px; color: #64748b; font-size: 12px; font-weight: 600; }
.kv-item p { margin: 0; color: #334155; line-height: 1.85; }
.plain-list { margin: 0; padding-left: 18px; color: #334155; line-height: 1.85; }
.plain-list li + li { margin-top: 5px; }
.dataset-list { display: flex; flex-direction: column; gap: 10px; }
.dataset-item { padding: 12px 14px; border: 1px solid #e2e8f0; border-radius: 12px; background: #f8fafc; }
.dataset-name { color: #0f172a; font-weight: 700; margin-bottom: 6px; }
.dataset-meta { display: flex; flex-wrap: wrap; gap: 6px 14px; color: #64748b; font-size: 12px; }
.result-row { padding: 10px 12px; border: 1px solid #e2e8f0; border-radius: 12px; background: #f8fafc; display: flex; flex-direction: column; gap: 5px; margin-bottom: 10px; color: #334155; font-size: 13px; }
.result-row strong { color: #0f172a; }
.support-panel { padding: 20px; margin-top: 18px; }
.section-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 18px; }
.section-heading h3 { margin: 0; color: #0f172a; font-size: 18px; }
.evidence-list { display: flex; flex-direction: column; gap: 16px; }
.evidence-item { padding: 14px 16px; border: 1px solid #e2e8f0; border-radius: 14px; background: #f8fafc; }
.evidence-claim { display: block; color: #0f172a; margin-bottom: 8px; }
.evidence-quote { margin: 0 0 8px; padding: 8px 12px; border-left: 3px solid #4f46e5; color: #475569; background: #eef2ff; border-radius: 0 8px 8px 0; line-height: 1.7; }
.evidence-source { display: flex; flex-wrap: wrap; gap: 6px 14px; color: #94a3b8; font-size: 11px; margin-bottom: 6px; }
.evidence-implication { margin: 0; color: #334155; font-size: 13px; line-height: 1.8; }
.question-list { display: flex; flex-direction: column; gap: 12px; }
.question-item { padding: 12px 14px; border: 1px solid #e2e8f0; border-radius: 12px; background: #f8fafc; }
.question-item strong { color: #0f172a; }
.question-item p { margin: 6px 0 0; color: #64748b; font-size: 13px; line-height: 1.8; }
.picker-overlay { position: fixed; z-index: 20; inset: 0; display: grid; place-items: center; padding: 20px; background: rgba(15, 23, 42, 0.42); }
.paper-picker { width: min(560px, 100%); max-height: min(680px, 90vh); overflow-y: auto; padding: 22px; border-radius: 20px; background: #fff; box-shadow: 0 24px 70px rgba(15, 23, 42, 0.22); }
.picker-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; padding-bottom: 16px; border-bottom: 1px solid #e2e8f0; }
.picker-header h2 { margin: 0; color: #0f172a; font-size: 22px; }
.close-btn { border: none; background: #f1f5f9; color: #475569; width: 34px; height: 34px; border-radius: 50%; cursor: pointer; font-size: 24px; line-height: 1; }
.picker-state { padding: 28px 4px; color: #64748b; text-align: center; }
.paper-options { display: flex; flex-direction: column; gap: 10px; padding-top: 16px; }
.paper-option { display: flex; align-items: center; gap: 12px; width: 100%; padding: 14px; text-align: left; border: 1px solid #e2e8f0; border-radius: 12px; background: #fff; color: #0f172a; cursor: pointer; }
.paper-option:hover, .paper-option.selected { border-color: #a5b4fc; background: #eef2ff; }
.paper-option-icon { display: grid; place-items: center; flex: 0 0 34px; width: 34px; height: 34px; border-radius: 10px; background: #e0e7ff; color: #4f46e5; font-size: 13px; font-weight: 700; }
.paper-option-content { display: flex; min-width: 0; flex: 1; flex-direction: column; gap: 5px; }
.paper-option-content strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }
.paper-option-content small { color: #64748b; font-size: 12px; }
.paper-option-arrow { color: #4f46e5; font-size: 24px; }
@media (max-width: 760px) {
  .hero-card, .section-heading { flex-direction: column; align-items: flex-start; }
  .analysis-grid { grid-template-columns: 1fr; }
  .hero-card h1 { font-size: 26px; }
  .hero-actions { width: 100%; }
  .hero-actions button { flex: 1; }
}
</style>
