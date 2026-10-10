<template>
  <div class="ai-chat-container">
    <van-nav-bar title="学术论文助手" fixed />

    <div class="chat-layout">
      <!-- 左侧：历史会话 -->
      <aside class="sidebar">
        <button class="new-chat-btn" @click="newChat">＋ 新建会话</button>

        <div class="history-groups">
          <div v-for="group in historyGroups" :key="group.label" class="history-group">
            <div class="group-label">{{ group.label }}</div>
            <div
              v-for="s in group.items"
              :key="s.id"
              class="history-item"
              :class="{ active: s.id === currentSessionId }"
              @click="showHistory(s)"
            >{{ s.title }}</div>
          </div>
          <div v-if="!sessions.length" class="history-empty">暂无历史会话</div>
        </div>
      </aside>

      <!-- 右侧：文献选择 + 对话区 -->
      <main class="main-area">
        <section class="paper-panel">
          <div class="paper-panel-title">文献</div>
          <div class="paper-list">
            <label v-for="paper in selectedPapers" :key="paper.id" class="paper-item">
              <input type="checkbox" :value="paper.id" v-model="selectedPaperIds" />
              <span>{{ paper.title }}</span>
            </label>
            <span v-if="!selectedPapers.length" class="paper-none">未选择文献，AI 将进行通用问答</span>
            <button class="more-papers-btn" @click="showPicker = true">＋ 选择更多文献</button>
          </div>
        </section>

        <section class="messages-container" ref="messagesContainer">
          <div
            v-for="(message, index) in messages"
            :key="index"
            :class="['message', message.role === 'user' ? 'user-message' : 'ai-message']"
          >
            <div class="message-role">{{ message.role === 'user' ? '用户：' : 'AI：' }}</div>
            <div class="message-content">
              <div v-if="message.role === 'assistant' && message.content === ''" class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <div v-else v-html="formatMessage(message.content)"></div>
            </div>
          </div>
        </section>

        <div class="input-container">
          <van-field
            v-model="userInput"
            rows="1"
            autosize
            type="textarea"
            placeholder="输入你的问题……"
            class="chat-input"
            @keypress.enter.prevent="sendMessage"
          />
          <van-button
            type="primary"
            class="send-button"
            :disabled="isLoading || !userInput.trim()"
            @click="sendMessage"
          >
            发送
          </van-button>
        </div>
      </main>
    </div>

    <!-- 选择更多文献弹窗 -->
    <div v-if="showPicker" class="picker-mask" @click.self="showPicker = false">
      <div class="picker-panel">
        <div class="picker-title">选择文献</div>
        <div class="picker-list">
          <label v-for="paper in papers" :key="paper.id" class="picker-item">
            <input type="checkbox" :value="paper.id" v-model="selectedPaperIds" />
            <span>{{ paper.title }}</span>
          </label>
          <div v-if="!papers.length" class="picker-empty">暂无文献，请先到「我的文献」上传论文</div>
        </div>
        <button class="picker-close" @click="showPicker = false">完成</button>
      </div>
    </div>

    <tab-bar />
  </div>
</template>

<script setup>
import { computed, ref, onMounted, nextTick, watch } from 'vue';
import TabBar from '../components/TabBar.vue';
import { showToast } from 'vant';
import * as marked from 'marked';
import DOMPurify from 'dompurify';
import { buildApiUrl } from '../config/api';
import { useUserStore } from '../store/user';

// 登录用户信息（调用后端接口时带上 token）
const userStore = useUserStore();

// 聊天消息
const messages = ref([
  { role: 'assistant', content: '你好！我是学术论文助手，选择文献或直接提问，我会结合你的论文库回答。' }
]);
const userInput = ref('');
const messagesContainer = ref(null);
const isLoading = ref(false);
const isLoadingPapers = ref(true);
const selectedPaperIds = ref([]);
const papers = ref([]);
const sessions = ref([]);
const showPicker = ref(false);
const currentSessionId = ref(null);

