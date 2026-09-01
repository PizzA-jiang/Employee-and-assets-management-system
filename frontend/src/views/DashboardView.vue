<template>
  <div class="dashboard">
    <div class="stat-cards">
      <div class="stat-card">
        <div class="stat-icon" style="background:#ecf5ff;color:#409eff">
          <el-icon :size="28"><User /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.total_employees }}</div>
          <div class="stat-label">员工总数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background:#f0f9eb;color:#67c23a">
          <el-icon :size="28"><Box /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.total_assets }}</div>
          <div class="stat-label">资产总数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background:#fdf6ec;color:#e6a23c">
          <el-icon :size="28"><Operation /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.assets_in_use }}</div>
          <div class="stat-label">使用中</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background:#fef0f0;color:#f56c6c">
          <el-icon :size="28"><Warning /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.assets_maintenance }}</div>
          <div class="stat-label">维修中</div>
        </div>
      </div>
    </div>

    <div class="chart-row">
      <div class="chart-card">
        <div class="chart-title">资产状态分布</div>
        <v-chart class="chart" :option="assetStatusOption" autoresize />
      </div>
      <div class="chart-card">
        <div class="chart-title">资产类型分布</div>
        <v-chart class="chart" :option="assetTypeOption" autoresize />
      </div>
      <div class="chart-card">
        <div class="chart-title">员工部门分布</div>
        <v-chart class="chart" :option="deptOption" autoresize />
      </div>
    </div>

    <div class="chart-row">
      <div class="chart-card wide">
        <div class="chart-title">流转操作统计</div>
        <v-chart class="chart" :option="logsOption" autoresize />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart, BarChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, LegendComponent, GridComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import {
  getDashboardStatsApi, getAssetsByTypeApi, getAssetsByStatusApi,
  getLogsByActionApi, getEmployeesByDeptApi,
} from '../api/dashboard'

use([PieChart, BarChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer])

const STATUS_MAP = { available: '闲置', in_use: '使用中', maintenance: '维修中', scrapped: '报废' }
const STATUS_COLOR = { available: '#67c23a', in_use: '#409eff', maintenance: '#e6a23c', scrapped: '#f56c6c' }
const TYPE_MAP = { computer: '电脑', phone: '手机', monitor: '显示器', peripheral: '外设', furniture: '办公家具', other: '其他' }
const ACTION_MAP = { checkout: '领用', return: '归还', transfer: '调拨', maintenance_in: '送修', maintenance_out: '修好', scrap: '报废' }

const stats = ref({ total_employees: 0, total_assets: 0, assets_in_use: 0, assets_available: 0, assets_maintenance: 0, assets_scrapped: 0 })
const assetStatusOption = ref({})
const assetTypeOption = ref({})
const deptOption = ref({})
const logsOption = ref({})

function makePie(data, nameMap, colorMap) {
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 12 } },
    color: Object.values(colorMap),
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}\n{d}%' },
      data: data.map(d => ({ name: nameMap[d.type || d.status || d.department || d.action] || d.type || d.status || d.department || d.action, value: d.count })),
    }],
  }
}

onMounted(async () => {
  try {
    const [s, byType, byStatus, logs, depts] = await Promise.all([
      getDashboardStatsApi(),
      getAssetsByTypeApi(),
      getAssetsByStatusApi(),
      getLogsByActionApi(),
      getEmployeesByDeptApi(),
    ])
    stats.value = s
    assetStatusOption.value = makePie(byStatus, STATUS_MAP, STATUS_COLOR)
    assetTypeOption.value = makePie(byType, TYPE_MAP, {
      computer: '#409eff', phone: '#67c23a', monitor: '#e6a23c',
      peripheral: '#f56c6c', furniture: '#909399', other: '#b37feb',
    })
    deptOption.value = makePie(depts, {}, {
      0: '#409eff', 1: '#67c23a', 2: '#e6a23c', 3: '#f56c6c', 4: '#909399', 5: '#b37feb',
    })
    logsOption.value = {
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: logs.map(l => ACTION_MAP[l.action] || l.action), axisLabel: { fontSize: 12 } },
      yAxis: { type: 'value', minInterval: 1 },
      series: [{ type: 'bar', data: logs.map(l => l.count), itemStyle: { borderRadius: [4, 4, 0, 0] }, color: '#409eff' }],
      grid: { left: 50, right: 20, bottom: 30, top: 20 },
    }
  } catch { /* ignore */ }
})
</script>

<style scoped>
.dashboard { padding: 0; }
.stat-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
.stat-card {
  display: flex; align-items: center; gap: 16px;
  background: #fff; border-radius: 8px; padding: 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
}
.stat-icon { width: 56px; height: 56px; border-radius: 12px; display: flex; align-items: center; justify-content: center; }
.stat-value { font-size: 28px; font-weight: 700; color: #303133; }
.stat-label { font-size: 13px; color: #909399; margin-top: 2px; }
.chart-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 16px; }
.chart-row:last-child { grid-template-columns: 1fr; }
.chart-card {
  background: #fff; border-radius: 8px; padding: 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
}
.chart-card.wide { grid-column: 1 / -1; }
.chart-title { font-size: 15px; font-weight: 600; color: #303133; margin-bottom: 8px; }
.chart { width: 100%; height: 300px; }
</style>
