<template>
  <div class="space-y-5">
    <!-- 标题与控制栏 -->
    <div class="flex items-center section-header">
      <h2 class="page-title text-2xl font-bold">协同机制分析</h2>
      <!-- 控件组（左对齐；年份作为最后一个按钮） -->
      <div class="flex items-center gap-4 ml-auto">
        <!-- 散点模式：保留标签 + 白色圆角按钮 -->
        <div class="relative flex items-center control-group">
          <span class="control-label">散点模式</span>
          <button ref="scatterButtonRef" class="control-button" @click="toggleScatterDropdown">
            {{ scatterMode === 'original' ? '原始值' : '标准化' }}
            <span class="control-arrow">▾</span>
          </button>
          <div v-if="showScatterDropdown" ref="scatterDropdownRef" class="control-dropdown" @click.stop>
            <ul>
              <li @click="selectScatterMode('original')" :class="{ selected: scatterMode === 'original' }">原始值</li>
              <li @click="selectScatterMode('standardized')" :class="{ selected: scatterMode === 'standardized' }">标准化</li>
            </ul>
          </div>
        </div>

        <!-- 雷达刻度：保留标签 + 白色圆角按钮 -->
        <div class="relative flex items-center control-group">
          <span class="control-label">雷达刻度</span>
          <button ref="radarScaleButtonRef" class="control-button" @click="toggleRadarScaleDropdown">
            {{ radarMode === 'original' ? '原值(0–1)' : 'Z 分数' }}
            <span class="control-arrow">▾</span>
          </button>
          <div v-if="showRadarScaleDropdown" ref="radarScaleDropdownRef" class="control-dropdown" @click.stop>
            <ul>
              <li @click="selectRadarMode('original')" :class="{ selected: radarMode === 'original' }">原值(0–1)</li>
              <li @click="selectRadarMode('z')" :class="{ selected: radarMode === 'z' }">Z 分数</li>
            </ul>
          </div>
        </div>

        <!-- 导出按钮已移除 -->

        <!-- 多省叠加选择（雷达图） -->
        <div class="relative flex items-center control-group">
          <span class="control-label">雷达叠加</span>
          <div class="relative" ref="selectDropdownRef">
            <button type="button" ref="selectButtonRef" @click="toggleDropdown" :title="selectedProvinces.join('、')"
              class="control-button min-w-[130px] text-left flex items-center justify-between gap-2">
              <span class="truncate max-w-[110px]">
                {{ selectedProvinces.length ? `已选${selectedProvinces.length}/4` : '请选择省份' }}
              </span>
              <span class="control-arrow">▾</span>
            </button>
            <div v-if="showSelectDropdown" ref="selectPanelRef"
                 class="fixed z-[20000] bg-white border border-gray-200 rounded shadow-xl p-2 radar-select-panel"
                 :style="{ top: dropdownTop + 'px', left: dropdownLeft + 'px', width: dropdownWidth + 'px', maxHeight: DROPDOWN_MAX_HEIGHT + 'px', overflowY: 'auto', overflowX: 'hidden', backgroundColor: '#ffffff', boxShadow: '0 6px 20px rgba(0,0,0,0.15)', borderRadius: '12px', border: '1px solid #e5e7eb', boxSizing: 'border-box' }">
              <div
                v-for="p in provinceOptions"
                :key="p"
                class="px-2 py-1 rounded cursor-pointer flex items-center gap-2"
                :class="[isSelected(p) ? 'bg-teal-50 text-[var(--primary-color)]' : 'hover:bg-gray-50', isDisabled(p) ? 'opacity-50 cursor-not-allowed' : '']"
                @click="!isDisabled(p) && toggleProvince(p)"
              >
                <input type="checkbox" class="mr-1" :checked="isSelected(p)" :disabled="isDisabled(p)"/>
                <span class="text-sm">{{ p }}</span>
              </div>
            </div>
          </div>
        </div>
        <!-- 年份按钮（放在所有按钮的最右侧） -->
        <div class="relative">
          <button ref="yearButtonRef" class="year-button" @click="toggleYearDropdown">
            {{ selectedYear }}
            <span class="year-button-arrow">▾</span>
          </button>
          <div v-if="showYearDropdown" ref="yearDropdownRef" class="year-dropdown" @click.stop>
            <ul>
              <li v-for="y in yearOptions" :key="y" @click="chooseYear(y)" :class="{ selected: y === selectedYear }">{{ y }}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
    <!-- 错误提示与重试 -->
    <div v-if="loadError" class="bg-yellow-50 border border-yellow-200 text-yellow-700 rounded-xl px-4 py-2 flex items-center justify-between">
      <span>数据加载异常：{{ loadError }}</span>
      <button @click="retryLoad" class="text-sm bg-yellow-600 text-white px-3 py-1 rounded">重试</button>
    </div>

    <!-- 图表网格布局（四卡片：雷达/散点/柱状/关联） -->
    <div class="grid-layout" style="--grid-gap: 24px; --grid-padding: 24px; grid-template-columns: 1fr 1fr; grid-template-rows: 420px 420px; grid-template-areas: 'radar scatter' 'bar chord';">
      <!-- 雷达图：能源/生态/效率均衡性 -->
      <div class="card flex flex-col" style="grid-area: radar">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-lg font-semibold text-gray-700">协同三角雷达图</h3>
          <div class="text-xs text-gray-500">指数：能源结构 / 生态水平 / 碳效率</div>
        </div>
        <div ref="radarRef" class="w-full flex-1" style="min-height:0"></div>
      </div>

      <!-- 散点图：机制验证（原始/标准化切换） -->
      <div class="card flex flex-col" style="grid-area: scatter">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-lg font-semibold text-gray-700">协同散点图</h3>
          <div class="text-xs text-gray-500">
            <span v-if="scatterMode==='original'">X：清洁能源占比；Y：单位GDP排放；点大小：绿化率</span>
            <span v-else>X：能源指数（z）；Y：碳效率指数（-z）；点大小：生态指数（z）</span>
          </div>
        </div>
        <div ref="scatterRef" class="w-full flex-1" style="min-height:0"></div>
      </div>

      <!-- 柱状图：协调发展指数（排序+高亮） -->
      <div class="card flex flex-col" style="grid-area: bar">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-lg font-semibold text-gray-700">协调发展指数</h3>
          <div class="text-xs text-gray-500">Synergy Score（加权综合）</div>
        </div>
        <!-- 权重滑条（0.4/0.3/0.3 默认，可调整即刻重算） -->
        <div class="flex items-center gap-3 mb-2">
          <div class="flex items-center gap-2">
            <span class="text-xs text-gray-600">能源</span>
            <input type="range" min="0" max="1" step="0.05" v-model.number="weightEnergy" class="w-24" />
            <span class="text-xs text-gray-600">{{ weightEnergy.toFixed(2) }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs text-gray-600">生态</span>
            <input type="range" min="0" max="1" step="0.05" v-model.number="weightEco" class="w-24" />
            <span class="text-xs text-gray-600">{{ weightEco.toFixed(2) }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs text-gray-600">碳效率</span>
            <input type="range" min="0" max="1" step="0.05" v-model.number="weightEfficiency" class="w-24" />
            <span class="text-xs text-gray-600">{{ weightEfficiency.toFixed(2) }}</span>
          </div>
        </div>
        <div ref="barRef" class="w-full flex-1" style="min-height:0"></div>
      </div>

      <!-- 关联图：能源—生态—效率相关强度（圆形图） -->
      <div class="card flex flex-col" style="grid-area: chord">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-lg font-semibold text-gray-700">能源—生态—碳效率关联图</h3>
          <div class="text-xs text-gray-500">皮尔逊相关（正/负，线宽=强度）</div>
        </div>
        <div ref="chordRef" class="w-full flex-1" style="min-height:0"></div>
      </div>
    </div>
  </div>
  
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'

// ===================== 类型定义 =====================
type StdRecord = { province: string; year: number; energy_index?: number; eco_index?: number; efficiency_index?: number }
type ComboRecord = { province: string; year: number; clean_ratio?: number; green_rate?: number; emission_per_gdp?: number }
type SynergyRecord = { province: string; year: number; synergy_score: number }
type RelationRecord = { year: number; variable_x: string; variable_y: string; correlation: number }
type EmissionFlag = { province: string; year: number; emission_total?: number; emission_per_gdp?: number; is_imputed_emission?: number }

// ===================== 状态与引用 =====================
const radarRef = ref<HTMLDivElement|null>(null)
const scatterRef = ref<HTMLDivElement|null>(null)
const barRef = ref<HTMLDivElement|null>(null)
const chordRef = ref<HTMLDivElement|null>(null)
let radarChart: echarts.ECharts | null = null
let scatterChart: echarts.ECharts | null = null
let barChart: echarts.ECharts | null = null
let chordChart: echarts.ECharts | null = null

const yearOptions = ref<number[]>(Array.from({ length: 18 }, (_, i) => 2005 + i))
const selectedYear = ref<number>(2022)
const scatterMode = ref<'original'|'standardized'>('original')
const radarMode = ref<'original'|'z'>('original')
// 密度层选项已移除

// 顶部年份下拉逻辑（与模块一一致：悬浮白色圆角面板）
const showYearDropdown = ref(false)
const yearButtonRef = ref<HTMLElement|null>(null)
const yearDropdownRef = ref<HTMLElement|null>(null)
function toggleYearDropdown() { showYearDropdown.value = !showYearDropdown.value }
function chooseYear(y: number) { selectedYear.value = y; showYearDropdown.value = false }

// 散点/雷达刻度下拉（白色圆角弹框）
const showScatterDropdown = ref(false)
const scatterButtonRef = ref<HTMLElement|null>(null)
const scatterDropdownRef = ref<HTMLElement|null>(null)
function toggleScatterDropdown() { showScatterDropdown.value = !showScatterDropdown.value }
function selectScatterMode(m: 'original'|'standardized') { scatterMode.value = m; showScatterDropdown.value = false }

const showRadarScaleDropdown = ref(false)
const radarScaleButtonRef = ref<HTMLElement|null>(null)
const radarScaleDropdownRef = ref<HTMLElement|null>(null)
function toggleRadarScaleDropdown() { showRadarScaleDropdown.value = !showRadarScaleDropdown.value }
function selectRadarMode(m: 'original'|'z') { radarMode.value = m; showRadarScaleDropdown.value = false }

const weightEnergy = ref<number>(0.4)
const weightEco = ref<number>(0.3)
const weightEfficiency = ref<number>(0.3)

const standardizedRecords = ref<StdRecord[]>([])
const combinedRecords = ref<ComboRecord[]>([])
const synergyRecords = ref<SynergyRecord[]>([])
const relationRecords = ref<RelationRecord[]>([])
const emissionRecords = ref<EmissionFlag[]>([])

const loadError = ref<string>('')
let outsideHandler: ((e: MouseEvent) => void) | null = null

// 省份名称规范化（与 SpatialView 一致，确保展示与联动统一）
function normalizeProvinceName(s: string) {
  const map: Record<string, string> = {
    '北京': '北京市', '北京市': '北京市',
    '天津': '天津市', '天津市': '天津市',
    '上海': '上海市', '上海市': '上海市',
    '重庆': '重庆市', '重庆市': '重庆市',
    '河北': '河北省', '河北省': '河北省',
    '山西': '山西省', '山西省': '山西省',
    '辽宁': '辽宁省', '辽宁省': '辽宁省',
    '吉林': '吉林省', '吉林省': '吉林省',
    '黑龙': '黑龙江省', '黑龙江': '黑龙江省', '黑龙江省': '黑龙江省',
    '江苏': '江苏省', '江苏省': '江苏省',
    '浙江': '浙江省', '浙江省': '浙江省',
    '安徽': '安徽省', '安徽省': '安徽省',
    '福建': '福建省', '福建省': '福建省',
    '江西': '江西省', '江西省': '江西省',
    '山东': '山东省', '山东省': '山东省',
    '河南': '河南省', '河南省': '河南省',
    '湖北': '湖北省', '湖北省': '湖北省',
    '湖南': '湖南省', '湖南省': '湖南省',
    '广东': '广东省', '广东省': '广东省',
    '海南': '海南省', '海南省': '海南省',
    '四川': '四川省', '四川省': '四川省',
    '贵州': '贵州省', '贵州省': '贵州省',
    '云南': '云南省', '云南省': '云南省',
    '陕西': '陕西省', '陕西省': '陕西省',
    '甘肃': '甘肃省', '甘肃省': '甘肃省',
    '青海': '青海省', '青海省': '青海省',
    '内蒙古': '内蒙古自治区', '内蒙': '内蒙古自治区', '内蒙古自治区': '内蒙古自治区',
    '广西': '广西壮族自治区', '广西壮族': '广西壮族自治区', '广西壮族自治区': '广西壮族自治区',
    '西藏': '西藏自治区', '西藏自治区': '西藏自治区',
    '宁夏': '宁夏回族自治区', '宁夏回族': '宁夏回族自治区', '宁夏回族自治区': '宁夏回族自治区',
    '新疆': '新疆维吾尔自治区', '新疆维吾尔': '新疆维吾尔自治区', '新疆维吾尔自治区': '新疆维吾尔自治区',
    '香港': '香港特别行政区', '香港特别行政区': '香港特别行政区',
    '澳门': '澳门特别行政区', '澳门特别行政区': '澳门特别行政区',
    '台湾': '台湾省', '台湾省': '台湾省',
  }
  return map[s] || s
}

// 省份选项（按当前年数据）
const provinceOptions = computed<string[]>(() => {
  const year = selectedYear.value
  const fromStd = standardizedRecords.value.filter(d => d.year === year && d.province)
  const names = Array.from(new Set(fromStd.map(d => normalizeProvinceName(String(d.province)))))
  return names.sort()
})

// 多省叠加选择（默认选择若干样例省份：北京/上海/广东/浙江，如不存在则取前4个）
const selectedProvinces = ref<string[]>([])
const showSelectDropdown = ref(false)
const selectDropdownRef = ref<HTMLElement|null>(null)
const selectButtonRef = ref<HTMLElement|null>(null)
const selectPanelRef = ref<HTMLElement|null>(null)
const dropdownTop = ref(0)
const dropdownLeft = ref(0)
const DROPDOWN_WIDTH_BASE = 200
const DROPDOWN_MAX_HEIGHT = 240
const VIEWPORT_MARGIN = 12
const RIGHT_SAFE_GAP = 24
const dropdownWidth = ref<number>(DROPDOWN_WIDTH_BASE)

function updateDropdownPosition() {
  if (!showSelectDropdown.value) return
  const btn = selectButtonRef.value
  if (!btn) return

  const rect = btn.getBoundingClientRect()
  const vw = window.innerWidth

  // 自适应面板宽度：两侧各留出 VIEWPORT_MARGIN，并为右侧预留 RIGHT_SAFE_GAP
  const maxAllowWidth = Math.max(160, vw - (VIEWPORT_MARGIN + RIGHT_SAFE_GAP) * 2)
  const width = Math.min(DROPDOWN_WIDTH_BASE, maxAllowWidth)
  dropdownWidth.value = Math.round(width)

  // 默认左对齐
  let left = rect.left
  let top = rect.bottom + 6

  const viewportRight = vw - RIGHT_SAFE_GAP // 右侧安全边界（视口坐标）
  const panelRightIfLeftAlign = left + width

  // 如果左对齐会越过右侧安全边界 → 翻转为右对齐（与按钮右侧对齐）
  if (panelRightIfLeftAlign > viewportRight) {
    left = rect.right - width
    if (left + width > viewportRight) {
      left = viewportRight - width
    }
  }

  // 左侧基础留白
  left = Math.max(left, VIEWPORT_MARGIN)

  // 计算面板实际高度，必要时显示在按钮上方
  const panel = selectPanelRef.value
  const panelHeight = panel ? Math.min(panel.scrollHeight, DROPDOWN_MAX_HEIGHT) : DROPDOWN_MAX_HEIGHT
  const maxTop = window.innerHeight - VIEWPORT_MARGIN - panelHeight
  if (top > maxTop) {
    const above = rect.top - 6 - panelHeight
    top = Math.max(above, VIEWPORT_MARGIN)
  }

  dropdownTop.value = Math.round(top)
  dropdownLeft.value = Math.round(left)
}
function toggleDropdown(){
  showSelectDropdown.value = !showSelectDropdown.value
  if (showSelectDropdown.value) {
    const btn = selectButtonRef.value
    if (btn) {
      const rect = btn.getBoundingClientRect()
      dropdownTop.value = rect.bottom + 6
      dropdownLeft.value = rect.left
    }
    nextTick(() => updateDropdownPosition())
  }
}
function isSelected(p: string) { return selectedProvinces.value.includes(p) }
function isDisabled(p: string) { return !isSelected(p) && selectedProvinces.value.length >= 4 }
function toggleProvince(p: string) {
  if (isSelected(p)) {
    selectedProvinces.value = selectedProvinces.value.filter(x => x !== p)
  } else {
    if (selectedProvinces.value.length >= 4) return
    selectedProvinces.value = [...selectedProvinces.value, p]
  }
}

// ===================== 数据加载 =====================
const pick = (path: string) => {
  const base = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '')
  return [base ? `${base}${path}` : '', path, `http://127.0.0.1:5000${path}`].filter(Boolean)
}
const getWithFallback = async (paths: string[]) => {
  for (const u of paths) {
    try { return (await axios.get(u)).data } catch {}
  }
  throw new Error('接口不可达')
}

async function loadAll() {
  try {
    loadError.value = ''
    const [std, combo, syn, rel, emi] = await Promise.all([
      getWithFallback(pick('/api/standardized')),
      getWithFallback(pick('/api/province')),
      getWithFallback(pick('/api/synergy')),
      getWithFallback(pick('/api/relation')),
      getWithFallback(pick('/api/emission')),
    ])
    standardizedRecords.value = std || []
    combinedRecords.value = combo || []
    synergyRecords.value = syn || []
    relationRecords.value = rel || []
    emissionRecords.value = emi || []

    // 默认叠加省份：按当年协同指数 Top4
    const year = selectedYear.value
    const synYear = synergyRecords.value.filter(d => d.year === year && Number.isFinite(Number(d.synergy_score)))
    const top4 = synYear.sort((a,b) => Number(b.synergy_score) - Number(a.synergy_score)).slice(0,4)
    const defaults = top4.map(d => normalizeProvinceName(String(d.province)))
    const fallback = provinceOptions.value.slice(0,4)
    selectedProvinces.value = defaults.length ? defaults : fallback
  } catch (e: any) {
    loadError.value = e?.message || '加载失败'
  }
}

// ===================== 联动与工具函数 =====================
function linkageSelect(name: string) {
  const n = normalizeProvinceName(name)
  if (!selectedProvinces.value.includes(n)) {
    if (selectedProvinces.value.length >= 4) return
    selectedProvinces.value = [...selectedProvinces.value, n]
  }
  // 高亮：散点与柱状
  try { scatterChart?.dispatchAction({ type: 'downplay' }); scatterChart?.dispatchAction({ type: 'highlight', name: n }) } catch {}
  try { barChart?.dispatchAction({ type: 'downplay' }); barChart?.dispatchAction({ type: 'highlight', name: n }) } catch {}
}

function percent(v?: number) {
  if (v == null || !Number.isFinite(v)) return '缺失'
  return `${(Number(v) * 100).toFixed(1)}%`
}

function formatValue(v?: number, unit: string = '') {
  if (v == null || !Number.isFinite(v)) return '缺失'
  return `${Number(v).toFixed(4)}${unit}`
}

function getByProvYear<T extends { province: string; year: number }>(rows: T[], p: string, y: number) {
  const n = normalizeProvinceName(p)
  return rows.find(d => normalizeProvinceName(String(d.province)) === n && Number(d.year) === y)
}

function computeSynergyByWeights(p: string, y: number) {
  const std = getByProvYear(standardizedRecords.value, p, y) as any
  if (!std) return { total: NaN, contrib: { energy: 0, eco: 0, eff: 0 }, raw: { ez: 0, gz: 0, fz: 0 } }
  
  const ez = Number(std?.energy_index ?? 0)
  const gz = Number(std?.eco_index ?? 0)
  const fz = Number(std?.efficiency_index ?? 0)
  
  // 如果生态贡献或效率贡献为0，则不计算协同发展指数
  if (gz === 0 || fz === 0) {
    return { total: NaN, contrib: { energy: 0, eco: 0, eff: 0 }, raw: { ez, gz, fz } }
  }
  
  // 约定效率取负贡献（符合"效率指数（-z）"语义）
  const cE = weightEnergy.value * ez
  const cG = weightEco.value * gz
  const cF = -weightEfficiency.value * fz
  const total = cE + cG + cF
  return { total, contrib: { energy: cE, eco: cG, eff: cF }, raw: { ez, gz, fz } }
}

function unifiedTooltip(name: string, year: number) {
  const std = getByProvYear(standardizedRecords.value, name, year) as any
  const combo = getByProvYear(combinedRecords.value as any[], name, year) as any
  const emi = getByProvYear(emissionRecords.value, name, year)
  const syn = computeSynergyByWeights(name, year)
  const clean = combo?.clean_ratio
  const green = combo?.green_rate
  const epg = combo?.emission_per_gdp ?? emi?.emission_per_gdp
  const s = syn.total
  
  return `
    <div class="font-bold text-gray-800">${normalizeProvinceName(name)} (${year})</div>
    <div class="grid grid-cols-[auto_1fr] gap-x-2 mt-1">
      <div class="text-gray-500">清洁能源占比:</div><div>${percent(clean)}</div>
      <div class="text-gray-500">绿化率:</div><div>${percent(green)}</div>
      <div class="text-gray-500">单位GDP排放:</div><div>${formatValue(epg, ' 吨/万元')}</div>
      <div class="text-gray-500">能源指数(z):</div><div>${formatValue(std?.energy_index)}</div>
      <div class="text-gray-500">生态指数(z):</div><div>${formatValue(std?.eco_index)}</div>
      <div class="text-gray-500">碳效率指数(-z):</div><div>${formatValue(std?.efficiency_index)}</div>
      <div class="text-gray-500">协同指数:</div><div>${formatValue(s)}</div>
      <div class="text-gray-500">排放是否估算:</div><div>${emi?.is_imputed_emission ? '是' : '否'}</div>
    </div>
  `
}

// 导出功能已移除

// ===================== 渲染：雷达 =====================
function renderRadar() {
  if (!radarRef.value) return
  if (radarChart) radarChart.dispose()
  radarChart = echarts.init(radarRef.value)

  const year = selectedYear.value
  const stdRows = standardizedRecords.value.filter(d => d.year === year)
  const comboRows = combinedRecords.value.filter(d => d.year === year)
  // 颜色顺序：蓝 / 绿 / 黄 / 红（超过4个后继续使用其他辅助色）
  const palette = ['#3b82f6','#22c55e','#f59e0b','#ef4444','#8b5cf6','#06b6d4']
  const dataItems = selectedProvinces.value.map((p, i) => {
    const color = palette[i % palette.length]
    if (radarMode.value === 'z') {
      const row = stdRows.find(d => normalizeProvinceName(String(d.province)) === p)
      return {
        name: p,
        value: [Number(row?.energy_index ?? 0), Number(row?.eco_index ?? 0), Number(row?.efficiency_index ?? 0)],
        lineStyle: { color, width: 2 },
        itemStyle: { color },
        areaStyle: { color, opacity: 0.18 },
        emphasis: { lineStyle: { width: 3, color } },
      }
    } else {
      // 原值模式：clean、green 直接用 0–1；效率需做 0–1 归一并反向（越低越好）
      const row = (comboRows as any[]).find(d => normalizeProvinceName(String(d.province)) === p) as any
      const xs = (comboRows as any[]).map(d => Number((d as any).emission_per_gdp ?? 0)).filter((v: number) => Number.isFinite(v) && v > 0)
      const minE = xs.length ? Math.min(...xs) : 0
      const maxE = xs.length ? Math.max(...xs) : 1
      const clean = Number((row?.clean_ratio) ?? 0)
      const green = Number((row?.green_rate) ?? 0)
      const effRaw = Number((row?.emission_per_gdp) ?? 0)
      const effNorm = (maxE === minE) ? 0.5 : (1 - (effRaw - minE) / (maxE - minE))
      return {
        name: p,
        value: [clean, green, effNorm],
        lineStyle: { color, width: 2 },
        itemStyle: { color },
        areaStyle: { color, opacity: 0.18 },
        emphasis: { lineStyle: { width: 3, color } },
      }
    }
  })

  const maxAbs = (arr: number[]) => Math.max(1, ...arr.map(v => Math.abs(v)))
  const allValsZ = stdRows.flatMap(r => [r.energy_index ?? 0, r.eco_index ?? 0, r.efficiency_index ?? 0])
  const axisMaxZ = Math.min(3, Math.ceil(maxAbs(allValsZ)))

  // 全国平均（参考虚线）
  let avgVector: number[] = [0,0,0]
  if (radarMode.value === 'z') {
    const mean = (arr: number[]) => arr.reduce((a,b)=>a+b,0)/(arr.length||1)
    const eAvg = mean(stdRows.map(r => Number(r.energy_index ?? 0)))
    const gAvg = mean(stdRows.map(r => Number(r.eco_index ?? 0)))
    const fAvg = mean(stdRows.map(r => Number(r.efficiency_index ?? 0)))
    avgVector = [eAvg, gAvg, fAvg]
  } else {
    const xs = (comboRows as any[]).map(d => Number((d as any).emission_per_gdp ?? 0)).filter((v: number) => Number.isFinite(v) && v > 0)
    const minE = xs.length ? Math.min(...xs) : 0
    const maxE = xs.length ? Math.max(...xs) : 1
    const mean = (arr: number[]) => arr.reduce((a,b)=>a+b,0)/(arr.length||1)
    const cleanAvg = mean((comboRows as any[]).map(r => Number((r as any).clean_ratio ?? 0)))
    const greenAvg = mean((comboRows as any[]).map(r => Number((r as any).green_rate ?? 0)))
    const effAvgRaw = mean((comboRows as any[]).map(r => Number((r as any).emission_per_gdp ?? 0)))
    const effAvg = (maxE === minE) ? 0.5 : (1 - (effAvgRaw - minE) / (maxE - minE))
    avgVector = [cleanAvg, greenAvg, effAvg]
  }

  radarChart.setOption({
    tooltip: { show: true, confine: true, formatter: (p: any) => unifiedTooltip(p.name, year) },
    legend: { type: 'scroll', right: 8, bottom: 8, orient: 'vertical', textStyle: { color: '#555' } },
    radar: {
      indicator: radarMode.value === 'z' ? [
        { name: '能源结构（z）', max: axisMaxZ, min: -axisMaxZ },
        { name: '生态水平（z）', max: axisMaxZ, min: -axisMaxZ },
        { name: '碳效率（-z）', max: axisMaxZ, min: -axisMaxZ },
      ] : [
        { name: '能源结构(%)', min: 0, max: 1 },
        { name: '生态水平(%)', min: 0, max: 1 },
        { name: '效率(吨/万元, 低=好)', min: 0, max: 1 },
      ],
      axisName: { color: '#64748b' },
      splitLine: { lineStyle: { color: '#cbd5e1', opacity: 0.6 } },
      splitArea: { show: false, areaStyle: { opacity: 0 } },
      radius: '75%', // 放大雷达图
      center: ['50%', '50%'], // 保持居中
    },
    series: [
      { type: 'radar', symbol: 'none', lineStyle: { color: '#94a3b8', type: 'dashed' }, data: [avgVector] },
      { type: 'radar', data: dataItems },
    ],
  })
}

// ===================== 渲染：散点 =====================
function renderScatter() {
  if (!scatterRef.value) return
  if (scatterChart) scatterChart.dispose()
  scatterChart = echarts.init(scatterRef.value)

  const year = selectedYear.value
  const comboRows = combinedRecords.value.filter(d => d.year === year)
  const stdRows = standardizedRecords.value.filter(d => d.year === year)

  const toNum = (v: any) => {
    const n = Number(v)
    return Number.isFinite(n) ? n : undefined
  }

  // 原始模式数据：x=clean_ratio, y=emission_per_gdp, size=green_rate
  const dataOriginal = comboRows.map(d => {
    const name = normalizeProvinceName(String(d.province))
    const rawX = toNum(d.clean_ratio)
    const rawY = toNum(d.emission_per_gdp)
    const rawS = toNum(d.green_rate)
    const missingCount = [rawX, rawY, rawS].filter(v => v === undefined).length
    if (missingCount === 3) return null // 三项都缺 → 不显示气泡
    
    // 保留原始值，不替换为0，以便在tooltip中显示"缺失"
    return {
      name,
      value: [rawX !== undefined ? rawX : null, rawY !== undefined ? rawY : null],
      symbolSize: 8 + (rawS !== undefined ? rawS * 28 : 0),
      itemStyle: { color: missingCount > 0 ? '#ef4444' : '#0ea5e9', opacity: 0.85 },
      __meta: { rawX, rawY, rawS, missingCount }
    }
  }).filter(Boolean) as any[]

  // 标准化模式：symbolSize 需要正值 → 使用 min-max 归一到 [12, 36]
  const ecoVals = stdRows.map(d => Number(d.eco_index ?? 0))
  const ecoMin = Math.min(...ecoVals, 0), ecoMax = Math.max(...ecoVals, 1)
  const scaleStdSize = (v: number) => 12 + (ecoMax === ecoMin ? 0 : ((v - ecoMin) / (ecoMax - ecoMin)) * 24)
  const dataStd = stdRows.map(d => {
    const name = normalizeProvinceName(String(d.province))
    const rawX = toNum(d.energy_index)
    const rawY = toNum(d.efficiency_index)
    const rawS = toNum(d.eco_index)
    const missingCount = [rawX, rawY, rawS].filter(v => v === undefined).length
    if (missingCount === 3) return null
    const x = rawX ?? 0
    const y = rawY ?? 0
    const size = rawS === undefined ? 16 : scaleStdSize(rawS)
    return { name, value: [x, y], symbolSize: size, itemStyle: { color: missingCount > 0 ? '#ef4444' : '#22c55e', opacity: 0.85 }, __meta: { rawX, rawY, rawS, missingCount } }
  }).filter(Boolean) as any[]

  const useOriginal = scatterMode.value === 'original'

  // 计算原始模式的Y轴合适范围，避免数据过分稀疏或不可见
  const yVals = (dataOriginal as any[])
    .map(d => (d.__meta?.rawY))
    .filter((v: any) => Number.isFinite(v) && v > 0) as number[]
  const sorted = [...yVals].sort((a,b) => a-b)
  const q = (p:number) => sorted.length ? sorted[Math.min(sorted.length-1, Math.max(0, Math.floor(p*(sorted.length-1))))] : 0
  const yMin = q(0.05)
  const yMax = q(0.95)

  const optionOriginal = {
    tooltip: { trigger: 'item', confine: true, formatter: (p: any) => unifiedTooltip(p.name, year) },
    grid: { left: 40, right: 40, top: 40, bottom: 50 },
    xAxis: { type: 'value', name: '清洁能源占比(%)', min: 0, max: 1, axisLabel: { formatter: (v: number) => `${Math.round(v*100)}%`, color: '#555' } },
    // 使用线性坐标并限定可视区间（5%~95%分位）以避免点过度聚集/不可见
    yAxis: { type: 'value', name: '单位GDP排放(吨/万元) ↓', min: yMin || 'dataMin', max: yMax || 'dataMax', scale: true, axisLabel: { color: '#555' }, splitLine: { show: true } },
    dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 6 }],
    series: [
      // 密度层（可选）
      // 密度层已移除
      {
      type: 'scatter', name: '原始值',
      data: dataOriginal,
      symbolSize: (val: any, params: any) => params?.data?.symbolSize ?? 12,
      itemStyle: (p: any) => p?.data?.itemStyle || { color: '#0ea5e9' },
      emphasis: { itemStyle: { borderColor: '#f59e0b', borderWidth: 2 } },
        markLine: { silent: true, lineStyle: { color: '#9ca3af' }, data: [{ xAxis: median((dataOriginal as any[]).map(d => d.__meta?.rawX ?? 0)) }, { yAxis: median((dataOriginal as any[]).map(d => d.__meta?.rawY ?? 0)) }] }
      }
    ]
  }

  const optionStd = {
    tooltip: { trigger: 'item', confine: true, formatter: (p: any) => unifiedTooltip(p.name, year) },
    grid: { left: 40, right: 40, top: 40, bottom: 50 },
    xAxis: { type: 'value', name: '能源指数（z）', axisLabel: { color: '#555' } },
    yAxis: { type: 'value', name: '效率指数（-z）', axisLabel: { color: '#555' } },
    dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 6 }],
    series: [{
      type: 'scatter', name: '标准化',
      data: dataStd,
      symbolSize: (val: any, params: any) => params.data.symbolSize ?? 12,
      itemStyle: (p: any) => p?.data?.itemStyle || { color: '#22c55e' },
      emphasis: { itemStyle: { borderColor: '#f59e0b', borderWidth: 2 } },
      markLine: { silent: true, lineStyle: { color: '#9ca3af' }, data: [{ xAxis: median((dataStd as any[]).map(d => d.__meta?.rawX ?? 0)) }, { yAxis: median((dataStd as any[]).map(d => d.__meta?.rawY ?? 0)) }] }
    }]
  }

  scatterChart.setOption(useOriginal ? optionOriginal : optionStd)

  // 点击点 → 联动雷达/柱状
  const sc = scatterChart as echarts.ECharts
  sc.off('click')
  sc.on('click', (p: any) => { if (p?.name) linkageSelect(p.name) })

  // 刷选 → 联动雷达/柱状
  sc.off('brushSelected')
  sc.on('brushSelected', (params: any) => {
    try {
      const indices = params?.batch?.[0]?.selected?.[0]?.dataIndex || []
      const pool: any[] = useOriginal
        ? ((optionOriginal.series?.[0]?.data as any[]) || [])
        : ((optionStd.series?.[0]?.data as any[]) || [])
      const names: string[] = []
      for (const idx of indices) {
        const n = pool?.[idx]?.name
        if (n && !names.includes(n)) names.push(n)
      }
      if (names.length) {
        selectedProvinces.value = names.slice(0,4)
        renderRadar(); renderBar()
      }
    } catch {}
  })
}

