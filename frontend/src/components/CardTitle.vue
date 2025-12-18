<template>
  <div class="card-header">
    <h3 class="card-title">{{ title }}</h3>
    <div class="card-controls">
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
});
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
}

.card-controls {
  display: flex;
  gap: 12px;
  align-items: center;
}
</style>