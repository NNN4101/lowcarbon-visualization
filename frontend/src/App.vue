<template>
  <div class="flex flex-col h-screen bg-[var(--primary-bg)] text-gray-800">
    <!-- 顶部标题栏 -->
    <header class="bg-[var(--primary-color)] text-white h-[72px] px-16 flex items-center justify-between shadow-md">
      <div class="flex items-center">
        <h1 class="text-[25px] font-semibold tracking-wide ml-4">
          中国省域低碳发展协同演化可视化系统
        </h1>
      </div>
    </header>

    <!-- 主体内容 -->
    <div class="flex flex-1 overflow-hidden">
      <!-- 左侧导航栏 -->
      <aside class="w-[260px] bg-[var(--primary-color)] text-white py-6 px-8 flex flex-col shadow-md">
        <nav class="flex-1 space-y-2">
          <div
            v-for="item in menus"
            :key="item.name"
            :class="[
              'nav-item',
              currentPage === item.name ? 'nav-item-active' : '',
            ]"
            @click="nav.go(item.name)"
          >
            <i :class="item.icon"></i>
            <span class="ml-4">{{ item.label }}</span>
          </div>
        </nav>
      </aside>

      <!-- 右侧主内容 -->
      <main class="flex-1 overflow-y-auto bg-[var(--content-bg)] p-8">
        <component :is="currentComponent" />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { useNavStore } from "./stores/nav";
import { storeToRefs } from "pinia";

// ✅ 页面组件（保持原有逻辑）
import DashboardView from "./views/DashboardView.vue";
import SpatialView from "./views/SpatialView.vue";
import SynergyView from "./views/SynergyView.vue";
import TemporalView from "./views/TemporalView.vue";

const menus = [
  { name: "dashboard", label: "首页", icon: "bi bi-house-door-fill" },
  { name: "spatial", label: "空间识别分析", icon: "bi bi-geo-alt-fill" },
  { name: "synergy", label: "协同机制分析", icon: "bi bi-diagram-3-fill" },
  { name: "temporal", label: "时序演化分析", icon: "bi bi-graph-up-arrow" },
];

const nav = useNavStore();
const { currentPage } = storeToRefs(nav);

const currentComponent = computed(() => {
  switch (currentPage.value) {
    case "spatial":
      return SpatialView;
    case "synergy":
      return SynergyView;
    case "temporal":
      return TemporalView;
    // 模块四已移除
    default:
      return DashboardView;
  }
});

// 顶部年份与搜索栏交互（可扩展）
const years = Array.from({ length: 20 }, (_, i) => 2025 - i);
const selectedYear = ref(2022);
</script>

<style>
@import "bootstrap-icons/font/bootstrap-icons.css";

/* ====== 主题配色 ====== */
:root {
  --primary-color: #0FB5AE;
  --primary-bg: #EEF9F8;
  --content-bg: #e6f9f8; /* 浅绿色背景 */
}

 /* ====== 左侧导航栏样式（纵向排列，居中） ====== */
 /* 导航栏 */
 nav {
   display: flex;
   flex-direction: column; /* 子项纵向排列 */
   align-items: center;   /* 使固定宽度的选项盒子在侧栏水平居中 */
 }

/* 导航栏选项框 */
 .nav-item {
  padding-left: 12px;             /*内容与边框拉开点距离 */
  letter-spacing: 0.14em;         /* 增大字间距 */
   display: flex;
   align-items: center;
   justify-content: flex-start;
   width: 220px;  /* 选项盒子宽度 */
   height: 50px;  /* 选项盒子高度（增大） */
   margin: 6px 0; /* 垂直间距 */
   border-radius: 16px; /* 增大圆角 */
   cursor: pointer;
   transition: all 0.2s;
  font-size: 17px;                /* 导航字体变大 */
   font-weight: 540;
   color: white;  /* 默认字体为白色 */
 }

 /* 鼠标经过导航栏选项框 */
 .nav-item:hover {
   background: rgba(255, 255, 255, 0.15);
 }

 /* 选中导航栏选项框 */
 .nav-item-active {
   background: #ffffff;         /* 选中后变白 */
   color: var(--primary-color); /* 选中文本为主题色 */
   box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
   width: 220px;  /* 保持选中框宽度不变 */
   height: 50px;  /* 保持选中框高度同步增大 */
   display: flex;
   align-items: center;
   justify-content: flex-start;
   border-radius: 18px; /* 增大圆角（选中态同步） */
 }

 /* 修改标题为白色并整体右移 */
 header h1 {
   color: white;      /* 标题字体颜色改为白色 */
   margin-left: 27px; /* 标题整体向右移动 */
 }
</style>