// ===================== 散点辅助：分位数/中位数与热力网格/回归 =====================
function median(arr: number[]) {
  const a = (arr || []).filter(v => Number.isFinite(v)).sort((x,y)=>x-y)
  const n = a.length
  if (!n) return 0
  const m = Math.floor(n/2)
  if (n % 2 === 1) return a[m] ?? 0
  const li = m - 1 >= 0 ? m - 1 : 0
  const ri = m < n ? m : n - 1
  const left = a[li] ?? 0
  const right = a[ri] ?? 0
  return (left + right) / 2
}

function computeHeatmapGrid(points: [number,number][], nx: number, ny: number, xRange: [number,number], yRange: [number,number]) {
  const [xmin, xmax] = xRange
  const [ymin, ymax] = yRange
  const dx = (xmax - xmin) / nx
  const dy = (ymax - ymin) / ny
  const grid: number[][] = Array.from({length: nx}, () => Array(ny).fill(0))
  for (const p of points) {
    const x = Number(p[0]) || 0
    const y = Number(p[1]) || 0
    const ix = Math.min(nx-1, Math.max(0, Math.floor((x - xmin) / dx)))
    const iy = Math.min(ny-1, Math.max(0, Math.floor((y - ymin) / dy)))
    const row = grid[ix]!
    row[iy] = (row[iy] ?? 0) + 1
  }
  const result: [number,number,number][] = []
  for (let i=0; i<nx; i++) {
    const row = grid[i]!
    for (let j=0; j<ny; j++) {
      const cx = xmin + (i+0.5)*dx
      const cy = ymin + (j+0.5)*dy
      const v = row[j] ?? 0
      if (v>0) result.push([cx, cy, v])
    }
  }
  return result
}

