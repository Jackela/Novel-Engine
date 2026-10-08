# 最终候选首次前端全量的失败观测

候选：0799ddf8909dd28f9c31dd72e418636c5a7a8992。
来源：本轮 functions.exec → exec_command 会话92290的实际输出。该链式命令在失败前尚未进入末尾构建的输出重定向，因此原输出在工具响应，未生成 frontend-frozen.log；此记录保留实际关键结果，不伪装成重新执行的原日志。

类型、Biome lint、oxlint、format 均通过。执行 `pnpm --dir frontend test:unit --coverage`，163文件中162通过、1失败；890测试中889通过、1失败。失败为 `src/features/studio/hooks/useStudioPageModel.request-ledger.test.tsx:179` 的 `reads one shell plus one route-compatible active Document and keeps every other resource lazy`，原因 `Test timed out in 5000ms`，实际5146ms。启动17:17:21，耗时56.90s。

原断言和阈值未变；显式限定 maxWorkers=2 后全量163文件／890测试通过，日志 frontend-frozen-replay.log。此失败不证明产品请求账本断言错误，不能删除失败记录或降低断言来换取通过。机器发生长时间中断，因此仅以隔离重跑结果说明本轮验证，不宣称已定位所有超时根因。
