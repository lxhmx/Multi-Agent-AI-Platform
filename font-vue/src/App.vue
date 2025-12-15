<script setup lang="ts">
import { RouterView, useRoute } from 'vue-router'
import { computed } from 'vue'
import AppLayout from './layouts/AppLayout.vue'

const route = useRoute()
const isBlank = computed(() => route.meta.layout === 'blank')
</script>

<template>
  <RouterView v-slot="{ Component }">
    <component v-if="isBlank" :is="Component" />
    <AppLayout v-else>
      <component :is="Component" />
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
