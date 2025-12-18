<template>
  <!-- 顶部模块标题与统一控件行 -->
  <div class="section-header">
    <h2 class="section-title">时序演化分析</h2>
    <div class="section-controls">
      <!-- 年份滑轨（顶部统一控制） -->
      <el-slider
        v-model="yearRange"
        range
        :min="minYear"
        :max="maxYear"
        :step="1"
        show-tooltip
        style="width: 200px"
      />
      <!-- 省份选择（顶部统一控制） -->
      <el-select
        v-model="selectedProvinces"
        multiple
        :multiple-limit="4"
        fit-input-width
        placeholder="选择省份"
        class="compact-select"
        popper-class="compact-select-dropdown"
        style="width: 310px"
      >
        <el-option v-for="province in provinces" :key="province" :label="province" :value="province" />
      </el-select>
    </div>
  </div>

  <div class="grid-layout" style="--grid-gap: 24px; --grid-padding: 24px; grid-template-rows: 2fr 1fr; grid-template-areas: 'trend trend' 'delta timeline';">
    <!-- 趋势图 -->
    <div class="card" style="grid-area: trend;">
      <card-title title="三指标时间趋势图">
        <!-- 控件靠右并留白，提示位于按钮左侧 -->
        <div class="controls-row trend-controls">
          <el-tag v-if="axisMode==='single'" type="warning" effect="plain">已归一化展示</el-tag>
          <!-- 轴模式切换：双轴/同轴(归一化) -->
          <el-radio-group v-model="axisMode" size="small">
            <el-radio-button label="dual">双轴</el-radio-button>
            <el-radio-button label="single">同轴(归一化)</el-radio-button>
          </el-radio-group>
          <!-- 平滑模式 -->
          <el-select v-model="smoothMode" placeholder="平滑模式" style="width: 160px">
            <el-option label="不平滑" value="none" />
            <el-option label="3年滚动均值" value="moving_average" />
          </el-select>
          <el-button :icon="Download" circle @click="downloadTrendData" />
        </div>
      </card-title>
      <div ref="trendChartRef" class="chart-container"></div>
    </div>

    <!-- 年度变化速率 -->
    <div class="card" style="grid-area: delta;">
      <card-title title="年度变化速率">
        <div class="flex items-center space-x-4">
          <!-- 当选择“所有指标”时，左侧显示单选省份/全国选择框，并联动其他图表 -->
          <el-select v-if="selectedDeltaIndicator==='all'" v-model="singleDeltaProvince" placeholder="选择地区" style="width: 120px">
            <el-option v-for="province in provinces" :key="province" :label="province" :value="province" />
          </el-select>
          <el-select v-model="selectedDeltaIndicator" placeholder="选择指标" style="width: 120px">
            <el-option label="所有指标" value="all" />
            <el-option label="清洁能源占比变化" value="Δenergy" />
            <el-option label="绿化覆盖率变化" value="Δgreen" />
            <el-option label="单位GDP排放变化" value="Δemission" />
          </el-select>
        </div>
      </card-title>
      <div class="chart-container">
        <TemporalDeltaChart :chart-data="filteredDeltaData" :indicator="selectedDeltaIndicator" :hovered-year="hoveredYear" />
      </div>
    </div>

    <!-- 政策事件时间线 -->
    <div class="card" style="grid-area: timeline;">
      <card-title title="政策事件时间线">
        <div class="controls-row">
          <!-- 地区单选（仅控制政策事件时间线） -->
          <el-select v-model="timelineProvince" placeholder="选择地区" style="width: 120px">
            <el-option label="全国" value="全国" />
            <el-option v-for="province in provinces" :key="province" :label="province" :value="province" />
          </el-select>
          <!-- 年份滑轨（仅控制政策事件时间线） -->
          <el-slider
            v-model="timelineYearRange"
            range
            :min="minYear"
            :max="maxYear"
            :step="1"
            show-tooltip
            style="width: 180px"
          />
        </div>
      </card-title>
      <div class="chart-container">
        <TemporalTimelineChart :provinces="timelineProvinces" :year-range="timelineYearRange" @hover-year="onTimelineHover" @hover-clear="onTimelineHoverClear" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick, computed } from 'vue';
import * as echarts from 'echarts';
import axios from 'axios';
import { Download } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import CardTitle from '@/components/CardTitle.vue';
import TemporalDeltaChart from '@/components/TemporalDeltaChart.vue';
import TemporalTimelineChart from '@/components/TemporalTimelineChart.vue';

// --- Types ---
interface TrendRow {
  province: string;
  year: number;
  clean_ratio: number | null;
  green_rate: number | null;
  emission_per_gdp: number | null;
}

interface DeltaRow {
  province: string;
  year: number;
  'Δenergy': number | null;
  'Δgreen': number | null;
  'Δemission': number | null;
}

// Chart-related refs
const trendChartRef = ref<HTMLDivElement | null>(null);
let trendChartInstance: echarts.ECharts | null = null;

