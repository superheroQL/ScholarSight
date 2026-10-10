<template>
  <van-tabbar v-model="active" route>
    <van-tabbar-item to="/home" icon="home-o">{{ $t('nav.home') }}</van-tabbar-item>
    <van-tabbar-item to="/literature" icon="bookmark-o">{{ $t('nav.literatureManagement') }}</van-tabbar-item>
    <van-tabbar-item to="/read/1" icon="notes-o">{{ $t('nav.onlineReading') }}</van-tabbar-item>
    <van-tabbar-item to="/analysis/1" icon="chart-trending-o">{{ $t('nav.smartAnalysis') }}</van-tabbar-item>
    <van-tabbar-item to="/compare" icon="label-o">{{ $t('nav.multiPaperAnalysis') }}</van-tabbar-item>
    <van-tabbar-item to="/review" icon="orders-o">{{ $t('nav.literatureReview') }}</van-tabbar-item>
    <van-tabbar-item to="/aichat" icon="chat-o">{{ $t('nav.aiChat') }}</van-tabbar-item>
    <van-tabbar-item to="/my" icon="user-o">{{ $t('nav.my') }}</van-tabbar-item>
  </van-tabbar>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const active = ref(0)

const setActiveTab = () => {
  const path = route.path
  if (path.includes('/home')) {
    active.value = 0
  } else if (path.includes('/literature')) {
    active.value = 1
  } else if (path.includes('/read')) {
    active.value = 2
  } else if (path.includes('/analysis')) {
    active.value = 3
  } else if (path.includes('/compare') || path.includes('/multi-analysis')) {
    active.value = 4
  } else if (path.includes('/review')) {
    active.value = 5
  } else if (path.includes('/aichat')) {
    active.value = 6
  } else if (path.includes('/my')) {
    active.value = 7
  }
}

watch(
  () => route.path,
  () => setActiveTab(),
  { immediate: true }
)
</script>

<style scoped>
:deep(.van-tabbar) {
  height: 52px;
}

:deep(.van-tabbar-item__text) {
  font-size: 12px;
}
</style>