<template>
  <div class="platform-page home-page">
    <van-nav-bar title="研究首页" fixed />

    <div class="page-shell">
      <header class="hero-card">
        <div class="hero-topline">
          <span class="brand-pill">ScholarSight</span>
          <span class="status-pill success">系统在线</span>
        </div>
        <h1>研究工作台</h1>
        <p>聚合文献发现、知识整理与智能洞察，面向高质量学术研究协作。</p>
        <div class="hero-actions">
          <button class="primary-btn">新增任务</button>
          <button class="ghost-btn">导入文献</button>
        </div>
      </header>

      <section class="stats-grid">
        <div class="stat-card">
          <span class="stat-label">文献总量</span>
          <strong>128</strong>
          <small>+12 本周</small>
        </div>
        <div class="stat-card">
          <span class="stat-label">待分析</span>
          <strong>24</strong>
          <small>3 项需优先</small>
        </div>
        <div class="stat-card">
          <span class="stat-label">热点关键词</span>
          <strong>19</strong>
          <small>AI + 计算机视觉</small>
        </div>
        <div class="stat-card">
          <span class="stat-label">进度完成</span>
          <strong>96%</strong>
          <small>本月研究目标</small>
        </div>
      </section>

      <section class="content-grid">
        <div class="panel">
          <div class="panel-header">
            <h3>今日推荐</h3>
            <span>更新于 09:30</span>
          </div>
          <div class="recommend-list">
            <div class="recommend-item">
              <div>
                <p class="item-title">Large Language Models in Scientific Discovery</p>
                <p class="meta">Nature Machine Intelligence · 2026</p>
              </div>
              <span class="tag blue">高相关</span>
            </div>
            <div class="recommend-item">
              <div>
                <p class="item-title">Graph Neural Networks for Literature Mining</p>
                <p class="meta">ACL Findings · 2025</p>
              </div>
              <span class="tag green">推荐</span>
            </div>
            <div class="recommend-item">
              <div>
                <p class="item-title">Causal Inference in Academic Search</p>
                <p class="meta">ICML Workshop · 2026</p>
              </div>
              <span class="tag purple">新发</span>
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-header">
            <h3>研究热点</h3>
            <span>趋势</span>
          </div>
          <div class="trend-list">
            <div class="trend-item">
              <div class="trend-left">
                <span>AI for Science</span>
                <small>指数 94</small>
              </div>
              <div class="bar"><i style="width: 94%"></i></div>
            </div>
            <div class="trend-item">
              <div class="trend-left">
                <span>Knowledge Graph</span>
                <small>指数 81</small>
              </div>
              <div class="bar"><i style="width: 81%"></i></div>
            </div>
            <div class="trend-item">
              <div class="trend-left">
                <span>Retrieval-Augmented Generation</span>
                <small>指数 76</small>
              </div>
              <div class="bar"><i style="width: 76%"></i></div>
            </div>
          </div>
        </div>
      </section>

      <section class="panel full-panel">
        <div class="panel-header">
          <h3>我的文献池</h3>
          <button class="plain-link">查看全部</button>
        </div>

        <div class="paper-list">
          <article class="paper-item">
            <div class="paper-main">
              <span class="paper-type">Survey</span>
              <h4>Attention Is All You Need: A Survey of Transformer Research</h4>
            </div>
            <div class="paper-meta">
              <span>已阅读 78%</span>
              <span>2026-09-18</span>
            </div>
          </article>

          <article class="paper-item">
            <div class="paper-main">
              <span class="paper-type accent">Method</span>
              <h4>Multimodal Retrieval for Scientific Discovery</h4>
            </div>
            <div class="paper-meta">
              <span>待标注 4 处</span>
              <span>2026-09-14</span>
            </div>
          </article>

          <article class="paper-item">
            <div class="paper-main">
              <span class="paper-type neutral">Dataset</span>
              <h4>Academic Benchmark for Cross-Lingual Literature Analysis</h4>
            </div>
            <div class="paper-meta">
              <span>已归档</span>
              <span>2026-09-12</span>
            </div>
          </article>
        </div>
      </section>
    </div>

    <tab-bar />
  </div>