// State
const axisMode = ref<'dual' | 'single'>('dual');
const smoothMode = ref<'none' | 'moving_average' | 'sgolay3'>('none');
const selectedProvinces = ref<string[]>(['全国']);
const selectedDeltaIndicator = ref<'all' | 'Δenergy' | 'Δgreen' | 'Δemission'>('all');
// “所有指标”模式的单选地区（联动控制其他图表）
const singleDeltaProvince = ref<string>('全国');
const selectedProvince = computed<string>(() => selectedProvinces.value[0] || '全国');
const hoveredYear = ref<number | null>(null);
const yearRange = ref<[number, number]>([2005, 2022]);
// 政策事件时间线独立年份滑轨
const timelineYearRange = ref<[number, number]>([2005, 2022]);
// 政策事件时间线独立地区选择（仅全国或单省）
const timelineProvince = ref<string>('全国');
const timelineProvinces = computed<string[]>(() => {
  const p = timelineProvince.value || '全国';
  if (p === '全国') return ['全国'];
  // 同时显示全国与所选省份的事件
  return ['全国', p];
});
const trendData = ref<TrendRow[]>([]);
const deltaData = ref<DeltaRow[]>([]);
const provinces = ref<string[]>([]);
// 顶部年份滑轨范围
const minYear = computed<number>(() => trendData.value.length ? Math.min(...trendData.value.map(d => d.year)) : 2005);
const maxYear = computed<number>(() => trendData.value.length ? Math.max(...trendData.value.map(d => d.year)) : 2022);


const IMPUTED_YEARS: number[] = [2020, 2021, 2022];
const colors: Record<'energy' | 'green' | 'emission', string> = {
  energy: '#10b981',
  green: '#3b82f6',
  emission: '#f97316'
};
// 全国政策事件竖线锚点
const nationalPolicyYears = ref<number[]>([]);

// 限制最多显示6省
const limitedProvinces = computed<string[]>(() => {
  if (selectedProvinces.value.length > 6) {
    ElMessage.warning('最多显示6条折线，已自动限制并建议切换显示模式');
    return selectedProvinces.value.slice(0, 6);
  }
  return selectedProvinces.value;
});

// --- Data Loading and Processing ---

const normalizeProvinceName = (name: string): string => {
  if (!name) return '';
  // 统一到“无后缀的标准省名”，同时把数据源中的缩写映射为全称
  const map: Record<string, string> = {
    // 带后缀 → 标准名
    '北京市': '北京', '天津市': '天津', '上海市': '上海', '重庆市': '重庆',
    '内蒙古自治区': '内蒙古', '广西壮族自治区': '广西', '西藏自治区': '西藏',
    '宁夏回族自治区': '宁夏', '新疆维吾尔自治区': '新疆',
    // 常见缩写 → 标准名（与 policy_timeline.csv 保持一致）
    '内蒙': '内蒙古',
    '黑龙': '黑龙江',
    '广西壮族': '广西',
    '新疆维吾尔': '新疆',
  };
  const trimmed = String(name).trim();
  if (map[trimmed]) return map[trimmed];
  // 去除后缀后的标准化
  return trimmed.replace(/省|市|自治区|回族|维吾尔/g, '');
};

const loadData = async () => {
  try {
    const [trendResponse, deltaResponse] = await Promise.all([
      axios.get('/api/temporal/trend'),
      axios.get('/api/temporal/delta')
    ]);

    if (trendResponse.status !== 200) throw new Error('Failed to fetch trend data');
    if (deltaResponse.status !== 200) throw new Error('Failed to fetch delta data');

    const parsedTrendData = trendResponse.data as TrendRow[];
    deltaData.value = deltaResponse.data as DeltaRow[];

    const provinceSet = new Set(parsedTrendData.map(item => normalizeProvinceName(item.province)));
    provinces.value = ['全国', ...Array.from(provinceSet).sort()];
    
    trendData.value = parsedTrendData;
    // 默认显示全国（由 selectedProvince 计算得出）
    
    await nextTick();
    renderTrendChart();

  } catch (error) {
    console.error("Error loading data:", error);
  }
};

// 联动：当“所有指标”模式下选择单选地区时，统一控制顶部省份选择（限制为一个）
watch(singleDeltaProvince, (p: string) => {
  if (selectedDeltaIndicator.value === 'all') {
    selectedProvinces.value = [p];
  }
});

// 切换到“所有指标”时，用当前单选地区统一限定顶部选择为一个
watch(selectedDeltaIndicator, (ind) => {
  if (ind === 'all') {
    selectedProvinces.value = [singleDeltaProvince.value];
  }
});

// 加载全国政策事件年份（用于趋势图竖线锚点）
const loadNationalPolicyYears = async (): Promise<void> => {
  try {
    const resp = await axios.get('/api/policy');
    if (resp.status === 200) {
      const items = resp.data as Array<{ province: string; year: number }>; 
      const years: number[] = items
        .filter((d) => d.province === '中国')
        .map((d) => d.year);
      nationalPolicyYears.value = Array.from(new Set(years)).sort((a, b) => a - b);
    }
  } catch (e) {
    console.warn('加载全国政策事件失败:', e);
  }
};

