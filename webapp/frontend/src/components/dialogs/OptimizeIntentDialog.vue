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
    <el-input
      v-model="directionDraft"
      type="textarea"
      :rows="5"
      placeholder="希望加强的方向（可空），例如：场面更壮观、节奏更紧、感情更细…"
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
        下一步：预览
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.muted {
  color: #909399;
}
</style>