// 回归功能已删除

// ===================== 渲染：柱状（协同指数） =====================
function renderBar() {
  if (!barRef.value) return
  if (barChart) barChart.dispose()
  barChart = echarts.init(barRef.value)

  const year = selectedYear.value
  const stdRows = standardizedRecords.value.filter(d => d.year === year)
  // 以权重重算协同指数（energy + eco - efficiency）
  const computed = stdRows.map(r => {
    const name = normalizeProvinceName(String(r.province))
    const s = computeSynergyByWeights(name, year)
    // 如果协同指数为0，可能是数据缺失，不显示该省份
    if (s.total === 0) return null
    return { name, value: s.total, contrib: s.contrib }
  }).filter(d => d !== null && Number.isFinite(d?.value))
  const ordered = computed.sort((a,b) => (b?.value || 0) - (a?.value || 0))

  const categories = ordered.map(d => d?.name || '')
  const values = ordered.map(d => d?.value || 0)
  const min = Math.min(...values, -2), max = Math.max(...values, 2)
  const imputedSet = new Set((emissionRecords.value || []).filter(d => d?.year === year && Number(d?.is_imputed_emission) === 1).map(d => normalizeProvinceName(String(d?.province || ''))))
  const contribMap: Record<string, { energy: number, eco: number, eff: number }> = {}
  ordered.forEach(d => { if(d) contribMap[d.name] = d.contrib })

  barChart.setOption({
    tooltip: {
      trigger: 'item', confine: true,
      formatter: (p: any) => {
        const name = p.name
        const s = Number(p.value || 0)
        const c = contribMap[name] || { energy: 0, eco: 0, eff: 0 }
        return `${name}<br/>协同指数：${s.toFixed(2)}<br/>能源贡献：${c.energy.toFixed(2)}<br/>生态贡献：${c.eco.toFixed(2)}<br/>效率贡献：${c.eff.toFixed(2)}`
      }
    },
    grid: { left: 40, right: 30, top: 40, bottom: 60 },
    xAxis: { type: 'category', data: categories, axisLabel: { rotate: 45, color: '#555' } },
    yAxis: { type: 'value', name: '协同指数', axisLabel: { color: '#555' } },
    visualMap: { show: false, min: -2, max: 2, inRange: { color: ['#22d3ee','#e5e7eb','#fb923c'] } },
    series: [{
      type: 'bar', name: '协同指数',
      data: ordered.map(d => d ? { name: d.name, value: d.value, itemStyle: imputedSet.has(d.name || '') ? { decal: { symbol: 'line' } } : {} } : {}),
      emphasis: { itemStyle: { borderColor: '#f2c94c', borderWidth: 2 } },
    }],
    legend: { show: false }
  })

  const bc = barChart as echarts.ECharts
  bc.off('click')
  bc.on('click', (p: any) => {
    const idx = p?.dataIndex ?? 0
    const name = categories?.[idx]
    if (name) linkageSelect(name)
  })
}

