<template>
  <div class="main-layout">
    <router-view />
  </div>
</template>

<script setup lang="ts">
// Main layout simplified for full screen map
</script>

<style scoped>
.main-layout {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  position: relative;
}
</style>
