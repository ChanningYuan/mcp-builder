---
name: mcp-builder
description: 从 API 接口材料搭建钉钉 MCP 服务与工具：建服务、建/改/调试/发布工具、配鉴权与凭证（BASIC/API_SECRET/TOKEN/SIGNATURE）、取接入地址并真实调用验证。当用户给出 API 文档、OpenAPI/Swagger(yaml/json)、Postman Collection、curl 样例或任何 HTTP 接口描述，说「做成 MCP」「把这个接口给 agent/AI 用」「建个 MCP 工具」「接口变成工具/自动化动作」「上到 MCP 平台」时使用；对已有 MCP 服务做改工具/配鉴权/发布/取地址等单步操作同样用本 skill。即使用户没明说「MCP」，只要意图是把一个 HTTP 接口变成 agent 能调用的工具，就用本 skill。
---

# MCP 搭建助手（mcp-builder，v0.7）

把用户的 API 接口变成钉钉平台上可被 agent/工作流调用的 MCP 工具。做法：调用**「MCP 开发脚手架」这个 MCP 的工具**（`mcp_service_*` / `mcp_tool_*` / `mcp_auth_config_*` / `mcp_credential_*` / `mcp_member_*` / `mcp_server_url_get`）来建、调、发、验。

## 定位与边界

- 本 skill 面向**终端用户场景**（把自己的接口给 AI 用）。
- 本版覆盖 **HTTP 接口映射型工具**（走 `mcp_tool_create_http`）。鉴权：`NO_AUTH` / `BASIC` / `API_SECRET` / `TOKEN` / `SIGNATURE` 五种均已端到端验证，配置方法见 auth-credentials.md。

## 接入前自查（2 分钟，卡住的多数是这三条）

