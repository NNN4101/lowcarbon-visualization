<template>
  <div ref="deltaChartRef" class="chart-container"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';
import * as echarts from 'echarts';

const props = defineProps({
  chartData: {
    type: Array,
    required: true,
    default: () => []
  },
  indicator: {
    type: String,
    default: 'all'
  },
  hoveredYear: {
    type: Number,
    default: null
  }
});

const deltaChartRef = ref(null);
let deltaChartInstance = null;

const colors = {
  energy: '#10b981',
  green: '#3b82f6',
  emission: '#f97316'
};

const indicatorMap = {
  'Δenergy': 'Δ 清洁能源占比',
  'Δgreen': 'Δ 绿化覆盖率',
  'Δemission': 'Δ 单位GDP排放'
};

const renderChart = () => {
  if (!deltaChartInstance || !props.chartData.length) {
    deltaChartInstance?.clear();
    deltaChartInstance?.setOption({ title: { text: '无数据', left: 'center', top: 'center' } });
    return;
  }

  const years = [...new Set(props.chartData.map(d => d.year))].filter(year => year >= 2006).sort();
  let series = [];
  let legendData = [];

  if (props.indicator === 'all') {
    const data = props.chartData.filter(d => d.year >= 2006);
    const deltaEnergy = data.map(d => d['Δenergy']);
    const deltaGreen = data.map(d => d['Δgreen']);
    const deltaEmission = data.map(d => d['Δemission']);

    series = [
      {
        name: indicatorMap['Δenergy'],
        type: 'bar',
        data: deltaEnergy,
        itemStyle: { color: colors.energy },
        label: {
          show: true,
          formatter: (p) => (p.value != null && p.value < 0 ? '!' : ''),
          color: '#ef4444',
          position: 'bottom',
          fontWeight: 'bold'
        },
        emphasis: { focus: 'series' }
      },
      {
        name: indicatorMap['Δgreen'],
        type: 'bar',
        data: deltaGreen,
        itemStyle: { color: colors.green },
        label: {
          show: true,
          formatter: (p) => (p.value != null && p.value < 0 ? '!' : ''),
          color: '#ef4444',
          position: 'bottom',
          fontWeight: 'bold'
        },
        emphasis: { focus: 'series' }
      },
      {
        name: indicatorMap['Δemission'],
        type: 'bar',
        data: deltaEmission,
        itemStyle: { color: colors.emission },
        label: {
          show: true,
          formatter: (p) => (p.value != null && p.value > 0 ? '!' : ''),
          color: '#ef4444',
          position: 'top',
          fontWeight: 'bold'
        },
        emphasis: { focus: 'series' }
      }
    ];
    legendData = Object.values(indicatorMap);

  } else {
    const dataByProvince = {};
    props.chartData.forEach(d => {
      if (d.year >= 2006) {
        if (!dataByProvince[d.province]) {
          dataByProvince[d.province] = {};
        }
        dataByProvince[d.province][d.year] = d.value;
      }
    });

    legendData = Object.keys(dataByProvince);
    series = Object.entries(dataByProvince).map(([province, yearData]) => ({
      name: province,
      type: 'bar',
      emphasis: { focus: 'series' },
      data: years.map(year => yearData[year] ?? null),
      label: {
        show: true,
        formatter: (p) => {
          const v = p.value;
          if (v == null) return '';
          if (props.indicator === 'Δemission') {
            return v > 0 ? '!' : '';
          }
          // energy/green: 退步为负值
          return v < 0 ? '!' : '';
        },
        color: '#ef4444',
        position: props.indicator === 'Δemission' ? 'top' : 'bottom',
        fontWeight: 'bold'
      }
    }));
  }

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        let tooltipText = `${params[0].axisValue}年 年度变化率<br/>`;
        params.forEach(param => {
          const value = param.value;
          let formattedValue = 'N/A';
          if (value != null) {
            const emissionSeries = param.seriesName.includes('排放') || props.indicator === 'Δemission';
            formattedValue = emissionSeries ? Number(value).toFixed(3) + ' 吨/万元' : (value * 100).toFixed(2) + '%';
          }
          tooltipText += `${param.marker} ${param.seriesName}: ${formattedValue}<br/>`;
        });
        return tooltipText;
      }
    },
    legend: {
      data: legendData,
      bottom: 0,
      type: 'scroll'
    },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: years },
    yAxis: { type: 'value', axisLabel: { formatter: (v) => props.indicator === 'Δemission' ? Number(v).toFixed(3) : (v * 100).toFixed(0) + '%' } },
    series: series
  };

  // 悬停年份竖线联动高亮
  if (props.hoveredYear) {
    const markLine = { silent: true, lineStyle: { color: '#f59e0b', width: 2 }, data: [{ xAxis: String(props.hoveredYear) }] };
    if (option.series && option.series.length) {
      option.series[0].markLine = markLine;
    } else {
      option.markLine = markLine;
    }
  }

  deltaChartInstance.setOption(option, true);
};

const initChart = () => {
  if (deltaChartRef.value) {
    deltaChartInstance = echarts.init(deltaChartRef.value);
    renderChart();
  }
};

const handleResize = () => {
  deltaChartInstance?.resize();
};

onMounted(() => {
  initChart();
  window.addEventListener('resize', handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
  deltaChartInstance?.dispose();
});

watch(() => [props.chartData, props.indicator], () => {
  if (deltaChartInstance) {
    renderChart();
  }
}, { deep: true });

</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
}
</style>