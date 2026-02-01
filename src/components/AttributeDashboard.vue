<template>
  <div class="attribute-dashboard">
    <div class="dashboard-header">
      <span class="title">属性统计看板 (选区岩性)</span>
      <el-button 
        size="small" 
        :icon="Download" 
        circle 
        @click="exportChart" 
        title="导出图片" 
        :disabled="!hasData"
      />
    </div>
    <div class="chart-wrapper">
        <div ref="chartRef" class="chart-container"></div>
        <div v-if="!hasData" class="no-data-overlay">
            <el-empty description="请使用框选工具选择区域" :image-size="60" />
        </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue';
import * as echarts from 'echarts';
import { Download } from '@element-plus/icons-vue';

const props = defineProps<{
  data: Array<{ name: string; value: number }>;
}>();

const chartRef = ref<HTMLDivElement | null>(null);
let myChart: echarts.ECharts | null = null;

const hasData = computed(() => props.data && props.data.length > 0 && props.data.some(d => d.value > 0));

const initChart = () => {
  if (!chartRef.value) return;
  
  myChart = echarts.init(chartRef.value);
  
  updateChart();
  
  window.addEventListener('resize', handleResize);
};

const updateChart = () => {
  if (!myChart) return;

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      top: 'middle',
      textStyle: {
        fontSize: 11
      }
    },
    series: [
      {
        name: '岩性分布',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 5,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          },
          itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        },
        labelLine: {
          show: false
        },
        data: props.data && props.data.length ? props.data : []
      }
    ]
  };

  myChart.setOption(option);
};

const handleResize = () => {
  myChart?.resize();
};

const exportChart = () => {
    if (!myChart) return;
    const url = myChart.getDataURL({
        type: 'png',
        pixelRatio: 2,
        backgroundColor: '#fff'
    });
    
    const link = document.createElement('a');
    link.href = url;
    link.download = '岩性统计.png';
    link.click();
};

onMounted(() => {
    nextTick(() => {
        initChart();
    });
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  myChart?.dispose();
});

watch(() => props.data, () => {
  updateChart();
}, { deep: true });

</script>

<style scoped>
.attribute-dashboard {
  position: absolute;
  bottom: 20px;
  right: 20px;
  width: 360px;
  height: 240px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  z-index: 100;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.dashboard-header {
  padding: 10px 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(245, 247, 250, 0.8);
}

.title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.chart-wrapper {
  flex: 1;
  position: relative;
  width: 100%;
  height: 100%;
}

.chart-container {
  width: 100%;
  height: 100%;
}

.no-data-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 10;
}
</style>
