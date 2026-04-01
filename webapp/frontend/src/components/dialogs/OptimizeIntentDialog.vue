<script setup lang="ts">
const visible = defineModel<boolean>({ default: false });
const directionDraft = defineModel<string>("directionDraft", { default: "" });

defineProps<{
  previewingInput?: boolean;
}>();

const emit = defineEmits<{
  confirm: [];
}>();

function onCancel() {
  visible.value = false;
}

function onConfirm() {
  emit("confirm");
}
</script>

<template>
  <el-dialog
    v-model="visible"
    title="优化方向"
    width="520px"
    destroy-on-close
    class="optimize-intent-dialog"
  >
    <p class="lead muted">
      在「本章任务」中填写待优化的正文或说明后，在此补充<strong>希望加强的方向</strong>（可空）。将一并写入发给模型的任务，不单独改你的表单原文。
    </p>
    <el-input
      v-model="directionDraft"
      type="textarea"
      :rows="5"
      placeholder="例如：场面更壮观、更有压迫感；感情线更细腻、内心戏更足；节奏更紧、减少说明段落…"
      resize="vertical"
    />
    <template #footer>
      <el-button @click="onCancel">取消</el-button>
      <el-button
        type="primary"
        :loading="previewingInput"
        :disabled="previewingInput"
        @click="onConfirm"
      >
        下一步：生成 Input 预览
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
