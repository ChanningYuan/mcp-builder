# 脚手架 MCP 工具速查

skill 通过「MCP 开发脚手架」（serverName=`mcp-kit`）这个 MCP 的工具来建/管理别的 MCP。本文档是这些工具的参数、出参与用法速查。三段式入参见 `api-to-tool.md`，映射见 `mapping-rules.md`，鉴权与凭证见 `auth-credentials.md`。

## 主键约定

- **服务**主键 = `mcpId`（数字，`mcp_service_create` 返回）。所有服务级/工具级操作都传它。
- **工具**主键 = `toolId`（`G-ACT-*`）。入参、出参两侧统一叫 `toolId`（tool_list/versions 返回的元素里也是）。
- **凭证**主键 = `credentialId`（数字，`mcp_credential_save` 返回）。
- `serverName` = 服务的英文标识名（即 CLI 一级命令组名），可选；kebab-case、组织内唯一、1-255 字符（正则 `^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$`，归一小写）。格式非法报 `business_error_invalid_params`，重名报 `serverName already exists in this organization`。
- 身份注入：调用者 corpId/userId 由平台系统参数注入，工具入参不暴露、权限跟人走。

## 出参统一规范

- **每只工具出参都含三件套**：`success`(工具调用是否成功) / `errorCode` / `errorMsg`——负向判读靠它们；下表「出参」列只列三件套**之外**的业务字段。
- **写操作 9 只**（service_update/delete、tool_update/delete/publish、credential_bind/delete、member_add/remove）出参**仅三件套**，success=true 即生效。
- **分页 4 只**（service_list/tool_list/credential_list/tool_versions）：列表与分页字段全部**平铺在顶层**——`services`/`tools`/`credentials`/`versions` + `hasMore`/`nextCursor`/`totalCount`，没有 result/list 嵌套。

## 工具表（按组）

### 服务管理（5）

| 工具 | 必填参数 | 出参（三件套外） | 用途 |
|------|----------|------------------|------|
| `mcp_service_create` | name, description | `mcpId`(number) | 新建 MCP 服务（服务是工具的容器）。可选 icon_url / introduction / **serverName** |
| `mcp_service_list` | —（可选 keyword/creatorUserId/cursor/pageSize） | `services`(array) + 分页三字段 | 我有开发权限的服务列表（主管理员=组织全部；开发者=自建+协作）。⚠️ 偶发瞬态返回空（重索引），重试即好 |
| `mcp_service_get` | mcpId | `service`(object) | 服务详情（name/description/serverName/creatorUserId 等） |
| `mcp_service_update` | mcpId | 仅三件套 | 改服务基本信息（name/description/icon_url/introduction/serverName）。只传要改的字段 |
| `mcp_service_delete` | mcpId | 仅三件套 | **写·高**。删整个服务。服务下还有工具会被拒（`mcp_has_tools`），须先逐个删工具。需用户明确同意 |

### 工具管理（8）