const demoPapers = [
  { id: '1', title: 'Attention Is All You Need' },
  { id: '2', title: 'BERT: Pre-training of Deep Bidirectional Transformers' },
  { id: '3', title: 'Language Models are Unsupervised Multitask Learners' },
  { id: '4', title: 'Exploring the Limits of Transfer Learning with T5' }
];

// 当前勾选的论文
const selectedPapers = computed(() =>
  papers.value.filter((paper) => selectedPaperIds.value.includes(paper.id))
);

// 历史会话窗口按 今天/昨天/更早 分组
const historyGroups = computed(() => {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfYesterday = new Date(startOfToday.getTime() - 24 * 60 * 60 * 1000);
  const buckets = { 今天: [], 昨天: [], 更早: [] };

  for (const s of sessions.value) {
    const date = s.created_at ? new Date(s.created_at) : null;
    let label = '更早';
    if (date && date >= startOfToday) label = '今天';
    else if (date && date >= startOfYesterday) label = '昨天';
    buckets[label].push(s);
  }
  return ['今天', '昨天', '更早']
    .filter((label) => buckets[label].length)
    .map((label) => ({ label, items: buckets[label] }));
});

// 格式化消息内容（支持Markdown）
const formatMessage = (content) => {
  if (!content) return '';
  // 使用marked解析Markdown，并用DOMPurify清理HTML
  return DOMPurify.sanitize(marked.parse(content));
};

// 新建会话：清空对话区，开一个新会话窗口（首次提问时才在后端创建会话记录）
const newChat = () => {
  if (isLoading.value) return;
  currentSessionId.value = null;
  messages.value = [
    { role: 'assistant', content: '你好！我是学术论文助手，选择文献或直接提问，我会结合你的论文库回答。' }
  ];
  userInput.value = '';
  scrollToBottom();
};

const loadPapers = async () => {
  try {
    const response = await fetch(buildApiUrl('papers'), {
      headers: { Authorization: userStore.token }
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    const source = payload.data || payload.papers || payload;
    papers.value = (Array.isArray(source) ? source : []).map((paper) => ({
      id: String(paper.id || paper.paper_id),
      title: paper.title || paper.name || '未命名论文'
    })).filter((paper) => paper.id !== 'undefined');
  } catch {
    papers.value = demoPapers;
  } finally {
    isLoadingPapers.value = false;
  }
};

// 加载历史会话窗口列表
const loadSessions = async () => {
  try {
    const response = await fetch(buildApiUrl('chat', '/history'), {
      headers: { Authorization: userStore.token }
    });
    if (!response.ok) return;
    const payload = await response.json();
    sessions.value = Array.isArray(payload.data) ? payload.data : [];
  } catch {
    // 历史记录加载失败不影响问答
  }
};

// 点击历史会话窗口：恢复该窗口的全部问答，之后可以继续追问
const showHistory = async (s) => {
  currentSessionId.value = s.id;
  try {
    const response = await fetch(buildApiUrl('chat', `/history/${s.id}`), {
      headers: { Authorization: userStore.token }
    });
    if (!response.ok) return;
    const payload = await response.json();
    const records = Array.isArray(payload.data) ? payload.data : [];
    messages.value = records.flatMap((r) => [
      { role: 'user', content: r.question },
      { role: 'assistant', content: r.answer || '（无回复内容）' }
    ]);
    if (!messages.value.length) {
      messages.value = [{ role: 'assistant', content: '该会话暂无内容' }];
    }
    scrollToBottom();
  } catch {
    showToast('会话加载失败');
  }
};

// 发送消息
const sendMessage = async () => {
  if (!userInput.value.trim() || isLoading.value) return;

  // 检查登录状态
  if (!userStore.token) {
    showToast('请先登录');
    return;
  }

  // 添加用户消息（当前会话窗口内继续追加，不新建会话）
  const userMessage = userInput.value.trim();
  messages.value.push({ role: 'user', content: userMessage });
  userInput.value = '';

  // 添加AI消息占位
  messages.value.push({ role: 'assistant', content: '' });

  // 滚动到底部
  await nextTick();
  scrollToBottom();

  // 发送请求
  isLoading.value = true;
  try {
    await fetchAIResponse(userMessage);
    loadSessions();
  } catch (error) {
    console.error('Error fetching AI response:', error);
    // 更新最后一条消息为错误信息
    messages.value[messages.value.length - 1].content = `发生错误: ${error.message || '请检查网络连接和API设置'}`;
  } finally {
    isLoading.value = false;
    await nextTick();
    scrollToBottom();
  }
};

// 获取AI响应（SSE 流式，走后端 RAG + Agent 接口）
const fetchAIResponse = async (userMessage) => {
  try {
    const response = await fetch(buildApiUrl('chat', '/ask'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': userStore.token
      },
      body: JSON.stringify({
        question: userMessage,
        paper_ids: selectedPaperIds.value.map(Number),
        session_id: currentSessionId.value
      })
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error?.message || `HTTP error! status: ${response.status}`);
    }

    // 处理SSE流
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let aiResponse = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') continue;

          try {
            const json = JSON.parse(data);
            // 首个事件携带 session_id：记录当前会话窗口
            if (json.session_id) {
              currentSessionId.value = json.session_id;
            }
            const content = json.choices?.[0]?.delta?.content ||
                           json.output?.text ||
                           json.choices?.[0]?.message?.content || '';
            if (content) {
              aiResponse += content;
              // 更新最后一条消息
              messages.value[messages.value.length - 1].content = aiResponse;
              await nextTick();
              scrollToBottom();
            }
          } catch (e) {
            console.error('Error parsing SSE data:', e);
          }
        }
      }
    }

    // 如果没有收到任何内容
    if (!aiResponse) {
      messages.value[messages.value.length - 1].content = '抱歉，我无法生成回复。请稍后再试。';
    }
  } catch (error) {
    console.error('Fetch error:', error);
    throw error;
  }
};

