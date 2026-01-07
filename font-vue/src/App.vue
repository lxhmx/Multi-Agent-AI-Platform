<script setup lang="ts">
import { RouterView, useRoute } from 'vue-router'
import { computed } from 'vue'
import AppLayout from './layouts/AppLayout.vue'

const route = useRoute()
const isBlank = computed(() => route.meta.layout === 'blank')

// 需要缓存的页面组件名称列表
const cachedViews = [
  'AgentWorkbench',
  'VideoSummary', 
  'Chat',
  'Training',
  'DataManage'
]
</script>

<template>
  <RouterView v-slot="{ Component }">
    <component v-if="isBlank" :is="Component" />
    <AppLayout v-else>
      <keep-alive :include="cachedViews">
        <component :is="Component" />
      </keep-alive>
    </AppLayout>
  </RouterView>
</template>

<style>
html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
</style>
