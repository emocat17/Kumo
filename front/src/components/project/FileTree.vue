<template>
  <ul class="file-tree">
    <li v-for="item in items" :key="item.path">
      <div 
        class="tree-item" 
        :class="{ 'is-active': activePath === item.path }"
        @click="handleClick(item)"
      >
        <span class="icon">{{ item.type === 'dir' ? (item.isOpen ? '📂' : '📁') : '📄' }}</span>
        <span class="label">{{ item.label }}</span>
      </div>
      <div v-if="item.type === 'dir' && item.isOpen" class="children">
        <FileTree 
          :items="item.children || []" 
          :active-path="activePath" 
          @select="onSelect"
        />
      </div>
    </li>
  </ul>
</template>

<script setup lang="ts">
export interface TreeItem {
  label: string
  path: string
  type: 'file' | 'dir'
  children?: TreeItem[]
  isOpen?: boolean
}

const props = defineProps<{
  items: TreeItem[]
  activePath: string
}>()
// Use props to avoid unused variable warning (though defineProps returns props, it's fine)
void props

const emit = defineEmits(['select'])

const handleClick = (item: TreeItem) => {
  if (item.type === 'dir') {
    item.isOpen = !item.isOpen
  } else {
    emit('select', item)
  }
}

const onSelect = (item: TreeItem) => {
  emit('select', item)
}
</script>

<style scoped>
.file-tree {
  list-style: none;
  padding-left: 0;
  margin: 0;
}
.file-tree .file-tree {
    padding-left: 1rem;
}
.tree-item {
  cursor: pointer;
  padding: 4px 8px;
  display: flex;
  align-items: center;
  font-size: 13px;
  color: #555;
  user-select: none;
  border-radius: 4px;
}
.tree-item:hover {
  background-color: #f0f0f0;
  color: #333;
}
.tree-item.is-active {
  background-color: #e6f7ff;
  color: #1890ff;
}
.icon {
  margin-right: 6px;
  width: 16px;
  text-align: center;
  font-size: 14px;
}
.children {
  border-left: 1px solid #eee; 
}
</style>
