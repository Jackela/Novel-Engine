# 测试分诊（462 → 重建）

> 阶段 0 产出 · 2026-10-24
> 扫描：server/tests + frontend/src + frontend/tests，共 508 个文件

## 判定标准

一句话：**这个测试失败时，是产品行为错了，还是文件结构变了？** 前者迁移，后者重写或丢弃。

## 统计

| 处置 | 文件数 | 含义 |
|---|---|---|
| 迁移 | 333 | 断言的是需求或不变量，可直接移植 |
| 重写 | 146 | 断言穿过已消失的层，需按新模块重写 |
| 保留 | 19 | e2e 旅程，合并后保留 |
| 丢弃 | 5 | 测已删功能或旧门禁 |
| 待定 | 5 | 需人工判断 |

## 迁移（333）

| 文件 | 行数 | 说明 |
|---|---|---|
| `frontend/src/app/AppCrashFallback.test.tsx` | 44 | 契约/工具函数 |
| `frontend/src/app/LanguageSwitch.test.tsx` | 66 | 契约/工具函数 |
| `frontend/src/app/ThemeSwitch.test.tsx` | 110 | 契约/工具函数 |
| `frontend/src/app/api.beat.test.ts` | 104 | 契约/工具函数 |
| `frontend/src/app/api.document.test.ts` | 42 | 契约/工具函数 |
| `frontend/src/app/api.pagination.test.ts` | 68 | 契约/工具函数 |
| `frontend/src/app/api.project.test.ts` | 141 | 契约/工具函数 |
| `frontend/src/app/api.retry.test.ts` | 72 | 契约/工具函数 |
| `frontend/src/app/api.test.ts` | 298 | 契约/工具函数 |
| `frontend/src/app/apiContract.projectShell.test.ts` | 77 | 契约/工具函数 |
| `frontend/src/app/apiContract.test.ts` | 65 | 契约/工具函数 |
| `frontend/src/app/apiDiagnosticsContract.test.ts` | 72 | 契约/工具函数 |
| `frontend/src/app/apiLoreExtractContract.test.ts` | 127 | 契约/工具函数 |
| `frontend/src/app/apiStatsContract.test.ts` | 133 | 契约/工具函数 |
| `frontend/src/app/apiUsageContract.test.ts` | 84 | 契约/工具函数 |
| `frontend/src/app/apiWorkflowContract.test.ts` | 186 | 契约/工具函数 |
| `frontend/src/app/i18n/dictionaries/dictionaries.test.ts` | 145 | i18n 键对齐 |
| `frontend/src/app/i18n/format.test.ts` | 46 | i18n 键对齐 |
| `frontend/src/app/i18n/language.prepaint.test.ts` | 157 | i18n 键对齐 |
| `frontend/src/app/i18n/language.test.ts` | 130 | i18n 键对齐 |
| `frontend/src/app/i18n/translate.test.ts` | 40 | i18n 键对齐 |
| `frontend/src/app/localizeError.test.ts` | 265 | 契约/工具函数 |
| `frontend/src/app/networkError.test.ts` | 31 | 契约/工具函数 |
| `frontend/src/app/pageRequest.test.ts` | 102 | 契约/工具函数 |
| `frontend/src/app/productBuildConfig.test.ts` | 35 | 契约/工具函数 |
| `frontend/src/app/productIdentity.test.ts` | 11 | 契约/工具函数 |
| `frontend/src/app/proposalStream.deadline.test.ts` | 151 | 契约/工具函数 |
| `frontend/src/app/proposalStream.idempotency.test.ts` | 84 | 契约/工具函数 |
| `frontend/src/app/proposalStream.lifecycle.test.ts` | 92 | 契约/工具函数 |
| `frontend/src/app/proposalStream.test.ts` | 314 | 契约/工具函数 |
| `frontend/src/app/retryAttemptRegistry.test.ts` | 95 | 契约/工具函数 |
| `frontend/src/app/theme.test.ts` | 193 | 契约/工具函数 |
| `frontend/src/app/themeContrast.contract.test.ts` | 185 | 契约/工具函数 |
| `frontend/src/app/themeTokens.contract.test.ts` | 138 | 契约/工具函数 |
| `server/tests/api/artifact_download_response_lifetime.test.ts` | 96 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/auth_csrf.test.ts` | 102 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/auth_helpers.ts` | 111 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/auth_rate_limit.test.ts` | 199 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/auth_rate_limit_encoded_paths.test.ts` | 136 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/auth_session.test.ts` | 316 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/auth_session_secret.test.ts` | 120 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/auth_setup.test.ts` | 326 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/config_startup.test.ts` | 154 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/cors_contract.test.ts` | 96 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/data_directory_ownership.test.ts` | 75 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/database_authority.test.ts` | 52 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/database_lifecycle.test.ts` | 95 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/error_envelope.test.ts` | 236 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/export_acknowledgement_failure.test.ts` | 58 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/export_capacity_error.test.ts` | 201 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/export_download_capacity_api.test.ts` | 128 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/export_job_failures.test.ts` | 320 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/export_publication_cleanup_restart.test.ts` | 116 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/export_publication_restart.test.ts` | 185 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/export_publication_restart_fixture.ts` | 187 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/export_retry_atomicity.test.ts` | 96 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/export_retry_capacity_api.test.ts` | 93 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/export_snapshot_identity.test.ts` | 92 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/export_source_invalidation.test.ts` | 103 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/generation_capacity_api.test.ts` | 277 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/generation_pipeline_boundary.test.ts` | 123 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/health.test.ts` | 217 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/job_retry_idempotency_contract.test.ts` | 225 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/job_retry_proposal_replay_evidence.test.ts` | 226 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/job_retry_review_export_replay_evidence.test.ts` | 233 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/job_test_helpers.ts` | 159 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/metrics_route.test.ts` | 116 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/project_deletion_concurrency.test.ts` | 269 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/project_deletion_proposal_lifecycle.test.ts` | 199 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/project_deletion_retry_concurrency.test.ts` | 103 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/proposal_generation_idempotency.test.ts` | 328 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/proposal_generation_idempotency_contract.test.ts` | 51 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/proposal_responses_status.test.ts` | 181 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/proposal_retry_base_revision_fidelity.test.ts` | 265 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/proposal_retry_replay_boundaries.test.ts` | 188 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/proposal_stream_capacity_lifecycle.test.ts` | 241 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/proposal_stream_completion.test.ts` | 193 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/proposal_stream_resource_lifecycle.test.ts` | 137 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/proposal_stream_response.test.ts` | 260 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/proposal_stream_response_heartbeat.test.ts` | 85 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/proposal_stream_response_helpers.ts` | 82 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/proposal_stream_responses_failure.test.ts` | 168 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/proposal_stream_session_helpers.ts` | 58 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/proposal_stream_stall_reason.test.ts` | 138 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/proposal_test_helpers.ts` | 70 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/provider_catalog.test.ts` | 133 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/retry_test_helpers.ts` | 14 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/review_app_wiring.test.ts` | 240 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/review_chapter_findings.test.ts` | 140 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/review_job_failures.test.ts` | 214 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/review_manuscript_input.test.ts` | 156 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/review_prompt_capacity.test.ts` | 192 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/review_provider_lifecycle.test.ts` | 97 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/review_source_invalidation.test.ts` | 147 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/revision_history_test_helper.ts` | 38 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/setup_proxy_origin.test.ts` | 66 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/spa_serving.test.ts` | 161 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/structure_capacity_seed_helpers.ts` | 80 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_beat_candidates.test.ts` | 70 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_beat_helpers.ts` | 88 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_beats.test.ts` | 271 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_capacity_admission.test.ts` | 298 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_capacity_error.test.ts` | 87 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_capacity_export_cleanup.test.ts` | 299 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_capacity_provider_cleanup.test.ts` | 215 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_capacity_provider_cleanup_helpers.ts` | 178 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_diagnostics.test.ts` | 332 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_document_save_conflicts.test.ts` | 73 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_documents.test.ts` | 307 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_exports.test.ts` | 257 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_exports_pagination_contract.test.ts` | 228 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_helpers.ts` | 327 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_import_capacity_error.test.ts` | 109 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_imports.test.ts` | 175 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_imports_confinement.test.ts` | 117 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_job_bridges.test.ts` | 315 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_job_detail.test.ts` | 178 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_jobs.test.ts` | 257 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_jobs_pagination_contract.test.ts` | 301 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_lore_aliases.test.ts` | 191 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_lore_extract.test.ts` | 224 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_lore_status.test.ts` | 172 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_lorebook_prompts.test.ts` | 190 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_operation_dedup.test.ts` | 325 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_project_catalog_cursor_contract.test.ts` | 82 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_project_catalog_pagination.test.ts` | 294 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_project_read_budget.test.ts` | 165 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_project_revision_pointer_integrity.test.ts` | 103 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_project_settings_openapi.test.ts` | 59 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_project_settings_update.test.ts` | 194 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_project_settings_validation.test.ts` | 175 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_project_shell_contract.test.ts` | 250 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_project_shell_openapi.test.ts` | 51 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_projects.test.ts` | 222 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_proposals.test.ts` | 312 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_proposals_accept_conflict.test.ts` | 67 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_proposals_accounting.test.ts` | 312 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_proposals_disconnect.test.ts` | 137 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_proposals_guards.test.ts` | 315 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_proposals_language.test.ts` | 134 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_proposals_stream.test.ts` | 318 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_proposals_stream_limits.test.ts` | 167 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_proposals_stream_retry.test.ts` | 133 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_proposals_stream_service.test.ts` | 316 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_proposals_stream_unconfigured.test.ts` | 45 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_proposals_usage_safety.test.ts` | 38 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_provider_failure_diagnostics.test.ts` | 252 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_resident_prompts.test.ts` | 337 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_review_model_override.test.ts` | 250 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_reviews.test.ts` | 320 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_reviews_pagination_contract.test.ts` | 254 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_revision_cursor_contract.test.ts` | 47 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_revision_pagination_contract.test.ts` | 311 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_revisions.test.ts` | 331 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_route_composition.test.ts` | 33 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_search.test.ts` | 303 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_search_bounds.test.ts` | 79 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_search_pagination.test.ts` | 148 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_search_ranking.test.ts` | 56 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_structure_capacity_api.test.ts` | 281 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_structure_capacity_scalars.test.ts` | 276 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_usage.test.ts` | 295 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_usage_provenance.test.ts` | 138 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_volumes.test.ts` | 283 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_volumes_order.test.ts` | 173 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/studio_writing_stats.test.ts` | 240 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/version.test.ts` | 191 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/api/volume_deletion_catalog_order.test.ts` | 57 | HTTP 契约 → inject + contracts 校验 |
| `server/tests/apps/cli/backup_policy_cli.test.ts` | 108 | CLI 命令契约 |
| `server/tests/apps/cli/cli.test.ts` | 324 | CLI 命令契约 |
| `server/tests/apps/cli/cli_database_authority.test.ts` | 131 | CLI 命令契约 |
| `server/tests/apps/cli/cli_env_file_failures.test.ts` | 116 | CLI 命令契约 |
| `server/tests/apps/cli/cli_export_recovery.test.ts` | 144 | CLI 命令契约 |
| `server/tests/apps/cli/cli_lifecycle.test.ts` | 134 | CLI 命令契约 |
| `server/tests/apps/cli/cli_shutdown_signals.test.ts` | 288 | CLI 命令契约 |
| `server/tests/apps/cli/doctor_readonly_cli.test.ts` | 204 | CLI 命令契约 |
| `server/tests/apps/cli/legacy_import_cli.test.ts` | 117 | CLI 命令契约 |
| `server/tests/apps/cli/migrate_cli.test.ts` | 125 | CLI 命令契约 |
| `server/tests/apps/cli/owner_reset_cli.test.ts` | 141 | CLI 命令契约 |
| `server/tests/apps/cli/restore_cli.test.ts` | 254 | CLI 命令契约 |
| `server/tests/apps/cli/shutdown_signal_fixtures.ts` | 40 | CLI 命令契约 |
| `server/tests/apps/cli/shutdown_signals.test.ts` | 47 | CLI 命令契约 |
| `server/tests/contexts/artifact_download_capacity.test.ts` | 56 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/beat_association_service.test.ts` | 317 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/dashscope_extractors.test.ts` | 37 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/dashscope_provider.test-helpers.ts` | 82 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/dashscope_provider.test.ts` | 191 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/dashscope_provider_timeout_floor.test.ts` | 85 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/dashscope_stream_extraction.test.ts` | 93 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/dashscope_transport.test.ts` | 116 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/deterministic_story_language.test.ts` | 115 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/direct_provider_model_defaults.test.ts` | 98 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/document_metadata_target_reads.test.ts` | 140 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_artifact_delivery_capacity.test.ts` | 167 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_artifact_docx_layout.test.ts` | 142 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_artifact_epub_package.test.ts` | 133 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_artifact_files.test.ts` | 314 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_artifact_identity.test.ts` | 71 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_artifact_markdown.test.ts` | 106 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_artifact_publication_capacity.test.ts` | 40 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_artifact_publication_ownership.test.ts` | 166 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_artifact_read_capacity.test.ts` | 83 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_artifact_service.test.ts` | 306 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_artifact_xml.test.ts` | 89 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_catalog_pagination.test.ts` | 295 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_outcome_transactions.test.ts` | 260 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_publication_authority_conflict.test.ts` | 58 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_publication_cleanup_journal_recovery.test.ts` | 213 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_publication_file_evidence.test.ts` | 120 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_publication_manifest_capacity.test.ts` | 87 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_publication_recovery.test.ts` | 324 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_publication_recovery_capacity.test.ts` | 101 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_publication_recovery_fixture.ts` | 137 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_renderer_capacity.test.ts` | 34 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_renderer_lifecycle.test.ts` | 189 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_renderer_permit.test.ts` | 20 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_renderer_retry_admission.test.ts` | 147 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_retry_capacity_outcome.test.ts` | 211 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_source_capacity.test.ts` | 272 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_source_identity.test.ts` | 42 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_source_revalidation.test.ts` | 243 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_store_catalog.test.ts` | 150 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_store_part.test.ts` | 313 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/export_store_transactions.test.ts` | 310 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/fts_match_query.test.ts` | 58 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/generation_capacity.test.ts` | 132 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/generation_capacity_admission.test.ts` | 137 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/generation_digest_capacity.test.ts` | 47 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/generation_prompt_boundary.test.ts` | 117 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/generation_retry_capacity_outcome.test.ts` | 95 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/legacy_import_demo_workspace.test.ts` | 126 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/legacy_import_service.test.ts` | 266 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/legacy_workspace_reader.test.ts` | 229 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/legacy_workspace_reader_bounds.test.ts` | 164 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/legacy_workspace_reader_identity.test.ts` | 100 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/lore_alias_service.test.ts` | 293 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/lore_injection.test.ts` | 261 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/lore_planner.test.ts` | 135 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/lorebook.test.ts` | 329 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/lorebook_init_capacity.test.ts` | 112 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/lorebook_init_extract.test.ts` | 163 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/lorebook_init_harness.ts` | 111 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/lorebook_init_reexecute.test.ts` | 248 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/lorebook_init_retry.test.ts` | 277 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/model_resolution.test.ts` | 114 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/openai_compatible_provider.test.ts` | 273 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/operation_in_flight.test.ts` | 150 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/outline_beats.test.ts` | 96 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/payload_guard_harness.ts` | 186 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/payload_schema_guard.test.ts` | 144 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/payload_schema_guard_batch2.test.ts` | 172 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/project_artifact_files.test.ts` | 159 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/project_settings_update.test.ts` | 233 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/project_shell_store.test.ts` | 209 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/proposal_acceptance_transactions.test.ts` | 295 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/proposal_context_pipeline.test.ts` | 263 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/proposal_context_store.test.ts` | 224 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/proposal_writing_language.test.ts` | 163 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/provider_external_cancellation.test.ts` | 232 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/provider_failure_body.test.ts` | 184 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/provider_http.test.ts` | 206 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/provider_payload.test.ts` | 63 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/provider_proposal_limits.test.ts` | 35 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/provider_response_bounds.test.ts` | 168 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/provider_response_cleanup_races.test.ts` | 120 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/provider_response_deadline.test.ts` | 108 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/provider_scaffold.test.ts` | 194 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/provider_sse_boundaries.test.ts` | 58 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/provider_streaming.test.ts` | 320 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/provider_streaming_completion.test.ts` | 171 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/provider_streaming_deadline.test.ts` | 75 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/provider_streaming_failures.test.ts` | 134 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/provider_streaming_retry.test.ts` | 140 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/provider_streaming_terminal_frames.test.ts` | 232 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/provider_streaming_timeouts.test.ts` | 291 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/provider_usage_safety.test.ts` | 149 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/resident_context.test.ts` | 322 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/resident_context_render_lazy.test.ts` | 32 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/review_outcome_harness.ts` | 107 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/review_page_harness.ts` | 128 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/review_page_query_budget.test.ts` | 120 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/review_prompt_capacity.test.ts` | 76 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/review_rules.test.ts` | 152 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/review_service.test.ts` | 312 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/review_store_pagination.test.ts` | 157 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/review_store_transactions.test.ts` | 224 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/revision_retention.test.ts` | 151 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/revision_retention_harness.ts` | 190 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/revision_retention_prune.test.ts` | 123 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/revision_service.test.ts` | 300 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/revision_source.test.ts` | 44 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/revision_store_pagination.test.ts` | 243 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/revision_word_count.test.ts` | 72 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/safe_usage_persistence.test.ts` | 177 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/sanitization.test.ts` | 329 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/stream_json_unwrap.test.ts` | 88 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/studio_failure_classification.test.ts` | 213 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/studio_operation_capacity.test.ts` | 315 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/text_generation.test-helpers.ts` | 20 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/text_generation.test.ts` | 234 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/text_generation_stream_budgets.test.ts` | 112 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/volume_service.test.ts` | 182 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/volume_service_harness.ts` | 177 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/writing_stats_calendar.test.ts` | 330 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/writing_stats_harness.ts` | 188 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/contexts/writing_stats_service.test.ts` | 145 | 用例/领域行为 → 拆分到 domain + usecase |
| `server/tests/db/backup_policy.test.ts` | 99 | schema/事务 → adapter 测试 |
| `server/tests/db/configured_database_authority.test.ts` | 53 | schema/事务 → adapter 测试 |
| `server/tests/db/data_directory_lock.test.ts` | 109 | schema/事务 → adapter 测试 |
| `server/tests/db/export_snapshot_cleanup.test.ts` | 191 | schema/事务 → adapter 测试 |
| `server/tests/db/job_event_sequence_backfill.test.ts` | 98 | schema/事务 → adapter 测试 |
| `server/tests/db/lore_status_backfill.test.ts` | 114 | schema/事务 → adapter 测试 |
| `server/tests/db/restart_persistence.test.ts` | 200 | schema/事务 → adapter 测试 |
| `server/tests/db/review_snapshot_cleanup.test.ts` | 171 | schema/事务 → adapter 测试 |
| `server/tests/db/revision_word_count_reconciliation.test.ts` | 249 | schema/事务 → adapter 测试 |
| `server/tests/db/safe_usage_tokens_migration.test.ts` | 87 | schema/事务 → adapter 测试 |
| `server/tests/db/startup_pipeline.test.ts` | 329 | schema/事务 → adapter 测试 |
| `server/tests/db/volume_backfill.test.ts` | 117 | schema/事务 → adapter 测试 |
| `server/tests/infrastructure/client_identity.test.ts` | 90 | 基础设施行为保持 |
| `server/tests/infrastructure/env_values.test.ts` | 92 | 基础设施行为保持 |
| `server/tests/infrastructure/error_code.test.ts` | 28 | 基础设施行为保持 |
| `server/tests/infrastructure/provider_config.test.ts` | 158 | 基础设施行为保持 |
| `server/tests/infrastructure/server_config.test.ts` | 255 | 基础设施行为保持 |
| `server/tests/infrastructure/server_config_capacity.test.ts` | 85 | 基础设施行为保持 |
| `server/tests/infrastructure/server_config_env_file_failures.test.ts` | 170 | 基础设施行为保持 |
| `server/tests/infrastructure/server_config_helpers.ts` | 56 | 基础设施行为保持 |
| `server/tests/infrastructure/server_config_production.test.ts` | 112 | 基础设施行为保持 |
| `server/tests/infrastructure/server_config_workspace_root.test.ts` | 96 | 基础设施行为保持 |
| `server/tests/infrastructure/setup_token.test.ts` | 92 | 基础设施行为保持 |
| `server/tests/infrastructure/sqlite_diagnostics_health.test.ts` | 63 | 基础设施行为保持 |
| `server/tests/infrastructure/sqlite_health_probe.test.ts` | 48 | 基础设施行为保持 |
| `server/tests/infrastructure/token_bucket.test.ts` | 100 | 基础设施行为保持 |
| `server/tests/infrastructure/workspace_manifest.test.ts` | 115 | 基础设施行为保持 |

