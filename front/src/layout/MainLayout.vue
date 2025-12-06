<template>
  <div class="layout-container">
    <!-- Sidebar -->
    <aside :class="['sidebar', { collapsed: isCollapsed }]">
      <div class="sidebar-header">
        <div class="brand-wrapper">
          <img src="@/assets/Kumo.jpg" alt="Logo" class="logo" />
          <div class="brand-text" v-if="!isCollapsed">
            <span class="title">Kumo</span>
            <span class="version">v1.0.0</span>
          </div>
        </div>
        <button class="toggle-btn" @click="toggleCollapse">
          {{ isCollapsed ? '»' : '«' }}
        </button>
      </div>

      <nav class="sidebar-nav">
        <router-link to="/" class="nav-item" active-class="active">
          <i class="icon-dashboard"></i>
          <span v-if="!isCollapsed">仪表盘</span>
        </router-link>
        <a href="#" class="nav-item">
          <i class="icon-cron"></i>
          <span v-if="!isCollapsed">定时任务</span>
        </a>
        <a href="#" class="nav-item">
          <i class="icon-project"></i>
          <span v-if="!isCollapsed">项目</span>
        </a>
        <router-link to="/python-environments" class="nav-item" active-class="active">
          <i class="icon-python"></i>
          <span v-if="!isCollapsed">Python环境</span>
        </router-link>
        <router-link to="/python-versions" class="nav-item" active-class="active">
          <i class="icon-version"></i>
          <span v-if="!isCollapsed">Python版本</span>
        </router-link>
        <a href="#" class="nav-item">
          <i class="icon-user"></i>
          <span v-if="!isCollapsed">用户管理</span>
        </a>
        <a href="#" class="nav-item">
          <i class="icon-node"></i>
          <span v-if="!isCollapsed">分布式节点</span>
        </a>
        <a href="#" class="nav-item">
          <i class="icon-log"></i>
          <span v-if="!isCollapsed">日志管理</span>
        </a>
        <a href="#" class="nav-item">
          <i class="icon-setting"></i>
          <span v-if="!isCollapsed">设置</span>
        </a>
      </nav>

    </aside>

    <!-- Main Content -->
    <div class="main-wrapper">
      <header class="top-header">
        <div class="header-left">
          <!-- Breadcrumb or Title could go here -->
        </div>
        <div class="header-right">
        </div>
      </header>

      <main class="content-area">
        <router-view />
      </main>

      <footer class="app-footer">
        Kumo . 2025. All rights reserved.
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const isCollapsed = ref(false)

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}
</script>

<style scoped>
.layout-container {
  display: flex;
  height: 100vh;
  background-color: #f3f4f6;
  color: #1f2937;
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

/* Sidebar */
.sidebar {
  width: 256px;
  background-color: #ffffff;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  flex-shrink: 0;
}

.sidebar.collapsed {
  width: 64px;
}

.sidebar-header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  border-bottom: 1px solid #f3f4f6;
}

.brand-wrapper {
  display: flex;
  align-items: center;
}

.toggle-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
  color: #6b7280;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.toggle-btn:hover {
  background-color: #f3f4f6;
  color: #111827;
}

.logo {
  width: 32px;
  height: 32px;
}

.brand-text {
  margin-left: 12px;
  display: flex;
  align-items: baseline;
}

.title {
  font-weight: 700;
  font-size: 1.125rem;
  color: #111827;
}

.version {
  font-size: 0.75rem;
  color: #6b7280;
  margin-left: 4px;
}

.sidebar-nav {
  flex: 1;
  padding: 16px 8px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  margin-bottom: 4px;
  border-radius: 6px;
  color: #4b5563;
  text-decoration: none;
  font-size: 0.875rem;
  transition: background-color 0.2s;
}

.nav-item:hover, .nav-item.active {
  background-color: #f3f4f6;
  color: #111827;
}

.nav-item i {
  width: 20px;
  height: 20px;
  background-color: #9ca3af; /* Placeholder for icon */
  margin-right: 12px;
  border-radius: 4px;
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 8px;
}

.sidebar.collapsed .nav-item i {
  margin-right: 0;
}

/* Removed Sidebar Footer Styles */


/* Main Content */
.main-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.top-header {
  height: 64px;
  background-color: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-link {
  color: #6b7280;
  text-decoration: none;
  font-size: 0.875rem;
}

.header-btn {
  padding: 6px 12px;
  border: 1px solid #e5e7eb;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
  color: #374151;
}

.header-btn:hover {
  background-color: #f9fafb;
}

.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.app-footer {
  padding: 16px 24px;
  background-color: #ffffff;
  border-top: 1px solid #e5e7eb;
  font-size: 0.75rem;
  color: #9ca3af;
  text-align: center;
}
</style>