| 工具 | 必填参数 | 出参（三件套外） | 用途 |
|------|----------|------------------|------|
| `mcp_tool_create_http` | mcpId, name, title, description, **httpInfo**, apiInputs, toolInputs, inputMappings, apiOutputs, toolOutputs, outputMappings（11 项必填；可选 **timeout**/**onlyOriginalKeys**） | `toolId`(string) | 建 **http 型**工具，**存草稿**。三段式见 api-to-tool.md |
| `mcp_tool_debug` | mcpId, toolId, value（可选 versionId；**带鉴权必传 credentialId**） | **`executeSuccess`(分水岭)**, **`toolOutput`(object,判读位)**, `toolInput`, `rawOutput`, `time` | **草稿态即可真跑**。value 直接是入参对象（不包 Body 层）。映射后结果看顶层 `toolOutput`。⚠️`rawOutput` **不是**映射前原始响应（是 toolOutput 外包一层 Body，映射取不到值时同样为空）——判据表与排障见 troubleshooting.md |
| `mcp_tool_publish` | mcpId, toolId | 仅三件套 | **写·闸门**。草稿转正线上版。发布时做出参 schema 向后兼容校验。发布前必须用户复核。⚠️ 带鉴权服务必须**先 `mcp_credential_bind` 再 publish**——顺序反了实例卡草稿态且不可恢复（auth-credentials.md） |
| `mcp_tool_update_http` | mcpId, toolId + create_http 同款必填集（可选 timeout/onlyOriginalKeys） | 仅三件套 | 编辑 http 工具，**全量提交**（漏字段=清空；仅 timeout/onlyOriginalKeys 例外：漏传=保留原值）。先 get 读回（读回即三段式，可直接改后提交） |
| `mcp_tool_list` | mcpId（可选 keyword/cursor/pageSize） | `tools`(array，元素含 `toolId`/status 三态) + 分页三字段 | status：`draft` / `published` / `published_with_draft`（有未发布新草稿，versionId 指草稿） |
| `mcp_tool_get` | mcpId, toolId（可选 versionId） | `tool`(object：含 toolType、httpInfo、timeout/onlyOriginalKeys、**三段式六件套**(apiInputs/toolInputs/inputMappings/apiOutputs/toolOutputs/outputMappings)) | **三段式读回**：读回内容可直接修改后经 `mcp_tool_update_http` 提交。update 前必调 |
| `mcp_tool_versions` | mcpId, toolId | `versions`(array，元素含 `toolId`/versionId/versionNo/status) + 分页三字段 | 版本历史；回滚场景先在此找 versionId |
| `mcp_tool_delete` | mcpId, toolId | 仅三件套 | **写·高**。草稿/已发布未上架可删；已上架市场被拒（`tool_already_listed_in_market`）。需确认 |

### 鉴权配置与凭证账号（9）—— 用法详见 `auth-credentials.md`

| 工具 | 必填参数 | 出参（三件套外） | 用途 |
|------|----------|------------------|------|
| `mcp_auth_config_save` | mcpId, authType（+对应 xxxAuthConfig） | `authConfig`(object) | 配服务级"鉴权说明书"。authType：NO_AUTH/BASIC/API_SECRET/TOKEN/SIGNATURE |
| `mcp_auth_config_get` | mcpId | `authConfig`(object) | 查当前鉴权配置（authType + authFields 字段清单） |
| `mcp_credential_save` | mcpId, name, content | `credentialId`(number), `credentialName` | 建/改凭证（真实密钥）。传 credentialId=更新。TOKEN 型保存时**真实换 token**。content 缺 authFields 必填字段**保存时即拒**（credential_missing_required_field，中文提示缺哪个字段） |
| `mcp_credential_list` | mcpId（可选 cursor/pageSize） | `credentials`(array) + 分页三字段 | 凭证列表（仅元信息）。按当前 authConfig 版本过滤 |
| `mcp_credential_get` | mcpId, credentialId | `credential`(object：id/name/editable/gmtCreate) | 单凭证详情。⚠️ 无法查凭证被引用数 |
| `mcp_credential_debug` | mcpId, credentialId | **`executeSuccess`**(HTTP 2xx 判定), `executeErrorMsg`, `detail`(object) | 凭证质检真跑 testRequest。executeSuccess=探测请求 HTTP 2xx 判定（非 2xx 为 false）；返回体内业务错误（errcode）不计入，需结合 detail.response 复核 |
| `mcp_credential_bind` | mcpId, credentialId | 仅三件套 | 凭证设为**正式实例**生效凭证。⚠️ debug 链路不吃 bind。⚠️ 必须在 `mcp_tool_publish` **之前**调用——先 publish 后 bind 实例卡草稿态、取不到地址且不可恢复 |
| `mcp_credential_unbind` | mcpId | 仅三件套 | 解绑实例生效凭证（bind 逆操作），幂等。⚠️ 服务从未配置鉴权时返回 NOT_FOUND「MCP不存在」——是实例凭证配置记录不存在，非服务不存在。场景：delete 报 credential_in_use 时先 unbind 再删 |
| `mcp_credential_delete` | mcpId, credentialId | 仅三件套 | **写·高**。删被绑定凭证被拒 `credential_in_use`（解锁=先 `mcp_credential_unbind`）。删除仍需向用户确认 |

### 成员管理（3）

| 工具 | 必填参数 | 出参（三件套外） | 用途 |
|------|----------|------------------|------|
| `mcp_member_list` | mcpId | `members`(array，**成员 userId 字符串数组**) | 成员（开发协作者）列表。owner 是独立身份不一定在列 |
| `mcp_member_add` | mcpId, memberUserIds | 仅三件套 | **增量**新增（staffId 数组）。空数组=no-op；不在组织报 `member_not_found` |
| `mcp_member_remove` | mcpId, memberUserIds | 仅三件套 | **写·高**。增量移除（权限撤销）。移除自己可能立即失去管理权限。先 list 复述再执行 |

### 接入地址（1）

| 工具 | 必填参数 | 出参（三件套外） | 用途 |
|------|----------|------------------|------|
| `mcp_server_url_get` | mcpId, source | `mcpUrl`(string), `mcpJson`(string) | source=`PUBLISHED`（已发布到企业、开发验证用）/ `MARKET`（已上架市场）。⚠️ 返回的是调用者**个人身份**实例地址（含个人 key 勿外发）。⚠️ success=true 但**无 mcpUrl**=带鉴权服务发布前没 bind（卡草稿态）——重建工具按「先 bind 再 publish」重发布。⚠️ **0 个已发布工具时仍返回完整 mcpUrl**（平台已知缺口）——该 URL tools/list 报 `PARAM_ERROR`、tools/call `not found the specified tool` 且 isError=false，取址前先 `mcp_tool_list` 核对发布数 |

## debug 的版本选择与鉴权（两大假阳性坑）

1. **版本选择规则**：不传 `versionId` 时——工具只要**发布过**（含 `published_with_draft` 态），就调**已发布老版本**，绝不自动挑最新草稿；只有从未发布过才退到调草稿。**调正在编辑的草稿必须显式传草稿 versionId**（`mcp_tool_get` 读回获取），否则"调试通过"测的其实是旧版本。
2. **鉴权凭证**：`mcp_tool_debug` **不使用 bind 结果**，服务配了鉴权时**必须显式传 `credentialId`**；不传则按"无账号"降级直连（TOKEN 注入配置原文、BASIC 静默不注入——全是误导性假症状）。

## 状态机（工具的生命周期）

```
mcp_tool_create_http → draft ──mcp_tool_debug(真跑验证)──> draft ──mcp_tool_publish──> published
                                                                          │
        mcp_tool_update_http ──> 草稿（无则新建，有则覆盖同一份）──────┘（需再 publish）
```

- **create/update 只产草稿**，草稿不影响线上；update 已有草稿时覆盖同一份（不新增版本）；
- **debug 在草稿态就能真跑**（真实调用下游接口，写操作类先备测试数据）；
- **publish 才生效**；发布后 status=`published`，再 update 会进入 `published_with_draft`。

## source=PUBLISHED 的意义（publish ≠ 上架）

- **publish（发布到企业）**：`mcp_tool_publish` 后，服务在企业内即可用。这一步就够了。
- **上架市场**：是另一件事（把 MCP 上到钉钉 MCP 市场），跟「能不能用」无关，本 skill 不涉及。
- 取新建服务的地址：`mcp_server_url_get(mcpId, source="PUBLISHED")` —— 直接拿到「已发布到企业、未上架市场」服务的可用地址（出参 `mcpUrl`），无需上架、无需外部工具，agent 全程自助闭环。

### 实例双轨道机制（实测印证）

同一个服务有**两条版本轨道**，`mcp_server_url_get` 的 `source` 决定拿哪条轨道的实例地址：

| source | 实例 | 里面的工具能力 |
|--------|------|----------------|
| `PUBLISHED` | 企业实例 | **企业内最新 publish 的版本**——publish 完立刻生效 |
| `MARKET` | 市场实例 | **上次上架时的快照**——publish 了新能力但没重新上架，这里仍是 publish 前的旧能力 |

- publish 更新企业轨道；**重新上架**把当前企业版本推到市场轨道（上架后已开启该服务的实例刷新）。这是发布分发机制（非 bug）。
- 实操含义：① 开发/验证一律用 `source=PUBLISHED` 取址；② 用户从**市场详情页复制的 URL 是 MARKET 轨道**——用它验证刚 publish 的改动会看到旧 schema/旧能力，属正常，要么换 PUBLISHED 地址验、要么让 owner 重新上架。
