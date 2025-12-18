<template>
  <main class="max-w-7xl mx-auto page-wrap">
    <!-- 统一缩放包装器：保证首页整体按比例缩小且相对位置不变 -->
    <div class="scale-wrap">
      <div class="grid-layout" style="--grid-gap: 38px; --grid-padding: 10px;">
    <!-- ① 系统总览卡片 -->
    <section class="card card--extra-bottom">
      <div class="space-y-4">
        <div class="kicker">中国省域低碳协同演化（2003–2022）</div>
        <h1 class="text-2xl md:text-3xl font-bold text-slate-900">中国省域低碳协同演化可视化系统</h1>
        <p class="text-slate-700 leading-relaxed hero-desc">
          基于省级尺度的<strong>能源结构</strong>、<strong>生态绿化</strong>与<strong>碳排放效率</strong>三维数据，
          通过<span class="muted-strong">空间识别</span> → <span class="muted-strong">协同机制</span> → <span class="muted-strong">时序演化</span>的分析链路，
          提供横向对标与纵向追踪的研究视角。
        </p>
        <!-- 使用自定义类 core-list，避免工具类冲突导致 gap 不生效 -->
        <div class="core-list">
          <div class="core-item">
            <div class="core-title">核心问题 1</div>
            <div class="core-desc">不同省份之间的低碳发展差异来自哪里？</div>
          </div>
          <div class="core-item">
            <div class="core-title">核心问题 2</div>
            <div class="core-desc">清洁能源、生态改善与碳效率是否形成协同？</div>
          </div>
          <div class="core-item">
            <div class="core-title">核心问题 3</div>
            <div class="core-desc">这种协同关系是否随时间发生结构性变化？</div>
          </div>
        </div>
      </div>
    </section>

    <!-- ② 分析链路示意 -->
    <section class="card">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-lg font-semibold text-slate-800">分析链路</h2>
        <div class="caption chain-caption">空间 → 协同 → 时序</div>
      </div>

      <div class="w-full overflow-x-auto">
        <div class="min-w-[740px]">
          <div class="chain-list">
            <!-- 模块一 -->
            <div class="chain-card">
              <div class="chain-title">模块一</div>
              <div class="chain-desc">空间识别分析：能源/绿化/排放的省域格局与差异</div>
            </div>
            <span class="flow-arrow self-center"></span>
            <!-- 模块二 -->
            <div class="chain-card">
              <div class="chain-title">模块二</div>
              <div class="chain-desc">协同机制分析：能源→效率的转化机制与协同指数</div>
            </div>
            <span class="flow-arrow self-center"></span>
            <!-- 模块三 -->
            <div class="chain-card">
              <div class="chain-title">模块三</div>
              <div class="chain-desc">时序演化分析：趋势、阶段跃迁与政策响应</div>
            </div>
          </div>
          <p class="mt-4 caption chain-caption">从“识别差异”到“解释机制”，再到“观察变化”，形成可操作的研究闭环。</p>
        </div>
      </div>
    </section>

    <!-- ③ 进入分析（模块入口） -> 改为与“核心问题”一致的样式 -->
    <section class="card card--extra-bottom">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-lg font-semibold text-slate-800">进入分析</h2>
        <div class="caption entry-caption">点击进入对应分析模块</div>
      </div>

      <div class="entry-list">
        <button type="button" class="entry-item" @click="nav.go('spatial')">
          <div class="entry-title">空间识别分析</div>
          <div class="entry-desc">省域能源结构 / 绿化覆盖 / 排放格局</div>
          <span class="entry-link">进入模块一 →</span>
        </button>

        <button type="button" class="entry-item" @click="nav.go('synergy')">
          <div class="entry-title">协同机制分析</div>
          <div class="entry-desc">能源—生态—效率协同关系与综合指数</div>
          <span class="entry-link">进入模块二 →</span>
        </button>

        <button type="button" class="entry-item" @click="nav.go('temporal')">
          <div class="entry-title">时序演化分析</div>
          <div class="entry-desc">20 年趋势、阶段跃迁与政策时间线</div>
          <span class="entry-link">进入模块三 →</span>
        </button>
      </div>
    </section>

    <!-- ⑤ 页脚信息（并排三列 + 统一字号） -->
    <section class="card footer-card">
      <div class="grid grid-cols-3 gap-32 xl:gap-40 items-start">
        <div class="footer-item">
          <div class="footer-title">数据来源</div>
          <div class="footer-text">国家统计局 / 中国能源统计年鉴 / 城市建设统计年鉴 / CEADs</div>
        </div>
        <div class="footer-item">
          <div class="footer-title">口径说明</div>
          <div class="footer-text">清洁能源与生态按省级比例；碳效率采用单位GDP排放；部分 2020–2022 年份为回归外推结果。</div>
        </div>
        <div class="footer-item">
          <div class="footer-title">系统信息</div>
          <div class="footer-text">版本 v1.0　|　最近更新：2025-11-18</div>
        </div>
      </div>
    </section>
      </div>
    </div>
  </main>