// ===================== 渲染：关联图（圆形 Graph 近似 Chord） =====================
function renderChord() {
  if (!chordRef.value) return
  if (chordChart) chordChart.dispose()
  chordChart = echarts.init(chordRef.value)

  const year = selectedYear.value
  const rows = relationRecords.value.filter(d => d.year === year)
  // 变量映射到中文名称
  const labelMap: Record<string,string> = {
    clean_ratio: '能源清洁化',
    green_rate: '生态改善',
    emission_per_gdp: '碳效率'
  }

  // 节点（固定三节点圆形布局）
  const nodes = [
    { name: labelMap.clean_ratio },
    { name: labelMap.green_rate },
    { name: labelMap.emission_per_gdp },
  ]
  // 边（宽度按 |corr|，颜色正负）
  const edges = rows.filter(r => r.variable_x !== r.variable_y).map(r => {
    const corr = Number(r.correlation || 0)
    const width = Math.max(1, Math.round(Math.abs(corr) * 8))
    const color = corr >= 0 ? '#fb923c' : '#3b82f6'
    return { source: labelMap[r.variable_x], target: labelMap[r.variable_y], value: corr, lineStyle: { width, color, opacity: 0.7 } }
  })

  chordChart.setOption({
    tooltip: { trigger: 'item', confine: true, formatter: (p: any) => {
      if (p?.dataType === 'edge') {
        const src = p?.data?.source ?? ''
        const dst = p?.data?.target ?? ''
        const val = Number(p?.data?.value ?? 0)
        return `${src} ↔ ${dst}<br/>相关：${val.toFixed(2)}`
      }
      return `${p?.name ?? ''}`
    } },
    series: [{
      type: 'graph', layout: 'circular',
      circular: { rotateLabel: true },
      roam: false,
      label: { 
        show: true, 
        color: '#334155',
        position: 'outside',
        distance: 5  // 增加标签与节点的距离
      },
      lineStyle: { curveness: 0.25 },
      data: nodes,
      edges,
      // 缩小图形整体大小
      zoom: 0.9,
      // 向上移动图形
      top: '5%'
    }]
  })
}

