/** Electron preload 注入的桌面能力（仅安装版窗口内存在） */

export type OpenPathResult = { ok: boolean; error?: string };

export type NovelAgentDesktopApi = {
  mode: string;
  openPath?: (targetPath: string) => Promise<OpenPathResult>;
};

export function getNovelAgentDesktop(): NovelAgentDesktopApi | undefined {
  return (window as unknown as { novelAgentDesktop?: NovelAgentDesktopApi }).novelAgentDesktop;
}