</template>

<script setup>
import { useNavStore } from '@/stores/nav'
const nav = useNavStore()
</script>

<style scoped>
/* 统一白色圆角卡片样式（保持与其他页面一致） */
.card {
  background: #ffffff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 6px 16px rgba(15, 181, 174, 0.25);
}

.module-tile {
  cursor: pointer;
  transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
  border: 1px solid #e5e7eb;
}
.module-tile:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 22px rgba(15, 181, 174, 0.25);
  border-color: #a7f3d0;
}

.kicker {
  font-size: 14px;
  letter-spacing: .08em;
  color: #0ea5a2;
  font-weight: 700;
  text-transform: uppercase;
}
.caption {
  font-size: 12px;
  color: #6b7280;
}
.muted-strong { color: #374151; }

.flow-arrow::after {
  content: "→";
  display: inline-block;
  margin: 0 12px;
  color: #94a3b8;
  font-weight: 600;
}
.footnote { font-size: 12px; color: #6b7280; }

/* 页脚信息卡片：统一为三列并排，标题与正文字号一致 */
.footer-card { }
.footer-title {
  font-size: var(--footer-title-size, 16px);
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 4px;
}
.footer-text {
  font-size: var(--footer-text-size, 16px);
  line-height: 1.65;
  color: #374151;
}

/* 增强三栏视觉间隙：每列增加左右内边距 */
.footer-item {
  padding-left: 25px;
  padding-right: 25px;
}

/* 页脚三栏的横向间距：显式设置 column-gap 提升生效稳定性 */
.footer-card .grid {
  column-gap: 160px; /* 与 gap-40 等效（约 160px） */
}
@media (min-width: 1280px) {
  .footer-card .grid {
    column-gap: 200px; /* xl 屏更宽（约 200px） */
  }
}

/* 页面包装层：与原型一致的左右留白与整体气质 */
.page-wrap {
  padding: 24px;
}

/* 与模块一一致的网格容器：提供统一的卡片间隙 */
.grid-layout {
  display: grid;
  gap: var(--grid-gap, 24px);
  padding: var(--grid-padding, 24px);
}

/* 系统总览卡片中的“核心问题”圆角容器：主题绿色背景与白字 */
.core-item {
  /* 背景：主题绿的淡化版本（可通过 --core-bg-alpha 微调淡度） */
  background: rgba(15, 181, 174, var(--core-bg-alpha, 0.12));
  color: var(--core-text-color, #111827);
  border: none;
  box-shadow: 0 6px 16px rgba(15, 181, 174, 0.18);
  border-radius: var(--core-radius, 16px);
  padding: var(--core-padding, 16px);
  min-height: var(--core-min-height, 80px); /* 高度更大 */
  width: var(--core-width, 500px);           /* 盒子宽度（更大并可控） */
}

.core-title {
  font-size: var(--core-title-size, 20px); /* 加大 */
  font-weight: 800;                        /* 加粗 */
  color: var(--core-title-color, #334155); /* 颜色更浅 */
  margin-bottom: 6px;
}

.core-desc {
  font-size: var(--core-body-size, 20px);               /* 问题文本更大 */
  line-height: var(--core-line-height, 1.8);            /* 行间距增大 */
  color: var(--core-desc-color, #384250);               /* 字体更浅 */
}

/* 避免工具类冲突，明确三列与间隙以及与父容器的上间隙 */
.core-list {
  display: grid;
  grid-template-columns: repeat(3, max-content); /* 每列宽度由盒子本身决定 */
  justify-content: center;                       /* 三个盒子整体居中 */
  gap: var(--core-gap, 120px);                   /* 缩小盒子间距 */
  margin-top: var(--core-top-gap, 16px);         /* 与上方文本的间隙 */
}

/* 顶部说明段落：可调字号与行高 */
.hero-desc {
  font-size: var(--hero-desc-size, 20px);
  line-height: var(--hero-desc-line, 1.85);
}

/* 首页统一缩放：优先使用 zoom（Chromium），其他浏览器回退到 transform */
.scale-wrap {
  zoom: var(--page-zoom, 0.68);
}
@supports not (zoom: 1) {
  .scale-wrap {
    transform: scale(var(--page-scale, 0.68));
    transform-origin: top left;
  }
}

/* 分析链路：白底绿色边框的圆角容器与可调尺寸 */
.chain-list {
  display: flex;
  align-items: stretch;
  justify-content: center;
  gap: var(--chain-gap, 36px);                  /* 增大三个容器之间的距离 */
}
.chain-card {
  background: #ffffff;
  border: var(--chain-border-width, 2px) solid var(--chain-border-color, var(--primary-color));
  border-radius: var(--chain-radius, 16px);
  padding: var(--chain-padding, 18px);
  width: var(--chain-width, 500px);             /* 缩短宽度（可调） */
  min-height: var(--chain-height, 90px);       /* 增大高度（可调） */
  box-shadow: 0 6px 16px rgba(15, 181, 174, 0.20);
}
.chain-title {
  font-size: var(--chain-title-size, 20px);     /* 模块标题更大 */
  font-weight: 800;                             /* 加粗 */
  color: #0f172add;                               /* 深色标题 */
  margin-bottom: 8px;
}
.chain-desc {
  font-size: var(--chain-desc-size, 19px);      /* 正文更大 */
  line-height: var(--chain-desc-line, 1.75);    /* 舒适行距 */
  color: #374151;                               /* 深灰正文 */
}
.chain-caption {
  font-size: var(--chain-caption-size, 17px);   /* 提升说明与“空间→协同→时序”字号 */
}

/* 进入分析：采用与核心问题一致的盒子视觉与可调参数 */
.entry-list {
  display: grid;
  grid-template-columns: repeat(3, max-content);
  justify-content: center;
  gap: var(--core-gap, 120px);                  /* 加大间距以与挑战/核心问题一致 */
  margin-top: var(--core-top-gap, 16px);
}
.entry-item {
  display: block;
  background: rgba(15, 181, 174, var(--core-bg-alpha, 0.12));
  color: var(--core-text-color, #111827);
  border: none;
  box-shadow: 0 6px 16px rgba(15, 181, 174, 0.18);
  border-radius: var(--core-radius, 16px);
  padding: var(--core-padding, 16px);
  min-height: var(--core-min-height, 100px);
  width: var(--core-width, 530px);
  cursor: pointer;
  text-align: left;
}
.entry-item:hover { transform: translateY(-1px); }
.entry-title {
  font-size: var(--core-title-size, 21px);
  font-weight: 800;
  color: var(--core-title-color, #334155);
  margin-bottom: 6px;
}
.entry-desc {
  font-size: var(--core-body-size, 20px);
  line-height: var(--core-line-height, 1.8);
  color: var(--core-desc-color, #384250);
}
.entry-link {
  margin-top: 10px;
  font-size: 16px;
  color: #0ea5a2;
  font-weight: 600;
}

/* 进入分析右上角说明：增大字体 */
.entry-caption { font-size: var(--entry-caption-size, 18px); }
/* 仅对系统总览与进入分析卡片增加底部内边距 */
.card--extra-bottom { padding-bottom: 35px; }
</style>
