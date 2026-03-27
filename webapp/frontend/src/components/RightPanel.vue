<template>
  <el-card shadow="never">
    <div style="display:flex; gap:8px; align-items:baseline; flex-wrap:wrap;">
      <div style="font-weight:600;">运行结果</div>
      <div class="muted" style="font-size:12px;">会自动显示 state.continuity / content / plan 等</div>
    </div>
    <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-top:8px;">
      <el-tag size="small" :type="running ? 'warning' : (runPhase === 'error' ? 'danger' : 'success')">
        {{ running ? `进行中：${runPhaseLabel}` : `状态：${runPhaseLabel}` }}
      </el-tag>
      <span class="muted" v-if="runHint">{{ runHint }}</span>
    </div>
    <div v-if="tokenUsageText" class="output-path-tip">
      本次 Token：<code>{{ tokenUsageText }}</code>
    </div>
    <div v-if="lastOutputPath" class="output-path-tip">
      输出文件：<code>{{ lastOutputPath }}</code>
    </div>
    <el-divider></el-divider>
    <el-tabs :model-value="rightTab" @update:model-value="onRightTabChange" class="right-tabs">
      <el-tab-pane label="文本输出" name="result">
        <pre ref="resultPreRef" class="result-pre" v-text="resultText || (running ? '（进行中，等待正文输出...）' : '（本次运行暂无正文输出）')"></pre>
      </el-tab-pane>
      <el-tab-pane label="下章建议" name="next">
        <pre ref="nextPreRef" class="result-pre" v-text="nextStatusText || (running ? '（生成中，完成后将展示下章建议）' : '（本次运行暂无下章建议）')"></pre>
      </el-tab-pane>
      <el-tab-pane label="规划流" name="plan">
        <pre ref="planPreRef" class="result-pre" v-text="planStreamText || (running ? '（进行中，等待规划流输出...）' : '（本次运行暂无规划流输出）')"></pre>
      </el-tab-pane>
      <el-tab-pane label="图谱可视化" name="graph">
        <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
          <el-button size="small" type="primary" @click="openGraphDialog" :disabled="!novelId">
            打开全屏图谱
          </el-button>
        </div>
        <div class="muted" style="margin-top:8px;">
          {{ novelId ? `当前视图：${graphViewLabel}` : "请先选择/创建小说，再查看图谱。" }}
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<script lang="ts" setup>
import { nextTick, ref, watch } from "vue";

const props = defineProps<{
  running: boolean;
  runPhase: string;
  runPhaseLabel: string;
  runHint: string;
  tokenUsageText: string;
  lastOutputPath: string;
  rightTab: "result" | "next" | "plan" | "graph";
  graphView: "people" | "events" | "mixed";
  resultText: string;
  nextStatusText: string;
  planStreamText: string;
  novelId: string;
  onRightTabChange: (v: "result" | "next" | "plan" | "graph") => void;
  graphViewLabel: string;
  openGraphDialog: () => void;
}>();

const resultPreRef = ref<HTMLElement | null>(null);
const nextPreRef = ref<HTMLElement | null>(null);
const planPreRef = ref<HTMLElement | null>(null);

async function scrollActiveOutputToBottom() {
  await nextTick();
  let el: HTMLElement | null = null;
  if (props.rightTab === "result") el = resultPreRef.value;
  if (props.rightTab === "next") el = nextPreRef.value;
  if (props.rightTab === "plan") el = planPreRef.value;
  if (!el) return;
  el.scrollTop = el.scrollHeight;
}

watch(
  () => [props.resultText, props.nextStatusText, props.planStreamText, props.rightTab],
  () => {
    void scrollActiveOutputToBottom();
  },
  { flush: "post" }
);
</script>

<style scoped>
.muted {
  color: #909399;
  font-size: 12px;
}
.output-path-tip {
  margin-top: 6px;
  font-size: 12px;
  color: #606266;
  word-break: break-all;
}
.result-pre {
  max-height: 48vh;
  overflow: auto;
  padding: 10px;
  background: #fff;
  border-radius: 10px;
  border: 1px solid #ebeef5;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}
.right-tabs :deep(.el-tabs__content) {
  padding-top: 6px;
}
</style>

