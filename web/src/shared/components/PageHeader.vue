<template>
  <header
    class="page-header"
    :class="{ 'page-header--described': description }"
    :aria-labelledby="titleId"
    :aria-describedby="description ? descriptionId : undefined"
  >
    <div class="page-header-copy">
      <p class="eyebrow">{{ eyebrow }}</p>
      <h1 :id="titleId">{{ title }}</h1>
      <p v-if="description" :id="descriptionId" class="page-description">{{ description }}</p>
    </div>
    <div class="page-header-actions" role="group" :aria-label="`${title}页面操作`">
      <slot />
    </div>
  </header>
</template>

<script setup lang="ts">
import { useId } from 'vue'

defineProps<{
  eyebrow: string
  title: string
  description?: string
}>()

const componentId = useId()
const titleId = `${componentId}-title`
const descriptionId = `${componentId}-description`
</script>