// 滚动到底部
const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

// 监听消息变化，自动滚动
watch(messages, () => {
  nextTick(scrollToBottom);
}, { deep: true });

// 组件挂载时滚动到底部
onMounted(() => {
  scrollToBottom();
  loadPapers();
  loadSessions();
});
</script>

<style scoped>
* { box-sizing: border-box; }

.ai-chat-container {
  min-height: 100vh;
  padding-top: 46px;
  padding-bottom: 50px;
  background: linear-gradient(180deg, #eef5ff 0%, #f8fafc 46%, #f7f8fa 100%);
}

/* 两栏布局 */
.chat-layout {
  display: flex;
  gap: 14px;
  width: min(1360px, 100%);
  margin: 0 auto;
  padding: 14px 16px;
  align-items: stretch;
}

/* 左侧：历史会话 */
.sidebar {
  width: 185px;
  flex-shrink: 0;
  padding: 14px 10px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.new-chat-btn {
  width: 100%;
  padding: 9px 0;
  border: 1px dashed #93c5fd;
  border-radius: 10px;
  color: #1d4f83;
  background: #eff6ff;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
}

.new-chat-btn:hover {
  background: #dbeafe;
}

.history-groups {
  margin-top: 12px;
}

.group-label {
  padding: 8px 4px 4px;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 600;
}

.history-item {
  padding: 8px 10px;
  border-radius: 9px;
  color: #334155;
  font-size: 13px;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-item:hover {
  background: #f1f5f9;
}

.history-item.active {
  color: #1d4f83;
  background: #e0efff;
  font-weight: 600;
}

.history-empty {
  padding: 14px 4px;
  color: #94a3b8;
  font-size: 12px;
  text-align: center;
}

/* 右侧主区域 */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 10px;
}

/* 文献面板 */
.paper-panel {
  padding: 12px 14px;
  border: 1px solid #dbe5f0;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.92);
}

.paper-panel-title {
  margin-bottom: 8px;
  color: #1e3a5f;
  font-size: 13px;
  font-weight: 700;
}

.paper-list {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.paper-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid #dbe5f0;
  border-radius: 999px;
  color: #334155;
  background: #f8fafc;
  cursor: pointer;
  font-size: 12px;
  max-width: 320px;
}

.paper-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.paper-none {
  color: #94a3b8;
  font-size: 12px;
}

.more-papers-btn {
  padding: 6px 12px;
  border: 1px dashed #93c5fd;
  border-radius: 999px;
  color: #1d4f83;
  background: #eff6ff;
  cursor: pointer;
  font: inherit;
  font-size: 12px;
}

/* 消息区 */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 18px 16px;
  border: 1px solid #dbe5f0;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.92);
  min-height: 380px;
  max-height: calc(100vh - 300px);
}

.message {
  margin-bottom: 14px;
  max-width: min(78%, 680px);
}

.user-message {
  margin-left: auto;
}

.ai-message {
  margin-right: auto;
}

.message-role {
  margin-bottom: 4px;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 600;
}

.user-message .message-role {
  text-align: right;
}

.message-content {
  padding: 11px 15px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  line-height: 1.7;
  font-size: 14px;
  box-shadow: 0 5px 16px rgba(15, 23, 42, 0.035);
  word-break: break-word;
}

.user-message .message-content {
  border-color: #bfdbfe;
  background: #e0efff;
  color: #173b68;
}

.ai-message .message-content {
  border-color: #d8e8e7;
  background: #fff;
  color: #334155;
}

/* 输入区 */
.input-container {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 10px;
  border: 1px solid #dbe5f0;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.92);
}

.chat-input {
  flex: 1;
  border-radius: 10px;
  background: #f8fafc;
}

.send-button {
  min-width: 64px;
  border-radius: 10px;
  background: #1d4f83;
}

/* 文献选择弹窗 */
.picker-mask {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.42);
}