// ===================== 生命周期与联动 =====================
function retryLoad() {
  loadAll().then(() => { renderRadar(); renderScatter(); renderBar(); renderChord() })
}

onMounted(async () => {
  await loadAll()
  renderRadar(); renderScatter(); renderBar(); renderChord()
  // 点击外部收起下拉
  outsideHandler = (e: MouseEvent) => {
    const target = e.target as Node
    // 雷达叠加
    const anchor = selectDropdownRef.value
    const panel = selectPanelRef.value
    const inAnchor = !!anchor && anchor.contains(target)
    const inPanel = !!panel && panel.contains(target)
    if (!inAnchor && !inPanel) showSelectDropdown.value = false
    // 年份
    const inYearBtn = !!yearButtonRef.value && yearButtonRef.value.contains(target)
    const inYearPanel = !!yearDropdownRef.value && yearDropdownRef.value.contains(target)
    if (!inYearBtn && !inYearPanel) showYearDropdown.value = false
    // 散点模式
    const inScatterBtn = !!scatterButtonRef.value && scatterButtonRef.value.contains(target)
    const inScatterPanel = !!scatterDropdownRef.value && scatterDropdownRef.value.contains(target)
    if (!inScatterBtn && !inScatterPanel) showScatterDropdown.value = false
    // 雷达刻度
    const inRadarBtn = !!radarScaleButtonRef.value && radarScaleButtonRef.value.contains(target)
    const inRadarPanel = !!radarScaleDropdownRef.value && radarScaleDropdownRef.value.contains(target)
    if (!inRadarBtn && !inRadarPanel) showRadarScaleDropdown.value = false
  }
  document.addEventListener('mousedown', outsideHandler)
  window.addEventListener('resize', updateDropdownPosition)
  window.addEventListener('scroll', updateDropdownPosition, { passive: true })
})