const filteredDeltaData = computed<any[]>(() => {
  if (!deltaData.value.length) return [] as any[];

  const data: DeltaRow[] = deltaData.value.map((d: DeltaRow) => ({
    ...d,
    province: normalizeProvinceName(d.province)
  }));

  const inRangeData: DeltaRow[] = data.filter((d: DeltaRow) => d.year >= yearRange.value[0] && d.year <= yearRange.value[1]);

  // 指标：全部（三条柱），仅展示单一地区或全国（由 singleDeltaProvince 控制）
  if (selectedDeltaIndicator.value === 'all') {
    const targetProvince: string = singleDeltaProvince.value || '全国';

    if (targetProvince === '全国') {
      const nationalDelta: Record<number, { year: number; 'Δenergy': (number | null)[]; 'Δgreen': (number | null)[]; 'Δemission': (number | null)[] }> = {};
      inRangeData.forEach((d: DeltaRow) => {
        const bucket = (nationalDelta[d.year] ||= { year: d.year, 'Δenergy': [], 'Δgreen': [], 'Δemission': [] });
        if (d['Δenergy'] != null) bucket['Δenergy'].push(d['Δenergy']);
        if (d['Δgreen'] != null) bucket['Δgreen'].push(d['Δgreen']);
        if (d['Δemission'] != null) bucket['Δemission'].push(d['Δemission']);
      });

      const nationalArray = Object.values(nationalDelta) as Array<{ year: number; 'Δenergy': (number | null)[]; 'Δgreen': (number | null)[]; 'Δemission': (number | null)[] }>;
      return nationalArray.map((y) => ({
        year: y.year,
        'Δenergy': y['Δenergy'].length ? (y['Δenergy'].reduce((a:number,b:number|null)=>a+(b??0),0)/y['Δenergy'].length) : null,
        'Δgreen': y['Δgreen'].length ? (y['Δgreen'].reduce((a:number,b:number|null)=>a+(b??0),0)/y['Δgreen'].length) : null,
        'Δemission': y['Δemission'].length ? (y['Δemission'].reduce((a:number,b:number|null)=>a+(b??0),0)/y['Δemission'].length) : null,
      })).sort((a, b)=>a.year-b.year);
    } else {
      const byYear: Record<number, { year: number; 'Δenergy': number | null; 'Δgreen': number | null; 'Δemission': number | null }> = {};
      inRangeData
        .filter((d: DeltaRow) => d.province === targetProvince)
        .forEach((d) => {
          byYear[d.year] = { year: d.year, 'Δenergy': d['Δenergy'], 'Δgreen': d['Δgreen'], 'Δemission': d['Δemission'] };
        });
      const years = Array.from(new Set(inRangeData.map(d => d.year))).filter(y=>y>=2006).sort((a,b)=>a-b);
      return years.map((y)=> byYear[y] ?? { year: y, 'Δenergy': null, 'Δgreen': null, 'Δemission': null });
    }
  }

  // 指标：单项（多省对比或单省/全国平均）
  const key: 'Δenergy' | 'Δgreen' | 'Δemission' = selectedDeltaIndicator.value as 'Δenergy' | 'Δgreen' | 'Δemission';
  if (selectedProvinces.value.length > 1) {
    const result = inRangeData
      .filter((d: DeltaRow) => selectedProvinces.value.includes(d.province))
      .map((d: DeltaRow) => ({ year: d.year, province: d.province, value: d[key] }))
      .sort((a, b) => a.year - b.year);

    // 如果包含“全国”，补充全国聚合系列
    if (selectedProvinces.value.includes('全国')) {
      const bucket: Record<number, number[]> = {};
      inRangeData.forEach((d: DeltaRow) => {
        const v = d[key];
        if (v != null) (bucket[d.year] ||= []).push(v as number);
      });
      const years = Array.from(new Set(inRangeData.map(d => d.year))).filter(y=>y>=2006).sort((a,b)=>a-b);
      const nationalSeries = years.map((y)=> ({ year: y, province: '全国', value: bucket[y]?.length ? (bucket[y]!.reduce((a,b)=>a+b,0)/bucket[y]!.length) : null }));
      return [...result, ...nationalSeries];
    }
    return result;
  } else {
    const targetProvince: string = selectedProvinces.value[0] ?? '全国';
    if (targetProvince === '全国') {
      const bucket: Record<number, number[]> = {};
      inRangeData.forEach((d: DeltaRow) => {
        const v = d[key];
        if (v != null) (bucket[d.year] ||= []).push(v as number);
      });
      const years = Array.from(new Set(inRangeData.map(d => d.year))).filter(y=>y>=2006).sort((a,b)=>a-b);
      return years.map((y)=> ({ year: y, province: '全国', value: bucket[y]?.length ? (bucket[y]!.reduce((a,b)=>a+b,0)/bucket[y]!.length) : null }));
    } else {
      return inRangeData
        .filter((d: DeltaRow) => d.province === targetProvince)
        .map((d) => ({ year: d.year, province: d.province, value: d[key] }))
        .sort((a, b) => a.year - b.year);
    }
  }
});

