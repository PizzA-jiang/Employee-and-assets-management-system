<template>
  <el-container class="layout">
    <el-aside width="200px" class="aside">
      <div class="logo">
        <el-icon :size="20"><OfficeBuilding /></el-icon>
        <span>资产管理系统</span>
      </div>
      <el-menu
        router
        :default-active="activeMenu"
        background-color="#001529"
        text-color="#bfcbd9"
        active-text-color="#ffffff"
        class="menu"
      >
        <el-menu-item v-if="userStore.isAdmin" index="/employees">
          <el-icon><User /></el-icon>
          <span>员工管理</span>
        </el-menu-item>
        <el-menu-item index="/assets">
          <el-icon><Box /></el-icon>
          <span>资产管理</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.isAdmin" index="/asset-logs">
          <el-icon><Tickets /></el-icon>
          <span>流转记录</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.isAdmin" index="/operation-logs">
          <el-icon><Document /></el-icon>
          <span>操作日志</span>
        </el-menu-item>
        <el-menu-item index="/cloud-files">
          <el-icon><FolderOpened /></el-icon>
          <span>云盘</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.isAdmin" index="/knowledge">
          <el-icon><Reading /></el-icon>
          <span>知识库</span>
        </el-menu-item>
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>AI问答</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.isAdmin" index="/ai-config">
          <el-icon><Setting /></el-icon>
          <span>AI配置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-title">{{ route.meta.title || '' }}</div>
        <el-dropdown @command="handleCommand">
          <span class="user-info">
            <el-avatar :size="30" class="avatar">{{ avatarText }}</el-avatar>
            <span class="username">{{ userStore.displayName }}</span>
            <el-tag size="small" :type="userStore.isAdmin ? 'danger' : 'info'" effect="light">
              {{ userStore.isAdmin ? '管理员' : '员工' }}
            </el-tag>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)
const avatarText = computed(() => (userStore.displayName || 'U').slice(0, 1).toUpperCase())

async function handleCommand(command) {
  if (command !== 'logout') return
  try {
    await ElMessageBox.confirm('确定退出登录吗？', '提示', {
      confirmButtonText: '退出',
      cancelButtonText: '取消',
      type: 'warning',
    })
    userStore.logout()
    router.push('/login')
  } catch {
    /* 用户取消 */
  }
}
</script>

<style scoped>
.layout {
  height: 100%;
}
.aside {
  background-color: #001529;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.menu {
  border-right: none;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
  height: 60px;
}
.header-title {
  font-size: 16px;
  font-weight: 600;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  outline: none;
}
.username {
  font-size: 14px;
  color: #333;
}
.avatar {
  background-color: #409eff;
  color: #fff;
  font-size: 14px;
}
.main {
  background-color: #f0f2f5;
  padding: 16px;
}
</style>
