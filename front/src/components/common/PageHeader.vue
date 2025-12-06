<template>
  <div class="page-header">
    <div class="header-content">
      <h1 class="page-title">
        <slot name="title">{{ title }}</slot>
      </h1>
      <div class="header-actions">
        <slot name="actions"></slot>
      </div>
    </div>
    <div class="header-description" v-if="description || $slots.description">
      <slot name="description">{{ description }}</slot>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps({
  title: {
    type: String,
    default: ''
  },
  description: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.page-header {
  margin-bottom: 24px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #111827;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.header-description {
  color: #6b7280;
  font-size: 0.875rem;
}
</style>
