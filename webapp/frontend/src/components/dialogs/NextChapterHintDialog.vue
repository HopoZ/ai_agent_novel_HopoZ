<script setup lang="ts">
const visible = defineModel<boolean>({ default: false });
const draft = defineModel<string>("draft", { default: "" });

defineProps<{
  previewingInput?: boolean;
}>();

const emit = defineEmits<{
  confirm: [];
}>();

function onLater() {
  visible.value = false;
}

function onConfirm() {
  emit("confirm");
}
</script>

<template>
  <el-dialog
    v-model="visible"
    title="下章提示"
    width="560px"
    destroy-on-close
    class="next-chapter-hint-dialog"
  >
    <p class="lead muted">
      以下为刚才的下章建议（可改写、补充）。点击「确认生成下一章」后，将打开与「生成正文」相同的
      Input 预览，确认无误后再开始规划与写作。
    </p>
    <el-input
      v-model="draft"
      type="textarea"
      :rows="12"
      placeholder="写下你希望下一章推进的方向、节奏或要点…"
      resize="vertical"
    />
    <template #footer>
      <el-button @click="onLater">稍后再说</el-button>
      <el-button
        type="primary"
        :loading="previewingInput"
        :disabled="previewingInput"
        @click="onConfirm"
      >
        确认生成下一章
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.lead {
  margin: 0 0 12px;
  line-height: 1.55;
  font-size: 13px;
}
.muted {
  color: #909399;
}
</style>
