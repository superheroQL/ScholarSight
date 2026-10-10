<template>
  <div class="platform-page reading-page">
    <van-nav-bar :title="`在线阅读 · ${paper.title || '#' + paperId}`" fixed />

    <div class="page-shell">
      <div v-if="isLoadingPaper" class="state-panel">正在加载论文...</div>
      <div v-else-if="paperError" class="state-panel error-state">
        <strong>未选择论文</strong>
        <span>{{ paperError }}</span>
        <div class="state-actions">
          <button class="primary-btn" @click="openPaperPicker">选择论文</button>
          <button class="primary-btn" @click="loadPaper">重新加载</button>
        </div>
      </div>

      <div v-else :class="['reader-layout', { 'no-toc': !tocVisible, 'no-assistant': !assistantVisible }]">
        <aside v-if="tocVisible" class="panel toc-panel">
          <div class="toc-header">
            <div class="panel-title">目录</div>
            <button class="toc-close" @click="tocVisible = false" aria-label="关闭目录">✕</button>
          </div>
          <ul class="toc-list">
            <li
              v-for="section in sections"
              :key="section.id"
              :class="{ active: activeSection === section.id }"
              @click="scrollToSection(section.id)"
            >
              {{ section.title }}
            </li>
          </ul>
          <div v-if="!sections.length" class="toc-empty">暂无可识别章节</div>
        </aside>

        <main class="panel pdf-panel">
          <div class="paper-header">
            <div class="paper-badge">Paper · #{{ paperId }}</div>
            <h1>{{ paper.title }}</h1>
            <div class="meta-row">
              <span>{{ paper.authors || '作者未知' }}</span>
              <span v-if="paper.journal">{{ paper.journal }}</span>
              <span v-if="paper.publish_year">{{ paper.publish_year }}</span>
              <span v-if="paper.doi">DOI: {{ paper.doi }}</span>
            </div>
          </div>

          <div class="pdf-toolbar">
            <button class="ghost-btn" @click="tocVisible = !tocVisible">目录</button>
            <button class="ghost-btn" @click="assistantVisible = !assistantVisible">AI 助手</button>
            <button class="ghost-btn" @click="openPaperPicker">选择论文</button>
            <a v-if="pdfUrl" class="ghost-btn" :href="pdfUrl" target="_blank">在新窗口打开 PDF</a>
            <button class="primary-btn" @click="scrollToSection(activeSection)">继续阅读</button>
          </div>

          <div v-if="pdfUrl" class="pdf-viewer">
            <iframe :src="pdfUrl" title="论文 PDF 阅读器" loading="lazy"></iframe>
          </div>
          <div v-else class="pdf-empty">未找到 PDF 原文件，以下为提取的论文文本。</div>

          <div v-if="paper.abstract" class="abstract-block">
            <h2>摘要</h2>
            <p>{{ paper.abstract }}</p>
          </div>

          <div class="section-preview">
            <article
              v-for="section in sections"
              :id="section.id"
              :key="section.id"
              class="page-block"
            >
              <h2>{{ section.title }}</h2>
              <pre class="section-text">{{ section.content }}</pre>
            </article>
            <div v-if="!sections.length" class="pdf-empty">论文暂无可显示的文本内容。</div>
          </div>
        </main>

        <aside v-if="assistantVisible" class="panel assistant-panel">
          <div class="assistant-head">
            <div class="assistant-header">AI论文助手</div>
            <button class="toc-close" @click="assistantVisible = false" aria-label="关闭AI助手">✕</button>
          </div>
          <small class="assistant-hint">基于当前论文内容回答（只检索本篇文献）</small>

          <div ref="messagesContainer" class="assistant-body">
            <div v-for="(message, index) in messages" :key="index" :class="['qa-card', `${message.role}-card`]">
              <span class="qa-label">{{ message.role === 'user' ? '问题' : 'AI' }}</span>
              <p>{{ message.content || '正在思考...' }}</p>
            </div>
          </div>

          <form class="assistant-input" @submit.prevent="sendQuestion">
            <input
              v-model="question"
              type="text"
              placeholder="输入问题……"
              :disabled="isStreaming"
            />
            <button type="submit" :disabled="isStreaming || !question.trim()" aria-label="发送问题">➤</button>
          </form>
        </aside>
      </div>
    </div>

    <!-- 论文选择弹窗 -->
    <div v-if="showPicker" class="picker-overlay" @click.self="showPicker = false">
      <section class="paper-picker" role="dialog" aria-modal="true">
        <div class="picker-header">
          <div>
            <span class="eyebrow">Paper Library</span>
            <h2>选择论文</h2>
          </div>
          <button class="close-btn" aria-label="关闭" @click="showPicker = false">×</button>
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
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TabBar from '../components/TabBar.vue'
import { buildApiUrl } from '../config/api'
import { useUserStore } from '../store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const paperId = computed(() => String(route.params.id || '1'))
const messagesContainer = ref(null)
const question = ref('')
const isLoadingPaper = ref(true)
const isStreaming = ref(false)
const paperError = ref('')
const activeSection = ref('')
const abortController = ref(null)
const pdfUrl = ref('')
const tocVisible = ref(true)
const assistantVisible = ref(true)
const showPicker = ref(false)
const isLoadingPapers = ref(false)
const uploadedPapers = ref([])

