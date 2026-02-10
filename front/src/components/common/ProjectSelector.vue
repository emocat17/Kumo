<template>
  <div class="project-selector">
    <select class="form-select" :value="modelValue" @change="updateValue">
      <option :value="null">所有项目</option>
      <option v-for="project in projects" :key="project.id" :value="project.id">
        {{ project.name }}
      </option>
    </select>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

defineProps<{
  modelValue?: number | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: number | null): void
}>()

interface Project {
  id: number
  name: string
}

const projects = ref<Project[]>([])

const fetchProjects = async () => {
  try {
    const res = await fetch('/api/projects')
    if (res.ok) {
      projects.value = await res.json()
    }
  } catch (e) {
    console.error('Failed to fetch projects', e)
  }
}

const updateValue = (e: Event) => {
  const target = e.target as HTMLSelectElement
  const val = target.value
  emit('update:modelValue', val ? parseInt(val) : null)
}

onMounted(() => {
  fetchProjects()
})
</script>

<style scoped>
.project-selector {
    display: inline-block;
}
.form-select {
    height: 36px;
    padding: 0 12px;
    border: 1px solid #d9d9d9;
    border-radius: 6px;
    font-size: 14px;
    color: #333;
    outline: none;
    transition: all 0.2s;
    min-width: 150px;
}
.form-select:focus {
    border-color: #40a9ff;
    box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}
</style>
