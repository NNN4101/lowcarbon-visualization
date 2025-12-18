<template>
  <div class="flex flex-col h-full relative" ref="wrapperRef">
    <div ref="timelineChartRef" class="flex-grow"></div>
    <!-- 右下角省份颜色图例 -->
    <div class="legend" v-if="legendItems.length">
      <div class="legend-item" v-for="item in legendItems" :key="item.name">
        <span class="legend-dot" :style="{ backgroundColor: item.color, borderColor: item.borderColor }"></span>
        <span class="legend-label">{{ item.name }}</span>
      </div>
    </div>
    <div
      v-if="detail.visible"
      ref="popoverRef"
      class="detail-popover"
      :style="{ left: detail.left + 'px', top: detail.top + 'px' }"
      @mouseenter="onPopoverEnter"
      @mouseleave="onPopoverLeave"
    >
      <div class="detail-title">{{ detail.data?.year }} 年政策</div>
      <div class="detail-body">
        <div style="margin-bottom:6px;">地区：{{ detail.data?.regionLabel }}</div>
        <div v-if="detail.data?.national?.length">
          <strong>全国：</strong>
          <ul>
            <li v-for="n in detail.data.national" :key="n.policy_name">{{ n.policy_name }}</li>
          </ul>
        </div>
        <div v-if="detail.data?.province?.length" style="margin-top:6px;">
          <strong>所选省份：</strong>
          <ul>
            <li v-for="p in detail.data.province" :key="p.policy_name">{{ p.policy_name }}</li>
          </ul>
        </div>
        <div v-if="!detail.data?.national?.length && !detail.data?.province?.length">无数据</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick, computed } from 'vue';
import * as echarts from 'echarts';
import axios from 'axios';

const props = defineProps({
  // 页面顶部/年度变化速率传入的已选省份（可包含“全国”）
  provinces: {
    type: Array,
    required: true,
    default: () => ['全国']
  },
  // 仅控制“政策事件时间线”的年份范围（父视图标题行滑轨）
  yearRange: {
    type: Array,
    required: false,
    default: () => []
  }
});

const timelineChartRef = ref(null);
const wrapperRef = ref(null);
const popoverRef = ref(null);
let timelineChartInstance = null;
const allPolicyData = ref([]);
const emit = defineEmits(['hover-year', 'hover-clear']);
// 年份范围（用于内部默认值，若父未传入）
const minYear = ref(2000);
const maxYear = ref(2025);
// 图例项
const legendItems = ref([]);
// 选中省份（包含“全国”时映射为“中国”）
const selectedAll = computed(() => {
  const arr = Array.isArray(props.provinces) ? props.provinces : [];
  const set = new Set(arr.filter(p => !!p));
  return Array.from(set);
});

// 颜色常量（满足需求：全国=绿色，省=橙色，同时有=蓝色）
const COLOR_NATIONAL = '#22c55e'; // 绿色
const COLOR_PROVINCE = '#f59e0b'; // 橙色
const COLOR_BOTH = '#2563eb';     // 蓝色

const levelSize = {
  '国家级': 12,
  '省级': 9,
  '市级': 7,
};
const levelBorderWidth = {
  '国家级': 2,
  '省级': 1,
  '市级': 0,
};

const normalizeProvinceName = (name) => {
  if (!name) return '';
  const mapping = {
    '北京市': '北京', '天津市': '天津', '上海市': '上海', '重庆市': '重庆',
    '内蒙古自治区': '内蒙古', '广西壮族自治区': '广西', '西藏自治区': '西藏',
    '宁夏回族自治区': '宁夏', '新疆维吾尔自治区': '新疆',
  };
  return mapping[name] || name.replace(/省|市|自治区|inant|回族|维吾尔/g, '');
};

const loadPolicyData = async () => {
  try {
    const response = await axios.get('/api/policy');
    if (response.status !== 200) throw new Error('Failed to fetch policy data');
    allPolicyData.value = response.data.map(d => ({
      ...d,
      province: normalizeProvinceName(d.province)
    }));
    // 初始化年份范围
    const years = allPolicyData.value.map(d => Number(d.year)).filter(y => !Number.isNaN(y));
    if (years.length) {
      minYear.value = Math.min(...years);
      maxYear.value = Math.max(...years);
    }
    computeLegend();
    await nextTick();
    renderTimelineChart();
  } catch (error) {
    console.error("Error loading policy data:", error);
  }
};

