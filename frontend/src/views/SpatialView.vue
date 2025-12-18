<template>
  <div class="space-y-5">
    <!-- 标题与控制栏 -->
    <div class="flex items-center justify-between section-header">
      <h2 class="page-title text-2xl font-bold">空间识别分析</h2>
      <!-- 年份选择按钮（主题色圆角、白色加粗文字；悬浮下拉不影响布局） -->
      <div class="relative mr-6">
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

    <!-- 错误提示与重试 -->
    <div v-if="loadError" class="bg-yellow-50 border border-yellow-200 text-yellow-700 rounded-xl px-4 py-2 flex items-center justify-between">
      <span>数据加载异常：{{ loadError }}</span>
      <button @click="retryLoad" class="text-sm bg-yellow-600 text-white px-3 py-1 rounded">重试</button>
    </div>

    <!-- 图表网格布局（三地图 + 散点 + 信息板块） -->
    <!-- 使用 CSS 变量控制行高/间距/容器内边距：--row-unit（默认 320px）、--grid-gap（默认 24px）、--grid-padding（默认 24px） -->
    <!-- --row-unit ：单行高度基准（默认 320px ，控制2/3与1/3的高度）；--grid-gap ：卡片之间的间隙（默认 24px ）；--grid-padding ：容器与边界的留白（默认 24px ）；grid-template-rows：每行高度；grid-template-columns：每列宽度 -->
    <div class="grid-layout" style="--row-unit: 320px; --grid-gap: 24px; --grid-padding: 24px; grid-template-columns: 1fr 1fr 1fr; grid-template-rows: repeat(3, var(--row-unit)); grid-template-areas: 'emission emission energy' 'emission emission green' 'scatter scatter info';">
      <!-- 左上（2/3宽 × 2/3高）：省级碳排放热力图 → emission -->
      <div class="card flex flex-col" style="grid-area: emission">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-lg font-semibold text-gray-700">各省碳排放总量</h3>
<div class="text-xs text-gray-500">单位：吨 CO₂</div>
        </div>
        <div ref="mapEmissionRef" class="w-full flex-1" style="min-height:0"></div>
      </div>

      <!-- 右上（1/3宽 × 1/3高）：清洁能源比例分层图 → energy -->
      <div class="card flex flex-col" style="grid-area: energy">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-lg font-semibold text-gray-700">清洁能源占比</h3>
          <div class="text-xs text-gray-500">单位：%</div>
        </div>
        <div ref="mapEnergyRef" class="w-full flex-1" style="min-height:0"></div>
      </div>

      <!-- 右中（1/3宽 × 1/3高）：建成区绿化覆盖率 → green -->
      <div class="card flex flex-col" style="grid-area: green">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-lg font-semibold text-gray-700">建成区绿化覆盖率</h3>
          <div class="text-xs text-gray-500">单位：%</div>
        </div>
        <div ref="mapGreenRef" class="w-full flex-1" style="min-height:0"></div>
      </div>

      <!-- 左下（2/3宽 × 1/3高）：联合柱状图 → scatter -->
      <div class="card flex flex-col" style="grid-area: scatter">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-lg font-semibold text-gray-700">联合柱状图</h3>
<div class="text-xs text-gray-500">X：省份；Y：Z-Score（碳排放取负）</div>
        </div>
        <div ref="scatterRef" class="w-full flex-1" style="min-height:0"></div>
      </div>

      <!-- 右下（1/3宽 × 1/3高）：信息展示板块 → info -->
      <div class="card" style="grid-area: info">
        <h3 class="text-xl font-semibold text-gray-700 mb-2">信息展示</h3>
        <div v-if="selectedProvince" class="text-base text-gray-700 space-y-1">
          <div>省份：{{ selectedProvince }}</div>
          <div>年份：{{ selectedYear }}</div>
          <div>碳排放总量：{{ currentStats?.emission_total ?? '—' }}</div>
          <div>清洁能源占比：{{ percent((currentStats?.clean_ratio ?? 0) * 100) }}</div>
          <div>建成区绿化覆盖率：{{ percent((currentStats?.green_rate ?? 0) * 100) }}</div>
        </div>
        <div v-else class="text-base text-gray-500">点击任一图表选择省份以查看详细信息。</div>
      </div>
    </div>
  </div>
  