const downloadTrendData = (): void => {
  if (!trendChartInstance) return;
  if (!trendData.value.length || limitedProvinces.value.length === 0) {
    console.warn('No data to download.');
    return;
  }
  const years: number[] = Array.from({ length: yearRange.value[1] - yearRange.value[0] + 1 }, (_, i) => yearRange.value[0] + i);
  const dataByYear: Record<number, any> = {};

  limitedProvinces.value.forEach((province) => {
    let provinceData: Array<{ year: number; clean_ratio: number | null; green_rate: number | null; emission_per_gdp: number | null; province?: string }>;
    if (province === '全国') {
      const national: Record<number, { year: number; clean_ratio: (number | null)[]; green_rate: (number | null)[]; emission_per_gdp: (number | null)[] }> = {};
      trendData.value.forEach((d: TrendRow) => {
        if (d.year >= yearRange.value[0] && d.year <= yearRange.value[1]) {
          const bucket = (national[d.year] ||= { year: d.year, clean_ratio: [], green_rate: [], emission_per_gdp: [] });
          if (d.clean_ratio != null) bucket.clean_ratio.push(d.clean_ratio);
          if (d.green_rate != null) bucket.green_rate.push(d.green_rate);
          if (d.emission_per_gdp != null) bucket.emission_per_gdp.push(d.emission_per_gdp);
        }
      });
      const nationalArray = Object.values(national) as Array<{ year: number; clean_ratio: (number | null)[]; green_rate: (number | null)[]; emission_per_gdp: (number | null)[] }>;
      provinceData = nationalArray.map((y) => ({
        year: y.year,
        clean_ratio: y.clean_ratio.length ? (y.clean_ratio.reduce((a:number,b:number|null)=>a+(b??0),0)/y.clean_ratio.length) : null,
        green_rate: y.green_rate.length ? (y.green_rate.reduce((a:number,b:number|null)=>a+(b??0),0)/y.green_rate.length) : null,
        emission_per_gdp: y.emission_per_gdp.length ? (y.emission_per_gdp.reduce((a:number,b:number|null)=>a+(b??0),0)/y.emission_per_gdp.length) : null,
      })).sort((a, b)=>a.year-b.year);
    } else {
      provinceData = trendData.value
        .filter((d: TrendRow) => normalizeProvinceName(d.province) === province && d.year >= yearRange.value[0] && d.year <= yearRange.value[1])
        .map((d) => ({ year: d.year, clean_ratio: d.clean_ratio ?? null, green_rate: d.green_rate ?? null, emission_per_gdp: d.emission_per_gdp ?? null, province: d.province }))
        .sort((a, b) => a.year - b.year);
    }

    const dataMap = new Map<number, { year: number; clean_ratio: number | null; green_rate: number | null; emission_per_gdp: number | null; province?: string }>(
      provinceData.map((d) => [d.year, d])
    );
    years.forEach((year: number) => {
      const d: { clean_ratio?: number | null; green_rate?: number | null; emission_per_gdp?: number | null } = dataMap.get(year) || {};
      if (!dataByYear[year]) dataByYear[year] = { year };
      if (!dataByYear[year][province]) dataByYear[year][province] = {};
      dataByYear[year][province]['清洁能源占比'] = d.clean_ratio ?? '';
      dataByYear[year][province]['绿化覆盖率'] = d.green_rate ?? '';
      dataByYear[year][province]['单位GDP排放'] = d.emission_per_gdp ?? '';
    });
  });

  const headers: string[] = ['year'];
  selectedProvinces.value.forEach((p: string) => {
    headers.push(`${p}_clean_ratio`, `${p}_green_rate`, `${p}_emission_per_gdp`);
  });

  const rows: string[] = Object.values(dataByYear).map((yearData: any) => {
    const row: any[] = [yearData.year];
    selectedProvinces.value.forEach((p: string) => {
      const provinceData: Record<string, any> = yearData[p] || {};
      row.push(provinceData['清洁能源占比'] ?? '');
      row.push(provinceData['绿化覆盖率'] ?? '');
      row.push(provinceData['单位GDP排放'] ?? '');
    });
    return row.join(',');
  });

  const csvContent = [headers.join(','), ...rows].join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.setAttribute('href', url);
  link.setAttribute('download', 'trend_data.csv');
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

// --- Chart Rendering ---

function renderTrendChart() {
  if (!trendChartInstance || !trendData.value.length) return;

  const yearsInRange: number[] = Array.from({ length: yearRange.value[1] - yearRange.value[0] + 1 }, (_, i) => yearRange.value[0] + i);
  
  let series: any[] = [];
  let insufficientDataProvinces: Set<string> = new Set();

  limitedProvinces.value.forEach((province: string) => {
    let provinceData: Array<{ year: number; clean_ratio: number | null; green_rate: number | null; emission_per_gdp: number | null; province?: string }>;
    if (province === '全国') {
      const nationalData: Record<number, { year: number; clean_ratio: (number | null)[]; green_rate: (number | null)[]; emission_per_gdp: (number | null)[] }> = {};
      trendData.value.forEach((d: TrendRow) => {
        if (d.year >= yearRange.value[0] && d.year <= yearRange.value[1]) {
          const bucket = (nationalData[d.year] ||= { year: d.year, clean_ratio: [], green_rate: [], emission_per_gdp: [] });
          if (d.clean_ratio != null) bucket.clean_ratio.push(d.clean_ratio);
          if (d.green_rate != null) bucket.green_rate.push(d.green_rate);
          if (d.emission_per_gdp != null) bucket.emission_per_gdp.push(d.emission_per_gdp);
        }
      });
      const nationalArray = Object.values(nationalData) as Array<{ year: number; clean_ratio: (number | null)[]; green_rate: (number | null)[]; emission_per_gdp: (number | null)[] }>;
      provinceData = nationalArray.map((yearData) => ({
        year: yearData.year,
        clean_ratio: yearData.clean_ratio.length > 0 ? (yearData.clean_ratio.reduce((a: number, b: number | null) => a + (b ?? 0), 0) / yearData.clean_ratio.length) : null,
        green_rate: yearData.green_rate.length > 0 ? (yearData.green_rate.reduce((a: number, b: number | null) => a + (b ?? 0), 0) / yearData.green_rate.length) : null,
        emission_per_gdp: yearData.emission_per_gdp.length > 0 ? (yearData.emission_per_gdp.reduce((a: number, b: number | null) => a + (b ?? 0), 0) / yearData.emission_per_gdp.length) : null,
      })).sort((a, b) => a.year - b.year);
    } else {
      provinceData = trendData.value
        .filter((d: TrendRow) => normalizeProvinceName(d.province) === province && d.year >= yearRange.value[0] && d.year <= yearRange.value[1])
        .map((d) => ({ year: d.year, clean_ratio: d.clean_ratio ?? null, green_rate: d.green_rate ?? null, emission_per_gdp: d.emission_per_gdp ?? null, province: d.province }))
        .sort((a, b) => a.year - b.year);
    }

    // Check for insufficient data
    const dataCompleteness = {
      clean_ratio: provinceData.filter(d => d.clean_ratio != null).length / yearsInRange.length,
      green_rate: provinceData.filter(d => d.green_rate != null).length / yearsInRange.length,
      emission_per_gdp: provinceData.filter(d => d.emission_per_gdp != null).length / yearsInRange.length,
    };

    if (Object.values(dataCompleteness).some(rate => rate < 0.5)) {
      insufficientDataProvinces.add(province);
    }

    const dataMap = new Map<number, { year: number; clean_ratio: number | null; green_rate: number | null; emission_per_gdp: number | null; province?: string }>(
      provinceData.map((d) => [d.year, d])
    );
    const completeData: Array<{ year: number; clean_ratio?: number | null; green_rate?: number | null; emission_per_gdp?: number | null; province?: string }>
      = yearsInRange.map((year: number) => dataMap.get(year) || { year });

    const cleanRatioData: (number | null)[] = completeData.map((d) => d.clean_ratio ?? null);
    const greenRateData: (number | null)[] = completeData.map((d) => d.green_rate ?? null);
    const emissionData: (number | null)[] = completeData.map((d) => d.emission_per_gdp ?? null);

    const applySmoothing = (arr: (number | null)[]): (number | null)[] => {
      if (smoothMode.value === 'none') return arr;
      const ma3 = arr.map((_, i, a) => {
        const idxs = [i-1, i, i+1].filter((k) => k>=0 && k<a.length && a[k]!=null);
        if (!idxs.length) return (a[i] ?? null);
        const sum = idxs.reduce((acc, k)=>acc + (a[k] as number), 0);
        return sum / idxs.length;
      });
      return ma3; // sgolay3 与 3点均值等价，保留接口
    };

    const hoveringActive = !!hoveredProvince.value;
    const isHovered = hoveringActive && hoveredProvince.value === province;
    const fadedOpacity = hoveringActive ? (isHovered ? 1 : 0.12) : 1;
    const baseWidth = hoveringActive ? (isHovered ? 4 : 1) : 2;

    series.push(
      {
        name: `${province}-清洁能源占比`,
        type: 'line',
        yAxisIndex: 0,
        connectNulls: true,
        data: applySmoothing(cleanRatioData),
        itemStyle: { color: colors.energy },
        lineStyle: { width: baseWidth, opacity: fadedOpacity },
        z: isHovered ? 5 : 1,
        emphasis: { focus: 'series', lineStyle: { width: Math.max(baseWidth + 2, 5) } }
      },
      {
        name: `${province}-绿化覆盖率`,
        type: 'line',
        yAxisIndex: 0,
        connectNulls: true,
        data: applySmoothing(greenRateData),
        itemStyle: { color: colors.green },
        lineStyle: { width: baseWidth, opacity: fadedOpacity },
        z: isHovered ? 5 : 1,
        emphasis: { focus: 'series', lineStyle: { width: Math.max(baseWidth + 2, 5) } }
      },
      {
        name: `${province}-单位GDP排放`,
        type: 'line',
        yAxisIndex: axisMode.value === 'dual' ? 1 : 0,
        connectNulls: true,
        data: applySmoothing(emissionData),
        itemStyle: { color: colors.emission },
        lineStyle: { width: baseWidth, opacity: fadedOpacity },
        z: isHovered ? 5 : 1,
        emphasis: { focus: 'series', lineStyle: { width: Math.max(baseWidth + 2, 5) } }
      }
    );
  });

  // 注意：平滑效果已在 applySmoothing 中处理，避免重复应用


  if (series.length === 0) {
    trendChartInstance.clear();
    trendChartInstance.setOption({ title: { text: '请先选择省份', left: 'center', top: 'center' } });
    return;
  }

  const years: number[] = yearsInRange;

  let titleConfig: any = {};
  let normalizationSubtitle = '';
  let warningSubtitle = '';

  if (axisMode.value === 'single') {
    series.forEach(s => {
      if (s.name.includes('单位GDP排放')) {
        const emissionValues = (s.data as (number | null)[]).filter((v): v is number => v != null);
        if (emissionValues.length > 0) {
          const min = Math.min(...emissionValues);
          const max = Math.max(...emissionValues);
          const range = max - min;
          if (range > 0) {
            const normalize = (val: number) => (val - min) / range;
            s.data = (s.data as (number | null)[]).map(v => v == null ? null : normalize(v));
          }
        }
      }
    });
    normalizationSubtitle = '（单位GDP排放已归一化）';
  }

  if (insufficientDataProvinces.size > 0) {
    warningSubtitle = `⚠️ ${[...insufficientDataProvinces].join(', ')} 数据不足`;
  }
  
  titleConfig = {
    subtext: [normalizationSubtitle, warningSubtitle].filter(Boolean).join('  '),
    subtextStyle: {
      color: '#f97316',
      align: 'right'
    }
  };


  // 独立的 tooltip 格式化函数，避免对象内联函数解析问题
  const formatTooltip = (params: any) => {
    if (!Array.isArray(params) || params.length === 0) return '';
    // 若存在悬停省份，则仅展示该省份的三指标信息
    const activeProvince = (hoveredProvince.value || '').trim();
    if (activeProvince) {
      params = params.filter((p: any) => {
        const [prov] = String(p?.seriesName || '').split('-');
        return prov === activeProvince;
      });
      if (!params.length) return '';
    }
    let tooltipText = `${params[0].axisValue}年<br/>`;
    const groupedByProvince: Record<string, any[]> = {};
    params.forEach((param: any) => {
      const [province] = param.seriesName.split('-');
      if (!groupedByProvince[province]) {
        groupedByProvince[province] = [];
      }
      groupedByProvince[province].push(param);
    });

    Object.keys(groupedByProvince).forEach((province) => {
      tooltipText += `<b>${province}</b><br/>`;
      const items = groupedByProvince[province] ?? [];
      items.forEach((param: any) => {
        const [, indicatorName] = param.seriesName.split('-');
        const isImputed = IMPUTED_YEARS.includes(Number(param.axisValue)) && indicatorName === '单位GDP排放';
        let formattedValue = 'N/A';

        if (param.value != null) {
          if (indicatorName === '清洁能源占比' || indicatorName === '绿化覆盖率') {
            formattedValue = (param.value * 100).toFixed(1) + '%';
          } else if (indicatorName === '单位GDP排放') {
            if (axisMode.value === 'single') {
              formattedValue = `${Number(param.value).toFixed(3)} (归一化)`;
            } else {
              formattedValue = Number(param.value).toFixed(3) + ' 吨/万元';
            }
          } else {
            formattedValue = Number(param.value).toFixed(3);
          }
        }

        tooltipText += `${param.marker} ${indicatorName}: ${formattedValue}`;
        if (isImputed) tooltipText += ' (⚠️外推)';
        tooltipText += '<br/>';
      });
    });

    const yearHovered = Number(params[0].axisValue);
    if (IMPUTED_YEARS.includes(yearHovered)) {
      tooltipText += `<div style="margin-top:6px;color:#f59e0b;">本省该段的排放强度由能源消费与化石比回归外推得出，建议与全国事件或能源口径变更交叉验证</div>`;
    }
    return tooltipText;
  };

  const option: any = {
    title: titleConfig,
    tooltip: { trigger: 'axis', formatter: formatTooltip },
    legend: { show: false },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '15%', containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: years },
    yAxis: axisMode.value === 'dual'
        ? [
            { type: 'value', name: '比例', min: 0, max: 1, axisLabel: { formatter: (v: number) => (v * 100).toFixed(0) + '%' } },
            { type: 'value', name: '吨/万元', axisLabel: { formatter: (v: number) => Number(v).toFixed(3) } }
        ]
        : { type: 'value', name: '归一化值', min: 0, max: 1 },
    series: series,
    dataZoom: [
        { type: 'inside', moveOnMouseWheel: true, moveOnMouseMove: true, zoomLock: true }
    ]
  };
  
  const imputedYearsRange = years.filter(year => IMPUTED_YEARS.includes(year));
  if (imputedYearsRange.length > 0) {
    const firstLeftSeries = series.find(s => !s.name.includes('单位GDP排放')) || series[0];
    if (firstLeftSeries) {
      firstLeftSeries.markArea = {
        silent: true,
        itemStyle: { opacity: 0.08, color: '#f59e0b' },
        data: [[{ xAxis: String(Math.min(...imputedYearsRange)) }, { xAxis: String(Math.max(...imputedYearsRange)) }]],
        label: { show: true, position: 'top', formatter: 'ⓘ 外推数据', fontSize: 12, color: '#f59e0b' }
      };
    }
  }

  // 全国政策事件竖线锚点
  if (nationalPolicyYears.value.length) {
    const markLine: { silent: boolean; lineStyle: { color: string; type: 'dashed'; width: number }; label: { show: boolean }; data: Array<{ xAxis: string }> } = {
      silent: true,
      lineStyle: { color: '#6b7280', type: 'dashed', width: 1 },
      label: { show: false },
      data: nationalPolicyYears.value.map(y => ({ xAxis: String(y) }))
    };
    // 附加到第一个系列，ECharts会在图层渲染竖线
    if (option.series && option.series.length) {
      option.series[0].markLine = markLine;
    } else {
      option.markLine = markLine;
    }
  }

  // 时间线悬停高亮年份竖线
  if (hoveredYear.value) {
    const hovered: { silent: boolean; lineStyle: { color: string; width: number }; data: Array<{ xAxis: string }> } = { silent: true, lineStyle: { color: '#f59e0b', width: 2 }, data: [{ xAxis: String(hoveredYear.value) }] };
    if (option.series && option.series.length) {
      const s0 = option.series[0];
      s0.markLine = s0.markLine ? { ...s0.markLine, data: [...(s0.markLine.data || []), ...hovered.data] } : hovered;
    } else {
      option.markLine = hovered;
    }
  }

  trendChartInstance!.setOption(option, true);
};


