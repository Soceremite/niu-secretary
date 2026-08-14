<template>
  <div
    v-if="adminFeedback"
    class="admin-feedback-bar"
    aria-live="polite"
    aria-atomic="true"
  >
    <el-alert
      :title="adminFeedback.title"
      :description="adminFeedback.message"
      :type="adminFeedback.type"
      show-icon
      closable
      @close="clearAdminFeedback"
    />
  </div>
</template>

<script setup lang="ts">
import { adminFeedback, clearAdminFeedback } from '@/shared/lib/adminFeedback'
</script>