</template>

<script setup lang="ts">
// ——————————————————————————————————————————————
// 空间识别分析（模块一）主视图
// 功能：加载后端 /api/emission 数据，绘制中国省份地图的碳排放总量热力图
//       可叠加清洁能源分层与绿化纹理图层；右侧展示散点并拟合线；
//       支持人机交互：悬停提示、点击省份高亮、图层开关联动、年份切换。
// ——————————————————————————————————————————————

import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'

// ===================== 类型定义 =====================
type ProvinceRecord = {
  province: string
  year: number
  clean_ratio?: number
  green_rate?: number
  emission_total?: number
}

// 新数据源类型（分别来自三个 CSV）
type EmissionRecord = { province: string; geoName: string; year: number; emission_total: number }
type EnergyRecord = { province: string; geoName: string; year: number; clean_ratio: number }
type GreenRecord = { province: string; geoName: string; year: number; green_rate: number }

// ===================== 状态与引用 =====================
const mapEmissionRef = ref<HTMLDivElement | null>(null)
const mapEnergyRef = ref<HTMLDivElement | null>(null)
const mapGreenRef = ref<HTMLDivElement | null>(null)
const scatterRef = ref<HTMLDivElement | null>(null)
let mapEmissionChart: echarts.ECharts | null = null
let mapEnergyChart: echarts.ECharts | null = null
let mapGreenChart: echarts.ECharts | null = null
let scatterChart: echarts.ECharts | null = null
// 柱状图分类（省份顺序）用于跨图高亮
let barCategories: string[] = []

// 年份选项（固定 2005–2022，加载后与数据求交集）
const yearOptions = ref<number[]>(Array.from({ length: 18 }, (_, i) => 2005 + i))
const selectedYear = ref<number>(2022)

// 顶部年份下拉逻辑（悬浮白色圆角面板，不影响布局）
const showYearDropdown = ref(false)
const yearButtonRef = ref<HTMLElement|null>(null)
const yearDropdownRef = ref<HTMLElement|null>(null)
function toggleYearDropdown() {
  showYearDropdown.value = !showYearDropdown.value
}
function chooseYear(y: number) {
  selectedYear.value = y
  showYearDropdown.value = false
}
function handleClickOutside(e: MouseEvent) {
  const btn = yearButtonRef.value
  const panel = yearDropdownRef.value
  const target = e.target as Node
  if (showYearDropdown.value && btn && panel && !btn.contains(target) && !panel.contains(target)) {
    showYearDropdown.value = false
  }
}

// 后端数据缓存（分三源）
const emissionRecords = ref<EmissionRecord[]>([])
const energyRecords = ref<EnergyRecord[]>([])
const greenRecords = ref<GreenRecord[]>([])
const chinaGeoJson = ref<any>(null)
const loadError = ref<string>('')
const loading = ref<boolean>(false)

// 选中省份联动
const selectedProvince = ref<string>('')
const currentStats = computed(() => {
  if (!selectedProvince.value) return undefined
  const y = selectedYear.value
  const p = selectedProvince.value
  const e = emissionRecords.value.find((d) => d.geoName === p && d.year === y)
  const c = energyRecords.value.find((d) => d.geoName === p && d.year === y)
  const g = greenRecords.value.find((d) => d.geoName === p && d.year === y)
  if (!e && !c && !g) return undefined
  return {
    province: p,
    year: y,
    emission_total: e?.emission_total,
    clean_ratio: c?.clean_ratio,
    green_rate: g?.green_rate,
  }
})

// ===================== 工具函数 =====================
/**
 * 将值映射为百分号字符串（保留一位小数）。
 */
const percentFilter = (value?: number | null) => `${Number(value ?? 0).toFixed(1)}%`

/**
 * 规范化省份名称为 ECharts 地图中的行政区名字
 * 例如："北京"→"北京市"，"内蒙"/"内蒙古"→"内蒙古自治区"，"广西"/"广西壮族"→"广西壮族自治区"
 */
