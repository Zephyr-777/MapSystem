<template>
  <div>
    <!-- Trigger Area -->
    <div 
      class="trigger-area" 
      @mouseenter="handleMouseEnter"
    >
      <div class="trigger-indicator"></div>
    </div>

    <!-- Panel -->
    <transition name="slide-fade">
      <div 
        v-show="isStatsVisible" 
        class="stats-panel glass-morphism"
      >
        <div class="panel-header">
          <span class="title">数据概览</span>
          <div class="actions">
            <el-button 
              link 
              size="small" 
              @click="refreshData" 
              :loading="loading"
              title="刷新"
              class="action-btn"
            >
              <el-icon><Refresh /></el-icon>
            </el-button>
            <!-- Close Button -->
            <el-button 
              link 
              size="small" 
              @click="handleClose" 
              title="关闭"
              class="action-btn close-btn"
            >
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
        </div>
        
        <div class="charts-container" v-loading="loading">
          <!-- 饼图：数据类型分布 -->
          <div class="chart-box">
            <div class="chart-title">数据类型分布</div>
            <div ref="pieChartRef" class="chart-instance"></div>
          </div>
          
          <!-- 柱状图：最近一周上传 -->
          <div class="chart-box">
            <div class="chart-title">近一周新增</div>
            <div ref="barChartRef" class="chart-instance"></div>
          </div>

          <!-- Admin Only Actions -->
          <div class="admin-actions" v-if="isAdmin">
            <el-button type="primary" size="small" plain style="width: 100%">
              导出统计数据
            </el-button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue';
import * as echarts from 'echarts';
import { Refresh, Close } from '@element-plus/icons-vue';
import { geoDataApi } from '@/api/geodata';
import { ElMessage } from 'element-plus';
import { useAuthStore } from '@/stores/auth';

const authStore = useAuthStore();
const isAdmin = computed(() => authStore.user?.role === 'admin');

const loading = ref(false);
const pieChartRef = ref<HTMLDivElement | null>(null);
const barChartRef = ref<HTMLDivElement | null>(null);
let pieChart: echarts.ECharts | null = null;
let barChart: echarts.ECharts | null = null;

const isStatsVisible = ref(false);

const handleMouseEnter = () => {
  if (!isStatsVisible.value) {
    isStatsVisible.value = true;
    // Resize charts when panel becomes visible
    nextTick(() => {
        // Force charts to re-read container size
        if (pieChart) pieChart.resize();
        if (barChart) barChart.resize();
    });
  }
};

const handleClose = () => {
  isStatsVisible.value = false;
};

const refreshData = async () => {
  loading.value = true;
  try {
    const res = await geoDataApi.getSummary();
    // res 应该直接是数据对象 { pie: [], bar: {} }
    // 如果有 axios 拦截器处理，直接取 res
    // 如果没有，取 res.data
    
    const data = (res as any).data || res;
    
    if (data.pie) {
      updatePieChart(data.pie);
    }
    
    if (data.bar) {
      updateBarChart(data.bar);
    }
    
  } catch (error) {
    console.error('Failed to fetch stats:', error);
    ElMessage.error('获取统计数据失败');
  } finally {
    loading.value = false;
  }
};

const initCharts = () => {
  if (pieChartRef.value) {
    pieChart = echarts.init(pieChartRef.value);
  }
  if (barChartRef.value) {
    barChart = echarts.init(barChartRef.value);
  }
};

const updatePieChart = (data: Array<{name: string, value: number}>) => {
  if (!pieChart) return;
  
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      bottom: '0%',
      left: 'center',
      itemWidth: 10,
      itemHeight: 10,
      textStyle: {
        color: '#333',
        fontSize: 10
      }
    },
    color: ['#0071E3', '#34C759', '#FF9500', '#FF3B30', '#AF52DE', '#5856D6'],
    series: [
      {
        name: '数据类型',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
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
            fontSize: 12,
            fontWeight: 'bold',
            color: '#1d1d1f'
          },
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.2)'
          }
        },
        labelLine: {
          show: false
        },
        data: data
      }
    ]
  };
  
  pieChart.setOption(option);
};

const updateBarChart = (data: { categories: string[], values: number[] }) => {
  if (!barChart) return;
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      backgroundColor: 'rgba(255, 255, 255, 0.9)',
      borderColor: '#eee',
      textStyle: {
        color: '#1d1d1f'
      }
    },
    grid: {
      top: '10%',
      left: '2%',
      right: '4%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: [
      {
        type: 'category',
        data: data.categories,
        axisTick: {
          show: false
        },
        axisLabel: {
          fontSize: 10,
          color: '#86868b',
          interval: 0,
          rotate: 30
        },
        axisLine: {
          lineStyle: {
            color: '#e5e5ea'
          }
        }
      }
    ],
    yAxis: [
      {
        type: 'value',
        minInterval: 1,
        splitLine: {
          lineStyle: {
            type: 'dashed',
            color: '#e5e5ea'
          }
        },
        axisLabel: {
          color: '#86868b',
          fontSize: 10
        }
      }
    ],
    series: [
      {
        name: '新增数据',
        type: 'bar',
        barWidth: '40%',
        data: data.values,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#5AC8FA' },
            { offset: 1, color: '#0071E3' }
          ]),
          borderRadius: [4, 4, 0, 0]
        },
        showBackground: true,
        backgroundStyle: {
          color: 'rgba(180, 180, 180, 0.1)',
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  };
  
  barChart.setOption(option);
};

const handleResize = () => {
  pieChart?.resize();
  barChart?.resize();
};

onMounted(async () => {
  await nextTick();
  initCharts();
  refreshData();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  pieChart?.dispose();
  barChart?.dispose();
});
</script>

<style scoped>
.trigger-area {
  position: absolute;
  top: 80px;
  left: 0;
  width: 20px;
  height: 400px;
  z-index: 98;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.trigger-indicator {
  width: 4px;
  height: 40px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 0 4px 4px 0;
  transition: all 0.2s;
}

.trigger-area:hover .trigger-indicator {
  width: 8px;
  background: #0071E3;
}

.stats-panel {
  position: absolute;
  top: 80px;
  left: 20px;
  width: 320px;
  z-index: 99;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.3s ease;
}

.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateX(-120%);
  opacity: 0;
}

/* 玻璃质感核心类 */
.glass-morphism {
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
}

.panel-header {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.03);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
  letter-spacing: -0.3px;
}

.actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  color: #86868b;
  font-size: 16px;
  transition: all 0.2s;
}

.action-btn:hover {
  color: #0071E3;
  transform: scale(1.1);
}

.close-btn:hover {
  color: #FF3B30;
}

.charts-container {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chart-box {
  width: 100%;
}

.chart-title {
  font-size: 13px;
  font-weight: 500;
  color: #86868b;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
}

.chart-title::before {
  content: '';
  display: inline-block;
  width: 4px;
  height: 12px;
  background: #0071E3;
  margin-right: 8px;
  border-radius: 2px;
}

.chart-instance {
  width: 100%;
  height: 160px;
}

.admin-actions {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}
</style>
