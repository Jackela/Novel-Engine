/**
 * 任务面板文案（DR-010：已完成提案行可懒加载阅读提案正文）。
 * 独立分块以便 studio 字典保持在文件行数预算内；与 `en.jobs.ts` 键集镜像。
 */
export const zhJobs = {
  "jobs.heading": "任务",
  "jobs.hint": "持久化操作的执行状态。",
  "jobs.action.refresh": "刷新任务",
  "jobs.action.refreshing": "正在刷新任务",
  "jobs.action.retry": "重试 {operation}",
  "jobs.action.retrying": "正在重试 {operation}",
  "jobs.action.retryTitle": "重试任务",
  "jobs.action.loadOlder": "加载更早的任务",
  "jobs.action.loadingOlder": "正在加载更早的任务",
  "jobs.empty": "暂无任务。",
  "jobs.row.meta": "{provider} · {date}",
  "jobs.proposal.copy": "复制",
  "jobs.proposal.error": "无法加载该提案。",
  "jobs.proposal.loading": "正在加载提案文本…",
  "jobs.proposal.view": "查看提案文本",
  // DR-021：服务端原始失败报告（英文，可能含 provider HTTP 细节）收在折叠区内。
  "jobs.error.failed": "该任务失败。",
  "jobs.error.technicalDetails": "技术详情",
};