// --- Lifecycle and Event Handlers ---

const initChart = (): void => {
  if (trendChartRef.value) {
    trendChartInstance = echarts.init(trendChartRef.value);
    // 兼容 toolbox 的 dataZoom 与内置滑条/滚轮缩放的事件格式
    trendChartInstance.on('datazoom', (params: any) => {
      try {
        const opt: any = trendChartInstance!.getOption();
        const xAxis0 = Array.isArray(opt?.xAxis) ? opt.xAxis[0] : opt?.xAxis;
        const axisData = (xAxis0?.data ?? []) as Array<string | number>;
        const axis: number[] = axisData.map((v: string | number) => Number(v));
        if (!axis.length) return;
    
        let sYear: number | undefined;
        let eYear: number | undefined;
    
        if (Array.isArray(params?.batch) && params.batch[0]) {
          const b = params.batch[0] as any;
          sYear = b.startValue !== undefined ? Number(b.startValue) : undefined;
          eYear = b.endValue !== undefined ? Number(b.endValue) : undefined;
        }
    
        if (sYear !== undefined && eYear !== undefined) {
          // 使用年份值直接更新
          const newStartYear = Math.min(sYear, eYear);
          const newEndYear = Math.max(sYear, eYear);
          if (newStartYear && newEndYear) yearRange.value = [newStartYear, newEndYear];
        } else {
          // 按百分比计算索引
          const sPct = Number(params?.start ?? 0);
          const ePct = Number(params?.end ?? 100);
          const sIdx = Math.round((sPct / 100) * (axis.length - 1));
          const eIdx = Math.round((ePct / 100) * (axis.length - 1));
          const newStartYear = axis[Math.max(0, Math.min(axis.length - 1, sIdx))] ?? axis[0];
          const newEndYear = axis[Math.max(0, Math.min(axis.length - 1, eIdx))] ?? axis[axis.length - 1];
          if (newStartYear && newEndYear) yearRange.value = [newStartYear, newEndYear];
        }
      } catch (e) {
        console.warn('datazoom 事件解析失败:', e);
      }
    });
    trendChartInstance.on('brushSelected', (params: any) => {
      const areas = (params.areas as Array<{ coordRange: [number, number] }>) || [];
      if (!areas.length) return;
      const opt: any = trendChartInstance!.getOption();
      const xAxis0 = Array.isArray(opt?.xAxis) ? opt.xAxis[0] : opt?.xAxis;
      const axisData = (xAxis0?.data ?? []) as Array<string | number>;
      const axis: number[] = axisData.map((v: string | number) => Number(v));
      const range = areas[0]?.coordRange;
      if (axis.length && range && range.length === 2) {
        const [start, end] = range;
        const idxS = Math.max(0, Math.round(start));
        const idxE = Math.min(axis.length - 1, Math.round(end));
        const newStart: number = axis[idxS]!;
        const newEnd: number = axis[idxE]!;
        if (newStart && newEnd) yearRange.value = [newStart, newEnd];
      }
    });
    // 鼠标悬停到某条线时记录省份并重绘以高亮该省的三条线
    trendChartInstance.on('mouseover', (evt: any) => {
      try {
        if (evt && evt.componentType === 'series' && typeof evt.seriesName === 'string') {
          const prov: string = String(evt.seriesName).split('-')[0] || '';
          hoveredProvince.value = prov;
          renderTrendChart();
        }
      } catch (e) {
        // 忽略解析异常
      }
    });
    // 鼠标移出某条线时，若不在其他线条上则恢复默认显示
    trendChartInstance.on('mouseout', (evt: any) => {
      try {
        if (evt && evt.componentType === 'series') {
          hoveredProvince.value = '';
          renderTrendChart();
        }
      } catch (_) {}
    });
    // 鼠标移出图表元素时取消高亮，恢复原逻辑
    trendChartInstance.on('globalout', () => {
      hoveredProvince.value = '';
      renderTrendChart();
    });
    loadData();
  }
};

