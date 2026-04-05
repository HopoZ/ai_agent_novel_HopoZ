<template>
  <el-dialog
    v-model="visible"
    title="DeepSeek API 密钥"
    width="min(480px, 92vw)"
    destroy-on-close
    @open="onOpen"
  >
    <p class="api-help">
      密钥仅保存在本机
      <code>storage/user_settings.json</code>
      （与小说数据同目录）；不会上传到项目仓库。调用模型时优先使用系统环境变量
      <code>DEEPSEEK_API_KEY</code>，若已设置环境变量，界面保存的密钥不会生效。
    </p>
    <el-alert
      v-if="source === 'env'"
      type="info"
      :closable="false"
      show-icon
      class="api-alert"
      title="当前已检测到环境变量 DEEPSEEK_API_KEY，将优先使用该密钥。"
    />
    <el-form label-position="top" @submit.prevent>
      <el-form-item label="API Key">
        <el-input
          v-model="draft"
          type="password"
          show-password
          placeholder="sk-..."
          clearable
          autocomplete="off"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button type="danger" plain :disabled="saving" @click="onClear">清除本地保存</el-button>
      <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script lang="ts" setup>
import { computed, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { apiJson } from "../../api/client";

const props = defineProps<{ modelValue: boolean }>();
const emit = defineEmits<{ (e: "update:modelValue", v: boolean): void }>();

const visible = computed({
  get: () => props.modelValue,
  set: (v: boolean) => emit("update:modelValue", v),
});

const draft = ref("");
const saving = ref(false);
const source = ref<"env" | "file" | "none">("none");

watch(visible, (v) => {
  if (!v) draft.value = "";
});

async function onOpen() {
  draft.value = "";
  try {
    const res = (await apiJson("/api/settings", "GET", null)) as {
      deepseek_api_key_configured?: boolean;
      deepseek_api_key_source?: "env" | "file" | "none";
    };
    source.value = res.deepseek_api_key_source || "none";
  } catch {
    source.value = "none";
  }
}

async function onSave() {
  const t = (draft.value || "").trim();
  if (!t) {
    ElMessage.warning("请输入 API Key 后再保存；若仅想删除本地保存，请点「清除本地保存」。");
    return;
  }
  saving.value = true;
  try {
    const res = (await apiJson("/api/settings/api_key", "POST", {
      api_key: t,
    })) as { ok?: boolean; deepseek_api_key_source?: "env" | "file" | "none" };
    if (res.deepseek_api_key_source) source.value = res.deepseek_api_key_source;
    ElMessage.success("已保存");
    visible.value = false;
  } catch (e: unknown) {
    const err = e as { message?: string };
    ElMessage.error(err?.message || String(e));
  } finally {
    saving.value = false;
  }
}

async function onClear() {
  saving.value = true;
  try {
    await apiJson("/api/settings/api_key", "POST", { api_key: "" });
    draft.value = "";
    source.value = "none";
    ElMessage.success("已清除本地保存的密钥");
  } catch (e: unknown) {
    const err = e as { message?: string };
    ElMessage.error(err?.message || String(e));
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.api-help {
  margin: 0 0 12px;
  font-size: 12px;
  line-height: 1.55;
  color: var(--lit-ink-muted, #606266);
}
.api-help code {
  font-size: 11px;
  word-break: break-all;
}
.api-alert {
  margin-bottom: 12px;
}
</style>