.picker-panel {
  width: min(560px, 92vw);
  max-height: 72vh;
  display: flex;
  flex-direction: column;
  padding: 18px;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.24);
}

.picker-title {
  margin-bottom: 12px;
  color: #1e3a5f;
  font-size: 16px;
  font-weight: 700;
}

.picker-list {
  flex: 1;
  overflow-y: auto;
}

.picker-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 8px;
  border-bottom: 1px solid #f1f5f9;
  color: #334155;
  cursor: pointer;
  font-size: 14px;
}

.picker-empty {
  padding: 20px 0;
  color: #94a3b8;
  font-size: 13px;
  text-align: center;
}

.picker-close {
  margin-top: 14px;
  padding: 10px 0;
  border: none;
  border-radius: 10px;
  color: #fff;
  background: #1d4f83;
  cursor: pointer;
  font: inherit;
  font-size: 14px;
  font-weight: 600;
}

/* 打字指示器 */
.typing-indicator {
  display: flex;
  padding: 5px;
}

.typing-indicator span {
  height: 8px;
  width: 8px;
  background-color: #999;
  border-radius: 50%;
  margin: 0 2px;
  animation: bounce 1.5s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-5px); }
}

/* Markdown 样式 */
.message-content pre {
  background-color: #f0f0f0;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
}

.message-content code {
  font-family: monospace;
  background-color: #f0f0f0;
  padding: 2px 4px;
  border-radius: 4px;
}

.message-content img {
  max-width: 100%;
}

/* 窄屏适配：侧栏变顶部横滑条 */
@media (max-width: 860px) {
  .chat-layout {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
  }

  .new-chat-btn {
    width: auto;
    flex-shrink: 0;
    padding: 8px 14px;
  }

  .history-groups {
    flex: 1;
    display: flex;
    gap: 8px;
    margin-top: 0;
    overflow-x: auto;
  }

  .history-group {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .group-label {
    flex-shrink: 0;
    padding: 0;
  }

  .history-item {
    max-width: 200px;
    flex-shrink: 0;
  }

  .messages-container {
    max-height: none;
    min-height: 320px;
  }
}
</style>