const handleResize = (): void => {
  trendChartInstance?.resize();
};

onMounted(() => {
  nextTick(() => {
      initChart();
  });
  window.addEventListener('resize', handleResize);
  loadNationalPolicyYears();
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
  trendChartInstance?.dispose();
});

// --- Watchers ---
watch([selectedProvinces, yearRange, axisMode, smoothMode], () => {
    if(trendChartInstance) {
        renderTrendChart();
    }
}, { deep: true });

// 同步时间线滑轨边界到数据范围（不影响其它图表）
watch([minYear, maxYear], () => {
  const minV = minYear.value;
  const maxV = maxYear.value;
  // 如果当前超界，重置为边界
  const [curMin, curMax] = timelineYearRange.value;
  const newMin = Math.max(minV, curMin);
  const newMax = Math.min(maxV, curMax);
  if (newMin !== curMin || newMax !== curMax) {
    timelineYearRange.value = [minV, maxV];
  } else if (!timelineYearRange.value || timelineYearRange.value.length !== 2) {
    timelineYearRange.value = [minV, maxV];
  }
});

const hoveredProvince = ref<string>('');
const onTimelineHover = (year: number, province?: string) => {
  hoveredYear.value = year;
  hoveredProvince.value = province ?? '';
  if (trendChartInstance) renderTrendChart();
};