</template>

<script setup>
import TabBar from '../components/TabBar.vue'
</script>

<style scoped>
.platform-page {
  min-height: 100vh;
  padding-top: 46px;
  padding-bottom: 62px;
  background: linear-gradient(180deg, #edf4ff 0%, #f5f7fb 18%, #f7f8fa 100%);
}

.page-shell {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px;
}

.hero-card {
  background: linear-gradient(135deg, #0f172a 0%, #173a73 100%);
  color: #fff;
  border-radius: 20px;
  padding: 22px 20px 18px;
  box-shadow: 0 18px 38px rgba(22, 50, 92, 0.18);
}

.hero-topline {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
}

.brand-pill,
.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  letter-spacing: 0.02em;
}

.brand-pill {
  background: rgba(255,255,255,0.12);
  border: 1px solid rgba(255,255,255,0.18);
}

.status-pill.success {
  background: rgba(52, 211, 153, 0.18);
  color: #d8fff0;
}

.hero-card h1 {
  margin: 0;
  font-size: 28px;
  line-height: 1.2;
}

.hero-card p {
  margin: 10px 0 18px;
  color: rgba(255,255,255,0.76);
  line-height: 1.6;
}

.hero-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.primary-btn,
.ghost-btn,
.plain-link {
  border: none;
  cursor: pointer;
  font: inherit;
}

.primary-btn {
  background: #fff;
  color: #1e3a8a;
  padding: 10px 16px;
  border-radius: 10px;
  font-weight: 600;
}

.ghost-btn {
  background: rgba(255,255,255,0.08);
  color: #fff;
  padding: 10px 16px;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.14);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-top: 18px;
}

.stat-card,
.panel {
  background: rgba(255,255,255,0.87);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(148,163,184,0.14);
  border-radius: 18px;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
}

.stat-card {
  padding: 16px 18px;
}

.stat-label {
  display: block;
  color: #64748b;
  font-size: 12px;
  margin-bottom: 12px;
}

.stat-card strong {
  display: block;
  font-size: 28px;
  line-height: 1.1;
  color: #0f172a;
  margin-bottom: 8px;
}

.stat-card small {
  color: #475569;
}

.content-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 18px;
  margin-top: 18px;
}

.panel {
  padding: 18px 18px 12px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.panel-header h3 {
  margin: 0;
  font-size: 18px;
  color: #0f172a;
}

.panel-header span,
.plain-link {
  color: #64748b;
  font-size: 12px;
}

.plain-link {
  background: transparent;
}

.recommend-list,
.trend-list,
.paper-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.recommend-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #eef2f7;
}

.recommend-item:last-child {
  border-bottom: none;
}

.item-title {
  margin: 0 0 4px;
  font-weight: 600;
  color: #111827;
}

.meta {
  margin: 0;
  color: #64748b;
  font-size: 12px;
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 6px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

.tag.blue { background: #e0f2fe; color: #0369a1; }
.tag.green { background: #dcfce7; color: #15803d; }
.tag.purple { background: #ede9fe; color: #6d28d9; }

.trend-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 0;
}

.trend-left {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #334155;
}

.trend-left small {
  color: #64748b;
}

.bar {
  width: 100%;
  height: 8px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #67e8f9 0%, #3b82f6 100%);
}

.full-panel {
  margin-top: 18px;
}

.paper-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 12px;
  border: 1px solid #edf2f7;
  border-radius: 14px;
  background: #f8fafc;
}

.paper-main {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.paper-type {
  display: inline-flex;
  width: fit-content;
  padding: 4px 8px;
  background: #dbeafe;
  color: #1d4ed8;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

.paper-type.accent {
  background: #dcfce7;
  color: #166534;
}

.paper-type.neutral {
  background: #f1f5f9;
  color: #475569;
}

.paper-main h4 {
  margin: 0;
  font-size: 16px;
  color: #0f172a;
}

.paper-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  color: #64748b;
  font-size: 12px;
}

@media (max-width: 760px) {
  .stats-grid,
  .content-grid {
    grid-template-columns: 1fr;
  }

  .paper-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .paper-meta {
    align-items: flex-start;
  }
}
</style>