// 选择论文弹窗
const openPaperPicker = () => {
  showPicker.value = true
  loadUploadedPapers()
}

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

const selectPaper = (id) => {
  showPicker.value = false
  if (String(id) !== paperId.value) router.push(`/read/${id}`)
}

const paper = ref({
  title: '',
  authors: '',
  journal: '',
  publish_year: '',
  doi: '',
  abstract: '',
  full_text: ''
})

// 把全文按 Markdown 标题（#/##/###）拆成章节；无标题则整体作为一节
const parseSections = (fullText) => {
  if (!fullText) return []
  const sections = []
  let current = null
  for (const line of fullText.split('\n')) {
    const match = line.match(/^(#{1,3})\s+(.+)$/)
    if (match) {
      current = { id: `sec-${sections.length}`, title: match[2].trim(), content: '' }
      sections.push(current)
    } else if (current) {
      current.content += line + '\n'
    } else {
      current = { id: 'sec-0', title: '开头', content: line + '\n' }
      sections.push(current)
    }
  }
  return sections.filter((s) => s.content.trim())
}

const sections = computed(() => parseSections(paper.value.full_text))

const revokePdfUrl = () => {
  if (pdfUrl.value) {
    URL.revokeObjectURL(pdfUrl.value)
    pdfUrl.value = ''
  }
}

const loadPaper = async () => {
  isLoadingPaper.value = true
  paperError.value = ''
  try {
    const response = await fetch(buildApiUrl('papers', `/${encodeURIComponent(paperId.value)}`), {
      headers: { Authorization: userStore.token }
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const payload = await response.json()
    const data = payload.data || payload
    paper.value = {
      title: data.title || '未命名论文',
      authors: data.authors || '',
      journal: data.journal || '',
      publish_year: data.publish_year || '',
      doi: data.doi || '',
      abstract: data.abstract || '',
      full_text: data.full_text || ''
    }
    activeSection.value = sections.value[0]?.id || ''
    loadPdf()
  } catch (error) {
    paperError.value = error.message === 'HTTP 404' ? '请点击下方选择论文' : (error.message || '请检查网络与登录状态')
  } finally {
    isLoadingPaper.value = false
  }
}

// 以 blob 方式加载 PDF（iframe 无法带 Authorization 头）
const loadPdf = async () => {
  revokePdfUrl()
  try {
    const response = await fetch(buildApiUrl('papers', `/${encodeURIComponent(paperId.value)}/file`), {
      headers: { Authorization: userStore.token }
    })
    if (!response.ok) return
    const blob = await response.blob()
    pdfUrl.value = URL.createObjectURL(blob)
  } catch {
    // 无 PDF 时退化为纯文本阅读
  }
}

const scrollToSection = (sectionId) => {
  if (!sectionId) return
  activeSection.value = sectionId
  document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const scrollAssistantToBottom = () => {
  if (messagesContainer.value) messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
}

const messages = ref([
  { role: 'assistant', content: '你好，我可以基于当前论文回答问题。' }
])

const parseSseBlock = (block) => {
  const data = block
    .split('\n')
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trim())
    .join('')
  if (!data || data === '[DONE]') return ''
  try {
    const json = JSON.parse(data)
    return json.choices?.[0]?.delta?.content || json.output?.text || json.content || ''
  } catch {
    return data
  }
}

const sendQuestion = async () => {
  const currentQuestion = question.value.trim()
  if (!currentQuestion || isStreaming.value) return
  if (!userStore.token) {
    messages.value.push({ role: 'assistant', content: '请先登录后再提问。' })
    return
  }

  question.value = ''
  messages.value.push({ role: 'user', content: currentQuestion })
  const answer = { role: 'assistant', content: '' }
  messages.value.push(answer)
  isStreaming.value = true
  abortController.value = new AbortController()
  await nextTick()
  scrollAssistantToBottom()

  try {
    // 复用 AI 问答接口：paper_ids 指定当前论文，RAG 只检索本篇文献
    const response = await fetch(buildApiUrl('chat', '/ask'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        Authorization: userStore.token
      },
      body: JSON.stringify({
        question: currentQuestion,
        paper_ids: [Number(paperId.value)],
        session_id: null
      }),
      signal: abortController.value.signal
    })
    if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`)

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() || ''
      for (const block of blocks) {
        const content = parseSseBlock(block)
        if (content) {
          answer.content += content
          await nextTick()
          scrollAssistantToBottom()
        }
      }
    }
    const finalContent = parseSseBlock(buffer)
    if (finalContent) answer.content += finalContent
    if (!answer.content) answer.content = '接口未返回回答内容。'
  } catch (error) {
    if (error.name !== 'AbortError') answer.content = `问答失败：${error.message || '请检查后端服务。'}`
  } finally {
    isStreaming.value = false
    abortController.value = null
    await nextTick()
    scrollAssistantToBottom()
  }
}

watch(() => route.params.id, loadPaper)
onMounted(() => {
  // 窄屏默认收起侧边栏
  tocVisible.value = window.innerWidth > 760
  assistantVisible.value = window.innerWidth > 760
  loadPaper()
})
onUnmounted(() => {
  abortController.value?.abort()
  revokePdfUrl()
})
</script>

<style scoped>
.platform-page { min-height: 100vh; padding-top: 46px; padding-bottom: 62px; background: linear-gradient(180deg, #f4f7ff 0%, #f7f8fa 100%); }
.page-shell { max-width: 1400px; margin: 0 auto; padding: 18px 16px; }
.reader-layout, .panel, .state-panel { background: rgba(255,255,255,0.92); border: 1px solid rgba(148,163,184,0.14); border-radius: 20px; box-shadow: 0 12px 26px rgba(15, 23, 42, 0.05); }
.reader-layout { display: grid; grid-template-columns: 220px minmax(0, 1fr) 320px; gap: 18px; align-items: start; }
.reader-layout.no-toc { grid-template-columns: minmax(0, 1fr) 320px; }
.reader-layout.no-assistant { grid-template-columns: 220px minmax(0, 1fr); }
.reader-layout.no-toc.no-assistant { grid-template-columns: minmax(0, 1fr); }
.panel, .state-panel { padding: 18px; }
.state-panel { display: flex; flex-direction: column; align-items: flex-start; gap: 12px; color: #475569; }
.state-panel strong { color: #0f172a; font-size: 18px; }
.state-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.toc-panel { min-height: 420px; }
.toc-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 1px solid #e2e8f0; }
.toc-header .panel-title { margin: 0; padding: 0; border: none; }
.toc-close { border: none; background: none; cursor: pointer; font-size: 16px; line-height: 1; color: #94a3b8; padding: 4px 8px; border-radius: 8px; }
.toc-close:hover { color: #475569; background: #f1f5f9; }
.panel-title, .assistant-header { font-size: 16px; font-weight: 700; color: #0f172a; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 1px solid #e2e8f0; }
.toc-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; max-height: 70vh; overflow-y: auto; }
.toc-list li { padding: 12px 14px; border-radius: 12px; color: #475569; background: #f8fafc; border: 1px solid transparent; cursor: pointer; }
.toc-list li.active { color: #1d4ed8; background: #edf4ff; border-color: rgba(59, 130, 246, 0.18); font-weight: 600; }
.toc-empty { color: #94a3b8; font-size: 12px; padding: 8px 4px; }
.paper-header { padding-bottom: 12px; }
.paper-badge { display: inline-flex; padding: 6px 10px; border-radius: 999px; background: #e0ecff; color: #2147b0; font-size: 12px; font-weight: 600; margin-bottom: 12px; }
.paper-header h1 { margin: 0 0 12px; font-size: 30px; line-height: 1.25; color: #0f172a; }
.meta-row { display: flex; flex-wrap: wrap; gap: 12px; color: #64748b; font-size: 13px; }
.pdf-toolbar { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 18px; flex-wrap: wrap; }
.primary-btn, .ghost-btn { border: none; cursor: pointer; font: inherit; border-radius: 10px; padding: 10px 14px; text-decoration: none; display: inline-block; }
.primary-btn { background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%); color: #fff; font-weight: 600; }
.ghost-btn { background: #f1f5f9; color: #1e293b; }
.pdf-viewer { overflow: hidden; min-height: 680px; border: 1px solid #dbe5f0; border-radius: 16px; background: #64748b; }
.pdf-viewer iframe { display: block; width: 100%; height: 680px; border: 0; background: #fff; }
.pdf-empty { padding: 28px; color: #64748b; text-align: center; background: #f8fafc; border-radius: 16px; }
.abstract-block { margin-top: 18px; padding: 16px 18px; background: #f8fafc; border: 1px solid #edf2f7; border-radius: 14px; }
.abstract-block h2 { margin: 0 0 10px; font-size: 16px; color: #0f172a; }
.abstract-block p { margin: 0; color: #334155; line-height: 1.9; }
.section-preview { display: flex; flex-direction: column; gap: 18px; margin-top: 18px; }
.page-block { scroll-margin-top: 70px; background: #fff; border-radius: 16px; border: 1px solid #edf2f7; padding: 18px 20px; }
.page-block h2 { margin: 0 0 12px; font-size: 18px; color: #0f172a; }
.section-text { margin: 0; color: #334155; line-height: 1.9; font-family: inherit; font-size: 14px; white-space: pre-wrap; word-break: break-word; }
.assistant-panel { display: flex; flex-direction: column; gap: 18px; min-height: 460px; }
.assistant-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 1px solid #e2e8f0; }
.assistant-head .assistant-header { margin: 0; padding: 0; border: none; }
.assistant-hint { color: #94a3b8; font-size: 11px; margin-top: -12px; }
.assistant-body { display: flex; flex-direction: column; gap: 12px; max-height: 520px; overflow-y: auto; }
.qa-card { background: #f8fafc; border: 1px solid #edf2f7; border-radius: 14px; padding: 14px 16px; }
.qa-label { display: inline-block; font-size: 11px; font-weight: 700; color: #2563eb; letter-spacing: 0.08em; margin-bottom: 8px; }
.qa-card p { margin: 0; line-height: 1.7; white-space: pre-wrap; color: #334155; }
.user-card { background: #f8fafc; }
.assistant-card { background: #eef6ff; }
.assistant-input { margin-top: auto; display: flex; align-items: center; gap: 8px; border: 1px solid #dfe8f2; border-radius: 12px; background: #fff; padding: 8px 10px; }
.assistant-input input { flex: 1; border: none; outline: none; background: transparent; min-width: 0; font: inherit; color: #0f172a; }
.assistant-input button { border: none; background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%); color: #fff; width: 38px; height: 38px; border-radius: 10px; cursor: pointer; font-size: 18px; }
.assistant-input button:disabled { opacity: 0.5; cursor: not-allowed; }

/* 论文选择弹窗 */
.picker-overlay { position: fixed; z-index: 2000; inset: 0; display: grid; place-items: center; padding: 20px; background: rgba(15, 23, 42, 0.42); }
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
@media (max-width: 1000px) {
  .reader-layout { grid-template-columns: 180px minmax(0, 1fr); }
  .reader-layout.no-toc { grid-template-columns: minmax(0, 1fr); }
  .reader-layout.no-assistant { grid-template-columns: 180px minmax(0, 1fr); }
  .reader-layout.no-toc.no-assistant { grid-template-columns: minmax(0, 1fr); }
  .assistant-panel { grid-column: 1 / -1; }
}
@media (max-width: 760px) {
  .reader-layout { grid-template-columns: 1fr; }
  .reader-layout.no-toc, .reader-layout.no-assistant, .reader-layout.no-toc.no-assistant { grid-template-columns: 1fr; }
  .pdf-toolbar { justify-content: flex-start; }
  .pdf-viewer, .pdf-viewer iframe { min-height: 520px; height: 520px; }
}
</style>