const onTimelineHoverClear = () => {
  hoveredYear.value = null;
  if (trendChartInstance) renderTrendChart();
};

</script>

<style scoped>
/* 页面标题统一左侧间距与颜色（略深的绿色） */
.section-title {
  margin-left: var(--title-left-gap, 28px);
  color: var(--primary-dark, #179299);
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
/* 顶部控件并排：滑轨在左、选择框在右 */
.section-controls {
  display: flex;
  align-items: center;
  gap: 30px;
}
/* 顶部滑轨改为主题色 */
.section-controls :deep(.el-slider) { --el-color-primary: var(--primary-color); }
.section-controls :deep(.el-slider__bar) { background-color: var(--primary-color); }
.section-controls :deep(.el-slider__button) { border-color: var(--primary-color); }
/* 省份选择弹框与输入同宽，略微收窄 */
:deep(.compact-select-dropdown) { width: 360px; }
/* 显示全部选中标签并隐藏每个标签的 × 关闭按钮 */
.compact-select :deep(.el-select__tags .el-tag .el-tag__close) { display: none; }
/* 主体网格容器：用于形成与主体边界的留白以及卡片间隙 */
.grid-layout {
  display: grid;
  gap: var(--grid-gap, 24px);
  padding: var(--grid-padding, 24px);
  height: 100%; /* 让网格布局占满整个视图高度 */
}

/* 统一白色圆角卡片样式 */
.card {
  background: #ffffff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 6px 16px rgba(15, 181, 174, 0.25);
  overflow: hidden; /* 裁剪内部图表，保证圆角可见 */
  display: flex; /* 使用 flex 布局来管理内部元素 */
  flex-direction: column; /* 垂直排列标题和图表 */
}

.chart-container {
  flex: 1; /* 让图表容器占据剩余空间 */
  min-height: 0; /* 防止 flex item 在内容过长时溢出 */
}
.controls-row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;      /* 小屏不拥挤 */
}
.controls-row > * {
  flex: 0 0 auto;       /* 禁止自动扩展/收缩，避免相互挤压 */
}
/* 趋势图控件靠右并与容器右侧保持留白 */
.trend-controls { justify-content: flex-end; margin-right: 12px; }
/* 双轴/同轴选中态换成主题色，仅作用于本控件组 */
.trend-controls :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background-color: var(--primary-color);
  border-color: var(--primary-color);
  color: #fff;
}
.trend-controls :deep(.el-radio-button.is-active .el-radio-button__inner) {
  background-color: var(--primary-color);
  border-color: var(--primary-color);
  color: #fff;
}
</style>