function normalizeProvinceName(src: string): string {
  const s = String(src || '').trim()
  const map: Record<string, string> = {
    '北京': '北京市', '北京市': '北京市',
    '上海': '上海市', '上海市': '上海市',
    '天津': '天津市', '天津市': '天津市',
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

/**
 * 简单线性回归（最小二乘）返回 [slope, intercept]
 */
function linearRegression(xs: number[], ys: number[]): [number, number] {
  const n = Math.min(xs.length, ys.length)
  if (n === 0) return [0, 0]
  const X = xs.slice(0, n)
  const Y = ys.slice(0, n)
  const meanX = X.reduce((a, b) => a + b, 0) / n
  const meanY = Y.reduce((a, b) => a + b, 0) / n
  let num = 0
  let den = 0
  for (let i = 0; i < n; i++) {
    const xi = X[i] ?? 0
    const yi = Y[i] ?? 0
    num += (xi - meanX) * (yi - meanY)
    den += (xi - meanX) * (xi - meanX)
  }
  const slope = den === 0 ? 0 : num / den
  const intercept = meanY - slope * meanX
  return [slope, intercept]
}

/**
 * 生成斜线纹理 Pattern，用于绿化覆盖率的“纹理分层图”（按密度映射）。
 * 通过改变线条间距控制密度，返回 HTMLCanvasElement 作为图案。
 */
function makeStripePattern(value: number, min: number, max: number, color = '#2ecc71') {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')!
  const size = 32
  canvas.width = size
  canvas.height = size
  // 将值映射到密度（间距越小密度越大）
  const t = Math.max(min, Math.min(max, value))
  const ratio = (t - min) / (max - min + 1e-9)
  const spacing = 6 - Math.round(ratio * 4) // 2–6 像素间距
  ctx.clearRect(0, 0, size, size)
  ctx.strokeStyle = color
  ctx.lineWidth = 1
  ctx.globalAlpha = 0.35
  for (let i = -size; i < size * 2; i += spacing) {
    ctx.beginPath()
    ctx.moveTo(i, 0)
    ctx.lineTo(i + size, size)
    ctx.stroke()
  }
  return canvas
}

// ===================== 数据加载 =====================
/**
 * 加载后端三数据源（emission_total、clean_ratio、green_rate）。
 * 路径：/api/province → backend/data/processed/province_combined.csv
 */
async function loadProvinceData() {
  loading.value = true
  loadError.value = ''
  const base = (import.meta as any)?.env?.VITE_API_BASE_URL?.replace(/\/$/, '')
  const build = (path: string) => [
    base ? `${base}${path}` : '',
    `http://127.0.0.1:5000${path}`,
    path,
  ].filter(Boolean)

  let okCount = 0
  // emission_total
  for (const url of build('/api/emission')) {
    try {
      const res = await axios.get<EmissionRecord[]>(url)
      emissionRecords.value = (res.data || []).map((d: any) => ({
        province: String(d.province),
        geoName: normalizeProvinceName(String(d.province)),
        year: Number(d.year),
        emission_total: Number(d.emission_total),
      }))
      okCount++; break
    } catch {}
  }
  // clean_ratio
  for (const url of build('/api/energy')) {
    try {
      const res = await axios.get<EnergyRecord[]>(url)
      energyRecords.value = (res.data || []).map((d: any) => ({
        province: String(d.province),
        geoName: normalizeProvinceName(String(d.province)),
        year: Number(d.year),
        clean_ratio: Number(d.clean_ratio),
      }))
      okCount++; break
    } catch {}
  }
  // green_rate
  for (const url of build('/api/green')) {
    try {
      const res = await axios.get<GreenRecord[]>(url)
      greenRecords.value = (res.data || []).map((d: any) => ({
        province: String(d.province),
        geoName: normalizeProvinceName(String(d.province)),
        year: Number(d.year),
        green_rate: d.green_rate != null ? Number(d.green_rate) : undefined,
      })) as any
      okCount++; break
    } catch {}
  }

  if (okCount < 3) {
    loadError.value = '部分数据源加载失败，请确认 Flask 已提供 /api/emission /api/energy /api/green。'
  }

  // 年份范围：三源的交集（2005–2022 之间）
  const yearsE = new Set(emissionRecords.value.map((d) => d.year))
  const yearsC = new Set(energyRecords.value.map((d) => d.year))
  const yearsG = new Set(greenRecords.value.map((d) => d.year))
  const allYears = Array.from(new Set([...yearsE, ...yearsC, ...yearsG])).sort((a, b) => a - b)
  const allowed = Array.from({ length: 20 }, (_, i) => 2003 + i) // 数据源范围更广
  const inter = allYears.filter((y) => allowed.includes(y))
  yearOptions.value = inter.length ? inter : allowed
  selectedYear.value = yearOptions.value.includes(2022)
    ? 2022
    : (yearOptions.value[yearOptions.value.length - 1]!)
  loading.value = false
}

/**
 * 加载中国省级 GeoJSON（来自阿里云数据服务）。
 * 说明：这是行政边界数据，不属于指标数据，不算“写死数据”。
 */
async function loadChinaGeo() {
  try {
    // 使用 v3 全量省界（包含省份名与编码）
    const url = 'https://geo.datav.aliyun.com/areas_v3/bound/geojson?code=100000_full'
    const res = await axios.get(url)
    chinaGeoJson.value = res.data
    echarts.registerMap('china', chinaGeoJson.value)
  } catch (e: any) {
    loadError.value = '地图边界数据加载失败，请检查网络连接。'
  }
}

// ===================== 取数与渲染 =====================
/**
 * 构建分层视觉映射（右下角，piecewise）
 */
function buildPiecewise(min: number, max: number, colors: string[], unitLabel?: string) {
  if (!isFinite(min) || !isFinite(max) || min === max) {
    min = 0; max = min + 1
  }
  const splitNumber = Math.max(3, Math.min(7, colors.length))
  return {
    type: 'piecewise',
    min,
    max,
    splitNumber,
    inRange: { color: colors },
    right: 20,
    bottom: 20,
    text: unitLabel ? [unitLabel, ''] : undefined,
    itemWidth: 12,
    itemHeight: 8,
    orient: 'vertical',
  }
}
function getDataForYear(year: number) {
  const rowsE = emissionRecords.value.filter((d) => d.year === year)
  const rowsC = energyRecords.value.filter((d) => d.year === year)
  const rowsG = greenRecords.value.filter((d) => d.year === year)
  // 按省份合并三源（同一年）
  const byProv: Record<string, { province: string; geoName: string; emission_total?: number; clean_ratio?: number; green_rate?: number }> = {}
  rowsE.forEach((d) => { const p = d.geoName; byProv[p] = byProv[p] || { province: d.province, geoName: p }; byProv[p].emission_total = d.emission_total })
  rowsC.forEach((d) => { const p = d.geoName; byProv[p] = byProv[p] || { province: d.province, geoName: p }; byProv[p].clean_ratio = d.clean_ratio })
  rowsG.forEach((d) => { const p = d.geoName; byProv[p] = byProv[p] || { province: d.province, geoName: p }; byProv[p].green_rate = d.green_rate })
  const rows = Object.values(byProv)
  const carbon = rows.map((d) => d.emission_total ?? 0).filter((v) => v > 0)
  const energy = rows.map((d) => d.clean_ratio ?? 0).filter((v) => v > 0)
  const green = rows.map((d) => d.green_rate ?? 0).filter((v) => v > 0)
  const minMax = (arr: number[]) => ({ min: Math.min(...arr), max: Math.max(...arr) })
  return {
    rows,
    carbonMM: carbon.length ? minMax(carbon) : { min: 0, max: 1 },
    energyMM: energy.length ? minMax(energy) : { min: 0, max: 1 },
    greenMM: green.length ? minMax(green) : { min: 0, max: 1 },
  }
}

/**
 * 渲染三张独立地图，并支持点击联动为黄色高亮
 */
function renderMapEmission() {
  if (!mapEmissionRef.value || !chinaGeoJson.value) return
  if (mapEmissionChart) mapEmissionChart.dispose()
  mapEmissionChart = echarts.init(mapEmissionRef.value)

  const { rows, carbonMM } = getDataForYear(selectedYear.value)
  const mapData = rows.map((d) => ({ name: d.geoName, value: d.emission_total ?? undefined }))

  mapEmissionChart.setOption({
    tooltip: {
      trigger: 'item',
      show: true,
      confine: true,
      formatter: (p: any) => {
        const name = p.name
        const row = rows.find((d) => d.geoName === name)
        const val = row?.emission_total ?? (Array.isArray(p.value) ? p.value[2] : p.value)
        const emis = val != null && isFinite(Number(val)) ? Number(val).toFixed(2) : '—'
        return `${name}<br/>碳排放总量：${emis}`
      },
    },
    // 仅使用 series.map 绘制一张固定的地图（不再重复 geo+map）
    visualMap: buildPiecewise(carbonMM.min, carbonMM.max, ['#4B9EFF','#7B61FF','#9B59B6','#D14A61','#E74C3C'], '吨 CO₂'),
    series: [{
 type: 'map', map: 'china', name: '碳排放总量', roam: false, zoom: 1.24,
      itemStyle: { borderColor: '#ffffff', borderWidth: 0.8 },
      emphasis: { itemStyle: { areaColor: '#f2c94c', borderColor: '#d97706', borderWidth: 1.5 } },
      data: mapData
    }],
  })

  mapEmissionChart.off('click')
  mapEmissionChart.on('click', (p: any) => { if (p?.name) linkageSelect(p.name) })
}

function renderMapEnergy() {
  if (!mapEnergyRef.value || !chinaGeoJson.value) return
  if (mapEnergyChart) mapEnergyChart.dispose()
  mapEnergyChart = echarts.init(mapEnergyRef.value)

  const { rows, energyMM } = getDataForYear(selectedYear.value)
  const mapData = rows.map((d) => ({ name: d.geoName, value: (d.clean_ratio ?? undefined) != null ? Number(d.clean_ratio) * 100 : undefined }))

  mapEnergyChart.setOption({
    tooltip: {
      trigger: 'item',
      show: true,
      confine: true,
      formatter: (p: any) => {
        const name = p.name
        const row = rows.find((d) => d.geoName === name)
        const val = row?.clean_ratio != null ? percentFilter(Number(row.clean_ratio) * 100) : '—'
        return `${name}<br/>清洁能源比例：${val}`
      },
    },
    // 仅 series.map，不再叠加 geo
    visualMap: buildPiecewise(energyMM.min * 100, energyMM.max * 100, ['#dbeafe','#93c5fd','#3b82f6','#1d4ed8','#1e3a8a'], '%'),
    series: [{
      type: 'map', map: 'china', name: '清洁能源比例', roam: false, zoom: 1.24,
      itemStyle: { borderColor: '#ffffff', borderWidth: 0.6 },
      emphasis: { itemStyle: { areaColor: '#f2c94c', borderColor: '#d97706', borderWidth: 1.5 } },
      data: mapData
    }],
  })

  mapEnergyChart.off('click')
  mapEnergyChart.on('click', (p: any) => { if (p?.name) linkageSelect(p.name) })
}

function renderMapGreen() {
  if (!mapGreenRef.value || !chinaGeoJson.value) return
  if (mapGreenChart) mapGreenChart.dispose()
  mapGreenChart = echarts.init(mapGreenRef.value)

  const { rows, greenMM } = getDataForYear(selectedYear.value)
  const mapData = rows.map((d) => ({ name: d.geoName, value: (d.green_rate ?? undefined) != null ? Number(d.green_rate) * 100 : undefined }))

  mapGreenChart.setOption({
    tooltip: {
      trigger: 'item',
      show: true,
      confine: true,
      formatter: (p: any) => {
        const name = p.name
        const row = rows.find((d) => d.geoName === name)
        const val = row?.green_rate != null ? percentFilter(Number(row.green_rate) * 100) : '—'
        return `${name}<br/>绿化率：${val}`
      },
    },
    // 仅 series.map，不再叠加 geo
    visualMap: buildPiecewise(greenMM.min * 100, greenMM.max * 100, ['#dcfce7','#86efac','#34d399','#065f46','#064e3b'], '%'),
    series: [{
      type: 'map', map: 'china', name: '绿化率', roam: false, zoom: 1.24,
      itemStyle: { borderColor: '#ffffff', borderWidth: 0.6 },
      emphasis: { itemStyle: { areaColor: '#f2c94c', borderColor: '#d97706', borderWidth: 1.5 } },
      data: mapData
    }],
  })

  mapGreenChart.off('click')
  mapGreenChart.on('click', (p: any) => { if (p?.name) linkageSelect(p.name) })
}

function setMapSelection(name: string) {
  const charts = [mapEmissionChart, mapEnergyChart, mapGreenChart]
  charts.forEach((c) => {
    try {
      c?.dispatchAction({ type: 'downplay' })
      c?.dispatchAction({ type: 'highlight', name })
    } catch {}
  })
}

function linkageSelect(name: string) {
  selectedProvince.value = name
  setMapSelection(name)
  highlightPointOnScatter(name)
}

/**
 * 渲染散点图（清洁能源 vs 碳排放总量，拟合线用于相关性验证）
 */
function renderScatter() {
  if (!scatterRef.value) return
  if (scatterChart) scatterChart.dispose()
  scatterChart = echarts.init(scatterRef.value)

  // 联合柱状图（Z-Score，分组发散柱）
  const { rows } = getDataForYear(selectedYear.value)
  // 只保留省份与三指标均有效的记录，保证索引对齐与类型稳定
  const validRows = rows.filter(
    (d) => d.geoName && d.emission_total != null && d.clean_ratio != null && d.green_rate != null,
  )
  const provinces: string[] = validRows.map((d) => String(d.geoName))
  const valuesE: number[] = validRows.map((d) => Number(d.emission_total))
  const valuesC: number[] = validRows.map((d) => Number(d.clean_ratio))
  const valuesG: number[] = validRows.map((d) => Number(d.green_rate))

  const z = (arr: number[]) => {
    const n = arr.length
    const mean = arr.reduce((a, b) => a + b, 0) / (n || 1)
    const sd = Math.sqrt(arr.reduce((s, v) => s + Math.pow(v - mean, 2), 0) / (n || 1)) || 1
    return arr.map((v) => (v - mean) / sd)
  }
  const zE = z(valuesE)
  const zC = z(valuesC)
  const zG = z(valuesG)

  // 协同指数排序（C' + G' - E'）
  const synergy = provinces.map((_, i) => (zC[i] ?? 0) + (zG[i] ?? 0) - (zE[i] ?? 0))
  const order = synergy
    .map((v, i) => ({ v, i }))
    .sort((a, b) => b.v - a.v)
    .map((o) => o.i)

  const orderedProv: string[] = order.map((i) => provinces[i]!)
  const categories: string[] = orderedProv.map((n) => n ?? '')
  barCategories = categories
  const dataE = order.map((i) => -Number(zE[i] ?? 0)) // 取负号显示（越高越好）
  const dataC = order.map((i) => Number(zC[i] ?? 0))
  const dataG = order.map((i) => Number(zG[i] ?? 0))

  const median = [...synergy].sort((a, b) => a - b)[Math.floor(synergy.length / 2)]
  const q1 = [...synergy].sort((a, b) => a - b)[Math.floor(synergy.length / 4)]
  const q3 = [...synergy].sort((a, b) => a - b)[Math.floor((3 * synergy.length) / 4)]

  scatterChart.setOption({
    grid: { left: 40, right: 30, top: 40, bottom: 60 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (p: any) => {
        const idx0 = Array.isArray(p) && p[0]?.dataIndex != null ? Number(p[0].dataIndex) : 0
        const idx = Math.max(0, Math.min(idx0, categories.length - 1))
        const name = categories[idx] ?? ''
        const valC = Number(dataC[idx] ?? 0)
        const valG = Number(dataG[idx] ?? 0)
        const valE = Number(dataE[idx] ?? 0)
        return `${name}<br/>清洁能源z：${valC.toFixed(2)}<br/>绿化率z：${valG.toFixed(2)}<br/>碳排放(-z)：${valE.toFixed(2)}`
      },
    },
    xAxis: { type: 'category', data: categories, axisLabel: { rotate: 45, color: '#555' } },
    yAxis: { type: 'value', name: 'Z-Score', axisLabel: { color: '#555' } },
    series: [
      { type: 'bar', name: '清洁能源', data: dataC, itemStyle: { color: '#3b82f6' }, emphasis: { itemStyle: { borderColor: '#f2c94c', borderWidth: 2 } } },
      { type: 'bar', name: '绿化率', data: dataG, itemStyle: { color: '#10b981' }, emphasis: { itemStyle: { borderColor: '#f2c94c', borderWidth: 2 } } },
      { type: 'bar', name: '碳排放(-z)', data: dataE, itemStyle: { color: '#fb923c' }, emphasis: { itemStyle: { borderColor: '#f2c94c', borderWidth: 2 } },
        markLine: {
          symbol: 'none',
          data: [
            { yAxis: median, name: '中位数' },
            { yAxis: q1, name: 'Q1' },
            { yAxis: q3, name: 'Q3' },
          ],
          lineStyle: { color: '#94a3b8', type: 'dashed' },
          label: { formatter: '{b}', color: '#64748b' },
        },
      },
    ],
    legend: { top: 8, right: 8 },
    // 参考线：协同指数的四分位与中位数
    graphic: [
      { type: 'line', left: 40, right: 30, top: 40, shape: { x1: 0, y1: 0, x2: 0, y2: 0 } },
    ],
    markLine: {
      silent: true,
    },
  })

  // 点击柱 → 联动地图高亮
  scatterChart.off('click')
  scatterChart.on('click', (p: any) => {
    const idx = p?.dataIndex
    const name = orderedProv[idx || 0]
    if (name) linkageSelect(name)
  })
}

/**
 * 在散点中高亮指定省份（使用 dispatchAction）
 */
function highlightPointOnScatter(name: string) {
  if (!scatterChart) return
  try {
    const index = barCategories.indexOf(name)
    if (index >= 0) {
      // 取消所有系列的选中，再选中该索引处三根柱
      for (let si = 0; si < 3; si++) {
        scatterChart.dispatchAction({ type: 'downplay', seriesIndex: si })
        scatterChart.dispatchAction({ type: 'highlight', seriesIndex: si, dataIndex: index })
      }
    }
  } catch {}
}

// ===================== 生命周期与监听 =====================
onMounted(async () => {
  // 1) 拉取数据与地图
  await Promise.all([loadProvinceData(), loadChinaGeo()])
  // 2) 初次渲染
  renderMapEmission()
  renderMapEnergy()
  renderMapGreen()
  renderScatter()
  // 3) 监听窗口变化
  window.addEventListener('resize', handleResize)
  // 关闭年份下拉的外部点击监听
  document.addEventListener('mousedown', handleClickOutside)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (mapEmissionChart) mapEmissionChart.dispose()
  if (mapEnergyChart) mapEnergyChart.dispose()
  if (mapGreenChart) mapGreenChart.dispose()
  if (scatterChart) scatterChart.dispose()
  document.removeEventListener('mousedown', handleClickOutside)
})

function handleResize() {
  mapEmissionChart?.resize()
  mapEnergyChart?.resize()
  mapGreenChart?.resize()
  scatterChart?.resize()
}

// 年份变动 → 重绘
watch(selectedYear, () => {
  renderMapEmission()
  renderMapEnergy()
  renderMapGreen()
  renderScatter()
  if (selectedProvince.value) {
    setMapSelection(selectedProvince.value)
    highlightPointOnScatter(selectedProvince.value)
  }
})

// 提供给模板调用
const percent = percentFilter

function retryLoad() {
  loadProvinceData().then(() => {
    renderMapEmission()
    renderMapEnergy()
    renderMapGreen()
    renderScatter()
  })
}
</script>

<style scoped>
/* 页面标题统一左侧间距与颜色（略深的绿色） */
.page-title {
  margin-left: var(--title-left-gap, 28px);
  color: var(--primary-dark, #179299);
}
/* 顶部容器：与主体右边界保持统一留白 */
.section-header {
  padding-right: var(--grid-padding, 24px);
}
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
  min-width: 140px; /* 比按钮略宽 */
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
/* 卡片圆角与阴影已通过 Tailwind 类实现。此处针对地图内元素做少量微调。 */
.echarts-tooltip {
  font-size: 12px;
}

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
  overflow: hidden; /* 裁剪内部图表，保证圆角可见 */
}
</style>