const computeLegend = ({ hasNational = true, hasProvince = true, hasBoth = true } = {}) => {
  const items = [];
  if (hasNational) items.push({ name: '全国政策', color: COLOR_NATIONAL, borderColor: '#1f2937' });
  if (hasProvince) items.push({ name: '所选省政策', color: COLOR_PROVINCE, borderColor: '#1f2937' });
  if (hasBoth) items.push({ name: '两者都有', color: COLOR_BOTH, borderColor: '#1f2937' });
  legendItems.value = items;
};

const renderTimelineChart = () => {
  if (!timelineChartInstance) return;

  // 独立选择的省份（若只选全国，则仅展示全国）
  const selectedProvince = selectedAll.value.find(p => p !== '全国') || '全国';

  const range = (props.yearRange && props.yearRange.length === 2) ? props.yearRange : [minYear.value, maxYear.value];

  const nationalData = allPolicyData.value
    .filter(d => d.province === '中国')
    .filter(d => d.year >= range[0] && d.year <= range[1]);

  const provinceData = selectedProvince === '全国'
    ? []
    : allPolicyData.value
        .filter(d => d.province === selectedProvince)
        .filter(d => d.year >= range[0] && d.year <= range[1]);

  const allYearsSet = new Set([
    ...nationalData.map(d => Number(d.year)),
    ...provinceData.map(d => Number(d.year)),
  ].filter(y => !Number.isNaN(y)));

  if (allYearsSet.size === 0) {
    timelineChartInstance.clear();
    timelineChartInstance.setOption({
      title: {
        text: '所选地区暂无政策事件，待补充',
        left: 'center',
        top: 'center',
        textStyle: { fontSize: 14, color: '#999' }
      }
    });
    return;
  }

  // 统一年份类型为字符串以适配 ECharts 类别轴（一个年份一个节点）
  const yearsNum = Array.from(allYearsSet).sort((a,b)=>a-b);
  const years = yearsNum.map(y => String(y));
  // 年度聚合：national vs province
  const aggregateByYear = yearsNum.map(y => {
    const national = nationalData.filter(d => Number(d.year) === y);
    const province = provinceData.filter(d => Number(d.year) === y);
    const hasNational = national.length > 0;
    const hasProvince = province.length > 0;
    const color = (hasNational && hasProvince) ? COLOR_BOTH : (hasNational ? COLOR_NATIONAL : COLOR_PROVINCE);
    return { year: y, national, province, hasNational, hasProvince, color };
  });

  // 更新图例：根据当前数据是否存在对应类别
  computeLegend({
    hasNational: nationalData.length > 0,
    hasProvince: provinceData.length > 0,
    hasBoth: aggregateByYear.some(a => a.hasNational && a.hasProvince)
  });

  // 上下交错：+1/-1 交替
  const lanes = aggregateByYear.map((_, idx) => (idx % 2 === 0 ? 1 : -1));
  const laneMax = 1;

  const scatterData = aggregateByYear.map((agg, idx) => ({
    name: String(agg.year),
    value: [String(agg.year), lanes[idx]],
    symbolSize: 12,
    itemStyle: {
      color: agg.color,
      borderWidth: 0,
      borderColor: '#1f2937'
    },
    label: {
      show: true,
      formatter: () => String(agg.year),
      position: lanes[idx] > 0 ? 'top' : 'bottom',
      color: '#111827',
      distance: 10
    }
  }));

  // 基线（y=0）
  const baseLineData = years.map(y => [y, 0]);

  // 树突：从轴 (y=0) 引到节点 (y=lane)
  const dendriteData = aggregateByYear.map((agg, idx) => ({ year: String(agg.year), lane: lanes[idx] }));

  const option = {
    tooltip: { show: false },
    grid: { top: 36, bottom: 36, left: 40, right: 40, containLabel: true },
    xAxis: {
      type: 'category',
      data: years,
      axisTick: { show: false },
      axisLabel: { show: false },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      min: -laneMax - 1,
      max: laneMax + 1,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: false },
      splitLine: { show: false }
    },
    series: [
      {
        type: 'line',
        data: baseLineData,
        symbol: 'none',
        lineStyle: { color: '#cbd5e1', width: 1.5 },
        emphasis: { disabled: true }
      },
      {
        type: 'custom',
        renderItem: (params, api) => {
          const year = api.value(0);
          const lane = api.value(1);
          const pt0 = api.coord([year, 0]);
          const pt1 = api.coord([year, lane]);
          return {
            type: 'line',
            shape: { x1: pt0[0], y1: pt0[1], x2: pt1[0], y2: pt1[1] },
            style: { stroke: '#cbd5e1', lineWidth: 1.5 }
          };
        },
        data: dendriteData.map(d => [d.year, d.lane]),
        tooltip: { show: false },
        z: 1
      },
      {
        type: 'scatter',
        data: scatterData,
        coordinateSystem: 'cartesian2d',
        itemStyle: { shadowBlur: 6, shadowColor: 'rgba(0,0,0,0.08)' },
        emphasis: { scale: 1.1 },
        z: 2
      }
    ]
  };

  timelineChartInstance.setOption(option, true);

  timelineChartInstance.off('mouseover');
  timelineChartInstance.off('globalout');
  timelineChartInstance.off('click');
  timelineChartInstance.on('mouseover', (params) => {
    if (params && (params.seriesType === 'scatter' || params.seriesType === 'custom') && params.value && params.value[0] != null) {
      if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
      const year = Number(params.value[0]);
      const agg = aggregateByYear[params.dataIndex];
      const provEmit = selectedProvince === '全国' ? '中国' : selectedProvince;
      if (!Number.isNaN(year)) emit('hover-year', year, provEmit);
      // 悬停显示年度聚合详情（国家与省份）
      // 使用鼠标位置来放置弹框，避免遮挡节点和鼠标
      const evt = params.event?.event;
      const mx = evt?.offsetX ?? 20;
      const my = evt?.offsetY ?? 20;
      const regionLabel = (agg.hasNational && agg.hasProvince)
        ? `全国 + ${selectedProvince}`
        : (agg.hasNational ? '全国' : (selectedProvince === '全国' ? '全国' : (agg.province.some(p => /市/.test(String(p.level))) ? `${selectedProvince}（市级）` : `${selectedProvince}`)));
      detail.value.data = { year: agg.year, national: agg.national, province: agg.province, regionLabel };
      // 先显示，再在 nextTick 中测量弹框尺寸并夹紧位置，避免首次显示高度不准导致溢出
      detail.value.visible = true;
      nextTick(() => {
        placePopoverNearCursor(mx, my);
      });
    }
  });
  timelineChartInstance.on('globalout', () => {
    emit('hover-clear');
    // 延时隐藏，给弹框 mouseenter 一个时间窗，避免出现竞态造成闪烁
    if (hideTimer) clearTimeout(hideTimer);
    hideTimer = setTimeout(() => {
      if (!isPopoverHover.value) detail.value.visible = false;
    }, 120);
  });
  // 鼠标移动近点捕获：当鼠标靠近散点时也显示弹框，避免线条/标签抢占命中导致不触发
  const zr = timelineChartInstance.getZr();
  zr.off('mousemove');
  zr.on('mousemove', (evt) => {
    if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
    const x = evt.offsetX, y = evt.offsetY;
    let closestIdx = -1;
    let minDist = Infinity;
    for (let i = 0; i < aggregateByYear.length; i++) {
      const pt = timelineChartInstance.convertToPixel({ seriesIndex: 2 }, [String(aggregateByYear[i].year), lanes[i]]);
      if (!pt) continue;
      const dx = pt[0] - x;
      const dy = pt[1] - y;
      const dist = Math.sqrt(dx*dx + dy*dy);
      if (dist < 22 && dist < minDist) { // 22px 命中半径（稍大以降低漏触发）
        minDist = dist;
        closestIdx = i;
      }
    }
    if (closestIdx >= 0) {
      const agg = aggregateByYear[closestIdx];
      const provEmit = selectedProvince === '全国' ? '中国' : selectedProvince;
      emit('hover-year', agg.year, provEmit);
      const regionLabel = (agg.hasNational && agg.hasProvince)
        ? `全国 + ${selectedProvince}`
        : (agg.hasNational ? '全国' : (selectedProvince === '全国' ? '全国' : (agg.province.some(p => /市/.test(String(p.level))) ? `${selectedProvince}（市级）` : `${selectedProvince}`)));
      detail.value.data = { year: agg.year, national: agg.national, province: agg.province, regionLabel };
      detail.value.visible = true;
      nextTick(() => {
        placePopoverNearCursor(x, y);
      });
    }
  });
  timelineChartInstance.on('click', (params) => {
    const agg = aggregateByYear[params.dataIndex];
    const evt = params.event?.event;
    const x = evt?.offsetX || 20;
    const y = evt?.offsetY || 20;
    const regionLabel = (agg.hasNational && agg.hasProvince)
      ? `全国 + ${selectedProvince}`
      : (agg.hasNational ? '全国' : (selectedProvince === '全国' ? '全国' : (agg.province.some(p => /市/.test(String(p.level))) ? `${selectedProvince}（市级）` : `${selectedProvince}`)));
    detail.value.data = { year: agg.year, national: agg.national, province: agg.province, regionLabel };
    placePopoverNearCursor(x, y);
    detail.value.visible = true;
  });
};