## 重写（146）

| 文件 | 行数 | 说明 |
|---|---|---|
| `frontend/src/features/studio/EditorInspectorTheme.contract.test.tsx` | 130 | 页面装配变化 |
| `frontend/src/features/studio/EntryPage.explainer.test.tsx` | 48 | 页面装配变化 |
| `frontend/src/features/studio/EntryPage.i18n.test.tsx` | 143 | 页面装配变化 |
| `frontend/src/features/studio/EntryPage.lifecycle.test.tsx` | 234 | 页面装配变化 |
| `frontend/src/features/studio/EntryPage.owner-creation.test.tsx` | 155 | 页面装配变化 |
| `frontend/src/features/studio/EntryPage.session-expiry.test.tsx` | 88 | 页面装配变化 |
| `frontend/src/features/studio/EntryPage.unmount.test.tsx` | 169 | 页面装配变化 |
| `frontend/src/features/studio/MarkdownEditor.test.tsx` | 127 | 页面装配变化 |
| `frontend/src/features/studio/ProductBrand.test.tsx` | 53 | 页面装配变化 |
| `frontend/src/features/studio/ProjectLibraryPage.actions.test.tsx` | 254 | 页面装配变化 |
| `frontend/src/features/studio/ProjectLibraryPage.deletion.test.tsx` | 179 | 页面装配变化 |
| `frontend/src/features/studio/ProjectLibraryPage.lifecycle.test.tsx` | 259 | 页面装配变化 |
| `frontend/src/features/studio/ProjectLibraryPage.pagination.test.tsx` | 230 | 页面装配变化 |
| `frontend/src/features/studio/StudioComponents.test.tsx` | 287 | 页面装配变化 |
| `frontend/src/features/studio/StudioEditorPane.test.tsx` | 326 | 页面装配变化 |
| `frontend/src/features/studio/StudioInspector.lore-identity.test.tsx` | 145 | 页面装配变化 |
| `frontend/src/features/studio/StudioInspector.lore-tab.test.tsx` | 114 | 页面装配变化 |
| `frontend/src/features/studio/StudioNavigator.focus.test.tsx` | 198 | 页面装配变化 |
| `frontend/src/features/studio/StudioNavigator.pending.test.tsx` | 90 | 页面装配变化 |
| `frontend/src/features/studio/StudioNavigator.rowCommands.test.tsx` | 230 | 页面装配变化 |
| `frontend/src/features/studio/StudioNavigator.test.tsx` | 312 | 页面装配变化 |
| `frontend/src/features/studio/StudioNavigator.volumes.test.tsx` | 296 | 页面装配变化 |
| `frontend/src/features/studio/StudioPage.test.tsx` | 273 | 页面装配变化 |
| `frontend/src/features/studio/components/ClipboardCopyButton.test.tsx` | 99 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioBeatPanel.project-scope.test.tsx` | 112 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioBeatPanel.test.tsx` | 311 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioBodyBudget.test.tsx` | 54 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioCopilotPanel.clipboard.test.tsx` | 61 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioCopilotPanel.streaming.test.tsx` | 117 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioCopilotPanel.test.tsx` | 267 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioExportPanel.test.tsx` | 257 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioHistoryPanel.preview.test.tsx` | 195 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioHistoryPanel.restore.test.tsx` | 207 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioHistoryPanel.test.tsx` | 237 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioJobsPanel.error-details.test.tsx` | 44 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioJobsPanel.proposal-text.test.tsx` | 160 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioJobsPanel.test.tsx` | 321 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioLoreStatusPanel.identity.test.tsx` | 129 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioLoreStatusPanel.test.tsx` | 290 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioLorebookWizardPanel.test.tsx` | 308 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioNavigatorSearch.test.tsx` | 96 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioOfflineNotice.test.tsx` | 54 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioReviewHistoryList.test.tsx` | 102 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioReviewPanel.empty.test.tsx` | 36 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioReviewPanel.test.tsx` | 145 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioSavedSourceNotice.test.tsx` | 51 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioSettingsPanel.diagnostics.test.tsx` | 103 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioSettingsPanel.i18n.test.tsx` | 45 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioSettingsPanel.test.tsx` | 219 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioUsagePanel.test.tsx` | 199 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioWholeBookControl.confirm.test.tsx` | 152 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioWholeBookControl.i18n.test.tsx` | 109 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioWholeBookControl.test.tsx` | 262 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/components/StudioWritingStatsPanel.test.tsx` | 194 | 组件重写后 props 形状改变 |
| `frontend/src/features/studio/hooks/acceptProposalAndRefresh.test.ts` | 111 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/keysetHistory.test.tsx` | 78 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/retryReview.test.tsx` | 158 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/studioPageModelView.test.ts` | 82 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/studioSearchModel.selection.test.tsx` | 163 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/toErrorMessage.test.ts` | 107 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useActiveDocument.test.tsx` | 110 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useCurrentDocument.ownership.test.tsx` | 269 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useCurrentDocument.test.tsx` | 335 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useCurrentDocument.unexpected.test.tsx` | 132 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useDiagnosticsDownload.test.tsx` | 222 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useDocumentDraft.autosave-recovery.test.tsx` | 328 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useDocumentDraft.autosaveRecoveryOrdering.test.tsx` | 219 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useDocumentDraft.conflict.test.tsx` | 274 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useDocumentDraft.external.test.tsx` | 307 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useDocumentDraft.identity.test.tsx` | 330 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useDocumentDraft.lifecycle.test.tsx` | 233 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useDocumentDraft.loadLatest.test.tsx` | 203 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useDocumentDraft.reconciliation.test.tsx` | 350 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useDocumentDraft.refreshOrdering.test.tsx` | 205 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useDocumentDraft.selection.test.tsx` | 227 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useDocumentDraft.test.tsx` | 339 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useExportDownload.lifecycle.test.tsx` | 286 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useExportDownload.test.tsx` | 284 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useExportHistory.test.tsx` | 262 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useLazyInspectorHistories.test.tsx` | 168 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useLorebookWizard.confirm.test.tsx` | 158 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useLorebookWizard.test.tsx` | 248 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useOwnerKeyedErrors.test.tsx` | 118 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useProjectErrorOwnership.test.tsx` | 95 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useProjectLibraryBootstrap.test.tsx` | 96 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useProjectSettingsUpdate.test.tsx` | 260 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useProjectUsage.test.tsx` | 159 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useReviewHistory.test.tsx` | 291 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useRevisionCache.errors.test.tsx` | 162 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useRevisionCache.lru.test.tsx` | 177 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useRevisionCache.pagination.test.tsx` | 316 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useRevisionCache.subscribers.test.tsx` | 169 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useRevisionCache.test.tsx` | 251 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useRevisionPreview.test.tsx` | 122 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useScopedRevisionRestore.test.tsx` | 101 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioActions.concurrency.test.tsx` | 171 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioActions.lifecycle.test.tsx` | 90 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioActions.lore-identity.test.tsx` | 259 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioActions.narrow-matrix.test.tsx` | 259 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioActions.pending-identity.test.tsx` | 146 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioActions.proposal-audit.test.tsx` | 60 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioActions.retry-idempotency.test.tsx` | 247 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioActions.test.tsx` | 325 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioChapterPlacement.test.tsx` | 264 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioDocumentActions.test.tsx` | 294 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioDocumentDeletion.test.tsx` | 200 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioGeneration.revisionAuthority.test.tsx` | 84 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioInspectorState.test.tsx` | 191 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioJobs.audit-identity.test.tsx` | 73 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioJobs.lifecycle.test.tsx` | 155 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioJobs.pagination.test.tsx` | 218 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioPageModel.conflict-preview.test.tsx` | 137 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioPageModel.lore-status.test.tsx` | 113 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioPageModel.lore-wizard.test.tsx` | 159 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioPageModel.proposal-undo.test.tsx` | 176 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioPageModel.proposalAcceptanceOrdering.test.tsx` | 287 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioPageModel.request-ledger.test.tsx` | 334 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioPageModel.rowCommands.test.tsx` | 158 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioPageModel.saved-source.test.tsx` | 132 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioPageModel.unpersisted-loading.test.tsx` | 185 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioPageModel.volumes.test.tsx` | 219 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioPageModel.whole-book-resume.test.tsx` | 352 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioProject.retry.test.tsx` | 153 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioProject.shellAuthority.test.tsx` | 110 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioProject.test.tsx` | 325 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioProposal.idempotency.test.tsx` | 107 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioProposal.identity.test.tsx` | 313 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioProposal.test.tsx` | 248 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioProposal.unknown.test.tsx` | 279 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioProviders.test.tsx` | 144 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useStudioSearchJobs.test.tsx` | 302 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useWholeBookLoop.acceptanceOrdering.test.tsx` | 84 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useWholeBookLoop.confirm.test.tsx` | 201 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useWholeBookLoop.run.test.tsx` | 295 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useWholeBookLoop.stop.test.tsx` | 251 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useWholeBookLoop.unknown.test.tsx` | 201 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/useWritingStats.test.tsx` | 162 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/hooks/wholeBookPlan.test.ts` | 120 | 测 hook 实现细节 → 模块行为测试 |
| `frontend/src/features/studio/studioRouteState.test.ts` | 67 | 页面装配变化 |
| `server/tests/contexts/diagnostics_service.test.ts` | 216 | job/diagnostics 语义变更 |
| `server/tests/contexts/job_history_summary_service.test.ts` | 134 | job/diagnostics 语义变更 |
| `server/tests/contexts/job_replay_payload.test.ts` | 169 | job/diagnostics 语义变更 |
| `server/tests/contexts/job_retry_idempotency.test.ts` | 300 | job/diagnostics 语义变更 |
| `server/tests/contexts/job_retry_scope_matrix.test.ts` | 162 | job/diagnostics 语义变更 |
| `server/tests/contexts/job_store_pagination.test.ts` | 240 | job/diagnostics 语义变更 |
| `server/tests/contexts/job_store_transactions.test.ts` | 283 | job/diagnostics 语义变更 |

## 保留（19）

| 文件 | 行数 | 说明 |
|---|---|---|
| `frontend/tests/e2e-ts/content_acceptance_helpers.ts` | 244 | 合并为 6 条主旅程 |
| `frontend/tests/e2e-ts/project_document_helpers.ts` | 158 | 合并为 6 条主旅程 |
| `frontend/tests/e2e-ts/studio-ts.spec.ts` | 331 | 合并为 6 条主旅程 |
| `frontend/tests/e2e-ts/studio_content.spec.ts` | 307 | 合并为 6 条主旅程 |
| `frontend/tests/e2e-ts/theme_selection.spec.ts` | 239 | 合并为 6 条主旅程 |
| `frontend/tests/e2e-ts/whole_book.spec.ts` | 145 | 合并为 6 条主旅程 |
| `frontend/tests/e2e-ts/workflows/studio_conflict_preview.spec.ts` | 92 | 合并为 6 条主旅程 |
| `frontend/tests/e2e-ts/workflows/studio_content_search.spec.ts` | 142 | 合并为 6 条主旅程 |
| `frontend/tests/e2e-ts/workflows/studio_diagnostics_export.spec.ts` | 177 | 合并为 6 条主旅程 |
| `frontend/tests/e2e-ts/workflows/studio_failure_isolation.spec.ts` | 383 | 合并为 6 条主旅程 |
| `frontend/tests/e2e-ts/workflows/studio_lorebook_wizard.spec.ts` | 268 | 合并为 6 条主旅程 |
| `frontend/tests/e2e-ts/workflows/studio_navigation_layout.spec.ts` | 105 | 合并为 6 条主旅程 |
| `frontend/tests/e2e-ts/workflows/studio_reorder.spec.ts` | 219 | 合并为 6 条主旅程 |
| `frontend/tests/e2e-ts/workflows/studio_review_export.spec.ts` | 204 | 合并为 6 条主旅程 |
| `frontend/tests/e2e-ts/workflows/studio_row_commands.spec.ts` | 287 | 合并为 6 条主旅程 |
| `frontend/tests/e2e-ts/workflows/studio_saved_source_feedback.spec.ts` | 168 | 合并为 6 条主旅程 |
| `frontend/tests/e2e-ts/workflows/studio_switch.spec.ts` | 125 | 合并为 6 条主旅程 |
| `frontend/tests/e2e-ts/workflows/studio_usage.spec.ts` | 298 | 合并为 6 条主旅程 |
| `frontend/tests/e2e-ts/workflows/studio_writing_stats.spec.ts` | 255 | 合并为 6 条主旅程 |

## 丢弃（5）

| 文件 | 行数 | 说明 |
|---|---|---|
| `server/tests/qa/compose_passthrough_gate.test.ts` | 327 | 门禁重写，旧断言失效 |
| `server/tests/qa/error_codes_gate.test.ts` | 151 | 门禁重写，旧断言失效 |
| `server/tests/qa/openapi_snapshot.test.ts` | 81 | 门禁重写，旧断言失效 |
| `server/tests/qa/qa_gate_regressions.test.ts` | 308 | 门禁重写，旧断言失效 |
| `server/tests/qa/ssot_gate.test.ts` | 252 | 门禁重写，旧断言失效 |

## 待定（5）

| 文件 | 行数 | 说明 |
|---|---|---|
| `frontend/tests/setup.ts` | 13 |  |
| `server/tests/apps/api/inbound_request_lifetime.test.ts` | 317 |  |
| `server/tests/apps/provider_runtime.test.ts` | 63 |  |
| `server/tests/credential_fixtures.ts` | 29 |  |
| `server/tests/legacy_workspace_fixtures.ts` | 56 |  |

## 执行规则

1. 删除任何测试文件前，必须在 `requirements-matrix.md` 或 `invariants.md` 里指出接替者。
2. 「重写」不是直接删，先把断言意图抄进新测试，再删旧文件。
3. `server/tests/qa/` 的 5 个门禁自测随门禁一起重写，不单独迁移。
4. e2e 的 17 个 spec 合并为 6 条：登录、写作与保存、提案接受、修订恢复、导出、搜索。
5. 覆盖率阈值在重建期间按切片计算，不按包聚合，避免中间态误报。
