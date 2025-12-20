<template>
  <router-view />
</template>

<script setup lang="ts">
</script>

<style>
body {
  margin: 0;
  padding: 0;
  background-color: #f3f4f6;
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  zoom: 1.1; /* Scale up content by ~25-50% based on request */
  overflow: hidden; /* Prevent outer scrollbar when zoom is applied */
}

*, *::before, *::after {
  box-sizing: border-box;
}
</style>