const initChart = () => {
  if (timelineChartRef.value) {
    timelineChartInstance = echarts.init(timelineChartRef.value);
    loadPolicyData();
  }
};

const handleResize = () => {
  timelineChartInstance?.resize();
  if (detail.value.visible) {
    // 重新校正弹框在容器内
    placePopover([detail.value.left, detail.value.top]);
  }
};

onMounted(() => {
  nextTick(() => {
    initChart();
  });
  window.addEventListener('resize', handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
  timelineChartInstance?.dispose();
});

watch(() => props.provinces, () => {
  if (timelineChartInstance) renderTimelineChart();
}, { deep: true });

watch(() => props.yearRange, () => {
  if (timelineChartInstance) renderTimelineChart();
}, { deep: true });

const detail = ref({ visible: false, left: 0, top: 0, data: null });

// —— 弹框交互与定位 ——
const isPopoverHover = ref(false);
const onPopoverEnter = () => { isPopoverHover.value = true; };
const onPopoverLeave = () => { isPopoverHover.value = false; if (hideTimer) clearTimeout(hideTimer); hideTimer = setTimeout(() => { if (!isPopoverHover.value) detail.value.visible = false; }, 80); };
// 隐藏防抖计时器，避免 globalout 与弹框 mouseenter 的竞态
let hideTimer = null;
const placePopover = (pt) => {
  const padding = 8;
  const w = wrapperRef.value?.clientWidth ?? 400;
  const h = wrapperRef.value?.clientHeight ?? 240;
  const popW = (popoverRef.value?.offsetWidth ?? 320);
  const popH = (popoverRef.value?.offsetHeight ?? 220);
  let lx = (pt?.[0] ?? 20) + 12;
  let ty = (pt?.[1] ?? 20) + 12;
  if (lx + popW + padding > w) lx = w - popW - padding;
  if (ty + popH + padding > h) ty = h - popH - padding;
  if (lx < padding) lx = padding;
  if (ty < padding) ty = padding;
  detail.value.left = lx;
  detail.value.top = ty;
};

// 根据鼠标位置智能放置弹框：优先在右下，不够空间时自动切换到左或上方
const placePopoverNearCursor = (x, y) => {
  const padding = 8;
  const w = wrapperRef.value?.clientWidth ?? 400;
  const h = wrapperRef.value?.clientHeight ?? 240;
  const popW = (popoverRef.value?.offsetWidth ?? 320);
  const popH = (popoverRef.value?.offsetHeight ?? 220);
  const offsetX = 16; // 与鼠标及节点保持安全距离
  const offsetY = 12;
  const canRight = x + offsetX + popW + padding <= w;
  const canBelow = y + offsetY + popH + padding <= h;
  let lx = canRight ? x + offsetX : x - popW - offsetX;
  let ty = canBelow ? y + offsetY : y - popH - offsetY;
  // 最终边界夹紧
  if (lx < padding) lx = padding;
  if (ty < padding) ty = padding;
  if (lx + popW + padding > w) lx = w - popW - padding;
  if (ty + popH + padding > h) ty = h - popH - padding;
  detail.value.left = lx;
  detail.value.top = ty;
};
</script>

<style scoped>
.flex-grow {
  flex-grow: 1;
  min-height: 0;
}

.legend {
  position: absolute;
  right: 8px;
  bottom: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  max-width: 320px;
}
.legend-item {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  color: #374151;
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 0;
  margin-right: 6px;
}

.detail-popover {
  position: absolute;
  background: #fff;
  border: 1px solid #e5e7eb;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  border-radius: 8px;
  padding: 10px 12px;
  max-width: 360px;
  max-height: 260px;
  overflow-y: auto;
  z-index: 20;
}
.detail-title {
  font-weight: 600;
  margin-bottom: 4px;
  font-size: 15px;
  }
.detail-body {
  font-size: 12px;
  color: #4b5563;
  line-height: 1.35;
}
/* 紧凑列表，提高信息承载能力 */
.detail-body ul {
  list-style: none;
  padding-left: 0;
  margin: 2px 0 6px;
}
.detail-body li {
  margin: 2px 0;
}
</style>