onBeforeUnmount(() => {
  radarChart?.dispose(); scatterChart?.dispose(); barChart?.dispose(); chordChart?.dispose()
  if (outsideHandler) document.removeEventListener('mousedown', outsideHandler)
  window.removeEventListener('resize', updateDropdownPosition)
  window.removeEventListener('scroll', updateDropdownPosition)
})

watch([selectedYear, scatterMode, selectedProvinces, radarMode, weightEnergy, weightEco, weightEfficiency], () => { renderRadar(); renderScatter(); renderBar(); renderChord() })
</script>

<style scoped>
/* 页面标题统一左侧间距与颜色（略深的绿色） */
.page-title {
  margin-left: var(--title-left-gap, 28px) !important;
  color: var(--primary-dark, #179299) !important;
}
/* 顶部容器：与主体右边界保持统一留白 */
.section-header { padding-right: var(--grid-padding, 24px); }
/* 每个控件组与下一个标签之间增加外间距；标签样式 */
.control-group { margin-right: 20px; }
.control-label { color: #64748b; font-size: 14px; margin-right: 8px; }
/* 控件组容器占据中间空间，避免把年份按钮挤没 */
.controls-wrap { flex: 1; min-width: 0; }

/* 顶部年份按钮（主题色圆角、白色加粗）以及悬浮下拉面板 */
.year-button {
  background-color: var(--primary, var(--primary-dark, #1aaeb6));
  color: #ffffff;
  font-weight: 700;
  font-size: 18px;
  border: none;
  border-radius: 9999px;
  padding: 10px 20px;
  box-shadow: 0 6px 16px rgba(15, 181, 174, 0.25);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.year-button-arrow { margin-left: 8px; opacity: 0.9; }
.year-dropdown {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  min-width: 120px; /* 略微缩窄 */
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 6px 20px rgba(0,0,0,0.15);
  border: 1px solid #e5e7eb;
  z-index: 20000;
  padding: 8px;
  max-height: 260px; /* 缩短高度，滚动查看 */
  overflow-y: auto;
}
.year-dropdown ul { list-style: none; margin: 0; padding: 0; }
.year-dropdown li {
  color: #4b5563; /* 灰色字体 */
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
}
.year-dropdown li:hover { background: #f3f4f6; }
.year-dropdown li.selected { font-weight: 700; color: #111827; }

/* 白色圆角控件按钮与弹框（散点模式、雷达刻度、雷达叠加按钮复用） */
.control-button {
  background: #ffffff;
  color: #374151;
  border: 1px solid #e5e7eb;
  border-radius: 9999px;
  padding: 6px 12px;
  box-shadow: 0 6px 16px rgba(15, 181, 174, 0.25);
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.control-arrow { margin-left: 6px; color: #6b7280; }
.control-dropdown {
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  min-width: 130px; /* 略微缩窄 */
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 6px 20px rgba(0,0,0,0.15);
  border: 1px solid #e5e7eb;
  z-index: 20000;
  padding: 8px;
  max-height: 240px;
  overflow-y: auto;
}
.control-dropdown ul { list-style: none; margin: 0; padding: 0; }
.control-dropdown li { color: #4b5563; padding: 8px 10px; border-radius: 8px; cursor: pointer; }
.control-dropdown li:hover { background: #f3f4f6; }
.control-dropdown li.selected { font-weight: 600; color: #111827; }
/* 主体网格容器：用于形成与主体边界的留白以及卡片间隙 */
.grid-layout {
  display: grid;
  gap: var(--grid-gap, 24px);
  padding: var(--grid-padding, 24px);
}

/* 统一白色圆角卡片样式（参考 v0.html 的 .card） */
.card {
  background: #ffffff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 6px 16px rgba(15, 181, 174, 0.25);
  overflow: hidden;
}

.echarts-tooltip { font-size: 12px; }

/* 强制雷达叠加下拉浮层为纯白不透明（避免被外部样式影响） */
.radar-select-panel,
.fixed.z-\[20000\] {
  background-color: #ffffff !important;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15) !important;
  border-radius: 12px !important;
  border: 1px solid #e5e7eb !important;
  /* 让容器按内联的 overflowX/overflowY 控制滚动，不再强制 visible */
  max-width: calc(100vw - (12px + 24px) * 2);
}
</style>