1. 当前组织能访问 [钉钉 MCP 市场](https://aihub.dingtalk.com) 并打开「MCP开发脚手架」详情页（取接入地址的入口）；
2. 当前账号在本组织有**开放平台开发者权限**——没有的话所有脚手架调用统一报 `no_permission`，先找组织管理员开通；
3. 目标接口本身可调用成功（涉鉴权时=密钥有效且接口权限/scope 已授权）——接口自己都调不通，建成工具也只会把同一个错误换个地方报。

## 前置：接入脚手架 MCP

运行前提：当前 agent 已连上「MCP 开发脚手架」这个 MCP（`mcp_service_create` / `mcp_tool_create_http` / `mcp_tool_debug` / `mcp_tool_publish` / `mcp_server_url_get` 等工具可调用）。`tools/list` 能看到这些工具即就绪。

- 未连接时，向用户发出如下引导（**逐字照发**）：

  > 1. 前往 [钉钉MCP开发脚手架（mcpId=10487）](https://aihub.dingtalk.com/#detail?mcpId=10487&detailType=marketMcpDetail)
  > 2. 登录钉钉账号，复制页面右侧的 **StreamableHTTP URL**
  > 3. 将 URL 发给我，我来帮你写入并完成初始化

  拿到 URL 后写入 MCP client（如 `claude mcp add --transport http mcp-scaffold "<URL含?key=>"`），`tools/list` 核对上述工具可见即就绪。
- URL 里的 `?key=` 是用户身份凭证，只进 client 配置，**禁止写档案/回复复读**。

## ⚠️ 平台关键机制（流程据此设计）

1. **create/update 只产草稿**：建/改工具都是草稿，不即生效、不影响线上。要 `mcp_tool_publish` 才发布。
2. **草稿态可 debug 真跑**：`mcp_tool_debug` 在草稿态就真实调用下游接口——**这是发布前验证映射对不对的关键手段**（映射位置名写错等问题只有真跑才暴露，见 mapping-rules.md §3）。
3. **debug 两大假阳性坑**：① 工具**发布过之后**，debug 不传 versionId 默认调**已发布老版本**（绝不自动挑新草稿）——调正在编辑的草稿必须显式传草稿 versionId；② debug **不吃凭证绑定（bind）**——带鉴权的工具调试必须显式传 `credentialId`，否则按无账号降级直连、症状极具误导性。
4. **发布是用户复核的强制闸门**：发布 = 使用方可调用。发布前必须让用户确认。
5. **publish ≠ 上架市场**：publish 到企业即可用；取地址用 `mcp_server_url_get(mcpId, source="PUBLISHED")` 自助拿到，不需要上架、不需要外部工具。返回的是**调用者个人身份**的实例地址（含个人 key，勿外发）。⚠️ `source=MARKET` 的实例能力停在**上次上架时的快照**——开发/验证一律用 PUBLISHED（双轨道机制见 scaffold-tools.md）。

## 参考文件（按需读，别全塞进上下文）

- **`references/scaffold-tools.md`** —— 脚手架工具的参数、出参、用途、工具状态机、debug 版本选择规则。**动手前先读**。
- **`references/api-to-tool.md`** —— 三段式工具定义结构（11 项必填契约）+ 怎么从 OpenAPI/Postman/curl 拆字段 + description 规范。**拆解材料/建工具时读**。
- **`references/mapping-rules.md`** —— inputMappings/outputMappings 的格式（JSONPath、Pascal 位置名、reference/fixed/express、出参整体透传与字段级精修、系统参数全集）。**写映射前必读**，这是最容易踩坑的地方。
- **`references/auth-credentials.md`** —— 5 种鉴权类型的配置与凭证账号全流程（auth_config → credential → debug 带 credentialId → bind）。**接口带鉴权时必读**。
- **`references/troubleshooting.md`** —— 排障分诊手册：debug 五字段判据表、三条禁止、六类症状的成因与修法、看下游真实返回的透传探针。**debug 结果不符合预期时必读**，先分诊再动手。
- **`references/expression-functions.md`** —— express 表达式函数全集（7 组 82 个）。只有做复杂数据变换时才查，日常用不到。
- **`scripts/mcp_call.py`** —— 直连新建 MCP 端点列/调工具的脚本，验证步骤用。

## 工作流（按序）

### Step 1 · 信息对齐（缺就问，禁止猜）
收齐三件事：① API 材料（OpenAPI/Postman/curl/文档，至少一种）；② 业务目标（这些接口给 agent 干什么——决定工具怎么拆、description 怎么写）；③ 鉴权方式（不确定就问，别默认 NO_AUTH 蒙混；带鉴权的还要向用户要密钥材料，说明密钥只进平台凭证、不落任何文档）。

### Step 2 · 拆解材料 → 工具设计（读 api-to-tool.md + mapping-rules.md）
把材料拆成三段式工具清单（一个语义动作一个工具）。每个工具产出：name/title/description、httpInfo、apiInputs、toolInputs、inputMappings、apiOutputs、toolOutputs、outputMappings（11 项全必填，见 api-to-tool.md；出参写法见 mapping-rules.md §5），以及一组**建议测试入参**（从材料示例值来，Step 6 用）。
- 只读接口**建议先真跑一次**取真实响应，反推出参、生成测试入参（比猜准）。
- 映射按 mapping-rules.md 写：位置名 Pascal（`$.Query.x`）、常量用 fixed、身份用系统注入。
- 出参：快速起步用整体透传；交付级建议**字段级精修**（toolOutputs 声明对外字段树+逐条映射，裁噪音/改语义名/写中文 desc）。⚠️ apiOutputs 要声明到被映射的最深层级，否则 UI 标「变量已失效」。
- 把设计整表给用户过一遍（此时改成本最低）。

### Step 3 · 建服务
`mcp_service_create(name, description)` → 拿到 **mcpId**（数字，后续所有操作的主键）。name 用业务语义、禁 test/临时 占位名（用户明说测试用途除外）。要接 CLI 命令组的可给 `serverName`（kebab-case、组织内唯一）。

### Step 4 · 配鉴权（接口带鉴权时；读 auth-credentials.md）
`mcp_auth_config_save`（服务级"说明书"，按 authType 传对应配置对象）→ `mcp_credential_save`（录真实密钥，拿 **credentialId**）→ `mcp_credential_debug` 质检（⚠️ success=true 只代表连通，要看 detail 判断鉴权真过没过）。无鉴权接口跳过本步。

### Step 5 · 建工具（草稿）
逐个 `mcp_tool_create_http(mcpId, name, title, description, httpInfo, apiInputs, toolInputs, inputMappings, apiOutputs, toolOutputs, outputMappings)` → 出参顶层拿到 **toolId**（`G-ACT-*`）。可选 `timeout`（1-180 秒，⚠️设置后无法清回系统默认）/`onlyOriginalKeys`。**先建最简单的一个**，`mcp_tool_get` 读回核对（rules 位置名对不对、映射条数对不对），结构没问题再建其余。每建一个 `mcp_tool_list` 反查一个，失败即停。

### Step 6 · 调试（发布前必做，抓映射错误）

**6.1 真跑**：逐个 `mcp_tool_debug(mcpId, toolId, value=<建议测试入参>)`（value 直接是入参对象，不要包 Body 层；**带鉴权必须传 credentialId**；改过已发布工具则必须显式传草稿 versionId）。`value` 要传符合 toolInputs 的**真实测试入参，不要传空 `{}` 走过场**。写操作类工具会真实写入下游 → 先让用户指定测试资源。

**6.2 判读（每次 debug 后必做，不能跳过）**：返回顶层五字段 `executeSuccess` / `toolOutput` / `rawOutput` / `toolInput` / `time`。**`executeSuccess` 是分水岭**，先按下表定性，再决定改什么：

| 观察 | 结论 | 去哪 |
|---|---|---|
| `executeSuccess=false`，`errorCode: 7000015` | 连不上 / 超时 | troubleshooting.md §3 |
| `executeSuccess=false`，`errorCode: api_business_error` | 下游 HTTP 非 200（errorMessage 里带完整响应） | troubleshooting.md §3 |
| `executeSuccess=true`，`toolOutput` 为 `{}` | **出参配置问题，与网络无关** | troubleshooting.md §4 |
| `executeSuccess=true`，`toolOutput` 是 `{"Body":{…}}` 多包一层 | `outputMappings` 传了 `[]` | mapping-rules.md §5 |
| `executeSuccess=true`，有数据但不是预期业务数据 | 入参没传对 / 下游业务报错 | troubleshooting.md §5 |
| `executeSuccess=true`，返回**真实业务数据** | ✅ 通过（查北京要真返回经纬度——「没报错」不算过） | 进 6.3 |

⚠️ **`rawOutput` 不是映射前的原始响应**：它是映射结果外包一层 `Body`，映射取不到值时同样是 `{"Body":{}}`。**不要拿它当「下游返回了什么」的证据**。要看下游真实返回，用 troubleshooting.md §4 的透传探针。

⛔ `executeSuccess=true` 时**禁止提出任何网络类推测**（改域名 / 换 IP / DNS / 防火墙 / SSRF）——`true` 即 HTTP 往返已完成、下游已响应。内网地址与解析不了的域名在 Step 5 建工具时就被 `unsafe_domain_url` 拒了，根本到不了这里。

**6.3 修复与收敛**：映射类问题按 mapping-rules.md 修 → `mcp_tool_update_http`（全量提交，先 `mcp_tool_get` 读回）→ 再 debug。**同一工具同一症状连续 2 次不通就停手**，按 troubleshooting.md 分诊后向用户报告「已排除项 + 待确认项 + 需要用户提供什么」，禁止继续盲试。映射类改动全绿后，建议让服务 owner 在管理台 UI 目视一眼出/入参映射页（UI 校验与运行时不同源，「变量已失效」/数组子字段空只有 UI 能暴露）。

### Step 7 · 发布（强制闸门）
**debug 全通过 ≠ 任务完成**——用户目标含「让我能调用 / 给 agent 用」时，此刻只是进入**待发布确认**状态：向用户复述「将发布哪些工具、发布后你企业内全员即可调用」，获得**明确同意**（「嗯/继续」不算）；确认到来前的每次汇报都要带「仍未发布、客户端不可用」。带鉴权的服务，**先 `mcp_credential_bind(mcpId, credentialId)` 绑定生效凭证，再逐个 `mcp_tool_publish(mcpId, toolId)` 发布**——顺序不能反：反了发布实例卡草稿态、取不到接入地址且**不可恢复**（只能重建工具重发布）。无鉴权服务直接逐个 publish。

### Step 8 · 取地址 + 真实调用验证（闭环）
1. **取址前先 `mcp_tool_list` 回读已发布数量**：0 个已发布工具（全是 draft）时 `mcp_server_url_get` 照样返回 success+完整 mcpUrl（平台已知缺口），该 URL 的 `tools/list` 报泛化 `PARAM_ERROR 参数不能为空`、`tools/call` 返回 `not found the specified tool` 且 `isError=false`——**这样的 URL 不是可用交付物，禁止交付**，回 Step 7 走发布。
2. `mcp_server_url_get(mcpId, source="PUBLISHED")` → 出参顶层 `mcpUrl` 即新 MCP 的接入地址（个人身份地址，带 key）。
   - ⚠️ 若返回 success=true 但**没有 mcpUrl**：多半是带鉴权服务发布前没 bind 凭证（实例卡草稿态）——核对是否按 Step 7『先 bind 再 publish』；先发布后 bind 事后补救无效，需重建工具按正确顺序重发布。
3. 用 `scripts/mcp_call.py` 连上去验证（agent 没法中途加 MCP，用脚本直连端点）：
   ```bash
   python3 scripts/mcp_call.py list "<mcpUrl>"
   python3 scripts/mcp_call.py call "<mcpUrl>" <tool> '<测试入参>'
   ```
4. 逐工具真实调一次，确认返回真实数据。**只有 publish → 取址 → tools/list → tools/call 全通过，才能宣称 MCP 闭环完成**。

### Step 9 · 交付清单
输出：mcpId / 工具对照表（name、toolId、状态、验证结果）/ 新 MCP 接入方式（`mcp_server_url_get` 取址，**不复读 key**）/ 未尽事项。

## 护栏（不可违反）

1. **发布是闸门**：`mcp_tool_publish` 前必须用户明确同意，不提供「全建全发不用看」；`mcp_service_delete` / `mcp_tool_delete` / `mcp_credential_delete` / `mcp_member_remove` 同样按红线需确认（删被绑定凭证会被拒 `credential_in_use`——解锁=先 `mcp_credential_unbind`；删除仍须用户确认）。
2. **发布前必调试**：每个工具 `mcp_tool_debug` 真跑通过才允许 publish——防映射错误上线。
3. **调草稿传 versionId、带鉴权传 credentialId**：违者 debug 结果是假阳性（测的是旧版本/无鉴权降级）。
4. **读回优先**：`mcp_tool_update_http` 前必 `mcp_tool_get` 读回现状再改（全量覆盖，漏字段=清字段；仅 timeout/onlyOriginalKeys 例外漏传=保留）。读回即三段式（含 httpInfo），可直接在读回基础上改后提交。
5. **映射位置名 Pascal**：`$.Query`/`$.Body` 不是 `$.QUERY`/`$.query`——写错静默失效（mapping-rules.md §3）。
6. **凭证纪律**：`?key=` 与密钥只进 client 配置/平台凭证/命令行入参，禁止写文件、禁止回复复读；密钥保存后平台不回显。
7. **参数不猜**：布尔/枚举/鉴权方式不确定就问用户。
8. 同类操作连续失败 3 次 → 停下汇总给用户，不空转。
9. **排障先分诊后动手**：debug 结果异常时先按 Step 6.2 判据表定性，再改东西。`executeSuccess=true` 时禁止任何网络类推测（改域名/换 IP/DNS/防火墙/SSRF）——那是 `executeSuccess=false` 才需要考虑的分支。同一症状连续 2 次不通即停手报告，不靠反复试错撞答案。
