import { onBeforeUnmount, onMounted, ref } from "vue";

const LEFT_MIN_WIDTH = 280;
const LEFT_MAX_WIDTH = 680;
const MID_MIN_WIDTH = 340;
const MID_MAX_WIDTH = 760;

/** 小于等于此宽度：三栏改为纵向堆叠（手机 / 窄笔记本） */
export const LAYOUT_STACK_BREAKPOINT_PX = 1180;

/** 横向三栏时右侧栏至少保留的像素（再小则压缩左/中） */
const RIGHT_MIN_FOR_ROW = 260;
/** 两分割条宽 + main-layout 的 gap（12px × 3） */
const HANDLES_AND_GAPS_PX = 10 + 10 + 12 * 3;

export function usePanelResize() {
  const leftPanelWidth = ref(360);
  const midPanelWidth = ref(420);

  const layoutStacked = ref(
    typeof window !== "undefined" && window.innerWidth <= LAYOUT_STACK_BREAKPOINT_PX
  );

  let resizingLeft = false;
  let resizeStartX = 0;
  let resizeStartW = 0;

  let resizingMid = false;
  let midResizeStartX = 0;
  let midResizeStartW = 0;

  let resizeDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  function measureStacked() {
    layoutStacked.value = window.innerWidth <= LAYOUT_STACK_BREAKPOINT_PX;
  }

  /**
   * 在宽屏横向布局下，保证 左+中+右最小宽+间隙 不超过 .wrap，避免整页横向滚动。
   */
  function clampPanelsToFit() {
    if (layoutStacked.value) return;
    const wrap = document.querySelector(".app-literary .wrap") as HTMLElement | null;
    if (!wrap) return;
    const available = wrap.clientWidth;
    const maxLeftMid = available - RIGHT_MIN_FOR_ROW - HANDLES_AND_GAPS_PX;
    const floorPair = LEFT_MIN_WIDTH + MID_MIN_WIDTH;
    if (maxLeftMid < floorPair) {
      leftPanelWidth.value = LEFT_MIN_WIDTH;
      midPanelWidth.value = MID_MIN_WIDTH;
      return;
    }
    let L = leftPanelWidth.value;
    let M = midPanelWidth.value;
    if (L + M <= maxLeftMid) return;
    const overflow = L + M - maxLeftMid;
    const shrinkMid = Math.min(overflow, Math.max(0, M - MID_MIN_WIDTH));
    midPanelWidth.value = M - shrinkMid;
    const remain = overflow - shrinkMid;
    if (remain > 0) {
      leftPanelWidth.value = Math.max(LEFT_MIN_WIDTH, L - remain);
    }
  }

  function scheduleLayoutRefresh() {
    if (resizeDebounceTimer != null) clearTimeout(resizeDebounceTimer);
    resizeDebounceTimer = setTimeout(() => {
      resizeDebounceTimer = null;
      measureStacked();
      clampPanelsToFit();
    }, 80);
  }

  function onLeftResizeMove(e: MouseEvent) {
    if (!resizingLeft) return;
    const delta = e.clientX - resizeStartX;
    const next = Math.max(LEFT_MIN_WIDTH, Math.min(LEFT_MAX_WIDTH, resizeStartW + delta));
    leftPanelWidth.value = next;
    clampPanelsToFit();
  }

  function onLeftResizeUp() {
    if (!resizingLeft) return;
    resizingLeft = false;
    window.removeEventListener("mousemove", onLeftResizeMove);
    window.removeEventListener("mouseup", onLeftResizeUp);
    clampPanelsToFit();
  }

  function startResizeLeft(e: MouseEvent) {
    if (layoutStacked.value) return;
    resizingLeft = true;
    resizeStartX = e.clientX;
    resizeStartW = leftPanelWidth.value;
    window.addEventListener("mousemove", onLeftResizeMove);
    window.addEventListener("mouseup", onLeftResizeUp);
  }

  function onMidResizeMove(e: MouseEvent) {
    if (!resizingMid) return;
    const delta = e.clientX - midResizeStartX;
    const next = Math.max(MID_MIN_WIDTH, Math.min(MID_MAX_WIDTH, midResizeStartW + delta));
    midPanelWidth.value = next;
    clampPanelsToFit();
  }

  function onMidResizeUp() {
    if (!resizingMid) return;
    resizingMid = false;
    window.removeEventListener("mousemove", onMidResizeMove);
    window.removeEventListener("mouseup", onMidResizeUp);
    clampPanelsToFit();
  }

  function startResizeMid(e: MouseEvent) {
    if (layoutStacked.value) return;
    resizingMid = true;
    midResizeStartX = e.clientX;
    midResizeStartW = midPanelWidth.value;
    window.addEventListener("mousemove", onMidResizeMove);
    window.addEventListener("mouseup", onMidResizeUp);
  }

  onMounted(() => {
    measureStacked();
    clampPanelsToFit();
    window.addEventListener("resize", scheduleLayoutRefresh);
  });

  onBeforeUnmount(() => {
    onLeftResizeUp();
    onMidResizeUp();
    window.removeEventListener("resize", scheduleLayoutRefresh);
    if (resizeDebounceTimer != null) clearTimeout(resizeDebounceTimer);
  });

  return {
    leftPanelWidth,
    midPanelWidth,
    layoutStacked,
    startResizeLeft,
    startResizeMid,
  };
}
