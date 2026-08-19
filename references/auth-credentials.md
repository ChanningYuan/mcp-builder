# 鉴权配置与凭证账号

下游接口带鉴权时用本文档。平台把鉴权拆成**两层**：

| 层 | 工具 | 存什么 | 类比 |
|----|------|--------|------|
| **鉴权配置**（服务级一份） | `mcp_auth_config_save` / `get` | 鉴权方式与结构（**不含真实密钥**） | 说明书 |
| **凭证账号**（可多个） | `mcp_credential_save` / `list` / `get` / `debug` / `bind` / `unbind` / `delete` | 真实密钥键值 | 钥匙 |

**开发者内置凭证语义**：凭证归属「当前用户 + 当前 MCP 服务」，密钥由**开发者**提供（不是使用者）；该 MCP 的调用统一用这个凭证访问下游，使用者无感。

> 各类型均已端到端实测。另：简单场景也可在工具级 `httpInfo.auth` 内联（`NO_AUTH`/`BASIC`），但服务级配置是推荐路径——支持 TOKEN/SIGNATURE、密钥不进工具定义、可多账号切换。

#### 鉴权方式选型（先选对类型再动手）

| 下游接口要什么 | 选型 |
|---|---|
| 无鉴权 | `NO_AUTH` |
| 用户名+密码（HTTP Basic） | `BASIC` |
| **静态 API key**（key 原文放 query 或 header，如 `?api_key=xxx`） | **`SIGNATURE` 自定义字段 + 直引**（见 SIGNATURE 节样本） |
| 动态换 token（先换 access_token 再调业务接口） | `TOKEN` |
| 自定义签名算法（时间戳/摘要等需表达式计算） | `SIGNATURE` + funcValue 表达式 |

## 标准工作流

```
1. mcp_auth_config_save(mcpId, authType, <类型>AuthConfig)   # 配"说明书"
2. mcp_auth_config_get(mcpId)                                # 核对 authFields（建账号要填哪些字段）
3. mcp_credential_save(mcpId, name, content)                 # 录真实密钥 → 返回 credentialId
4. mcp_credential_debug(mcpId, credentialId)                 # 凭证质检（真跑 testRequest）
5. mcp_tool_debug(..., credentialId=<id>)                    # ⚠️ 工具调试必须显式带 credentialId
6. mcp_credential_bind(mcpId, credentialId)                  # 先把凭证设为实例生效凭证（必须在 publish 之前）
7. mcp_tool_publish(mcpId, toolId)                           # 再发布——顺序反了会卡 DRAFT
#（撤下/换凭证：mcp_credential_unbind(mcpId) 解绑实例生效凭证——bind 的逆操作，幂等）
```

> ⚠️ **顺序铁律：bind 必须早于 publish**（无鉴权服务无此约束）。先 publish 后 bind → 发布实例卡草稿态（DRAFT）：`mcp_server_url_get` 恒返回 success=true 但**无 mcpUrl**，且**事后补 bind 也救不回**——只能重建工具按正确顺序重新发布（实测复现 + 平台侧确认定案）。

## ⚠️ 三条红线（实测踩坑定案）

1. **`mcp_tool_debug` 不吃 bind**：调试链路不使用 `mcp_credential_bind` 的绑定结果，**必须显式传 `credentialId`**；不传则按"无账号"降级直连——TOKEN 型会把注入配置**原文字面量**发给下游（报 token 无效/40014）、BASIC 静默不注入，症状极具误导性。bind 只影响正式实例运行时。
2. **`mcp_credential_debug` 判读口径**：顶层 `executeSuccess` = 探测请求的 **HTTP 2xx 判定**（下游非 2xx 为 false）；返回体内的**业务错误（如 errcode）不计入该判定**——业务错误码型下游仍需结合顶层 `detail.response` 复核后下结论。
3. **`mcp_credential_delete` 护栏**：删**已绑定**的凭证会被拒 `credential_in_use`——解锁出口=先 `mcp_credential_unbind(mcpId)` 解绑再删（unbind 幂等；⚠️服务从未配置鉴权时 unbind 返回 NOT_FOUND「MCP不存在」，是凭证配置记录不存在的误导文案，非服务不存在）。凭证被多少工具引用无法查询，删除前仍须向用户确认。

## 各类型配置要点（`mcp_auth_config_save` 的 xxxAuthConfig）

按 `authType`（**大写枚举**：`NO_AUTH` / `BASIC` / `TOKEN` / `SIGNATURE`）传对应对象，其余留空。各对象里的 `testRequest:{method,url}` 是凭证质检用的探测接口。

### BASIC

```json
{ "basicAuthConfig": { "testRequest": {"method":"GET","url":"https://…/basic-auth/u/p"}, "forceValidate": false } }
```
- username/password 是平台内置字段，**无需声明 authFields**；凭证 content 直接传 `{"username":"…","password":"…"}`。
- 运行时注入 `Authorization: Basic base64(user:pass)`（回显解码实证）。

### TOKEN（先换 token 再注入业务请求）

结构：`{authFields, fetchTokenRequest, authHeaders/authQuery/authBody, tokenExpireRules, refreshToken, testRequest, forceValidate}`。钉钉开放平台的**实测正解形态**：

> 注入位按下游要求三选一：`authHeaders`（token 放请求头，下方样本）/ `authQuery`（token 放 query 参数）/ `authBody`。**query 位模板**（已实测跑通，占位符按下游实际字段替换）：`"authQuery":[{"key":"<业务接口token参数名>","type":"text","value":"$.Body.<token字段路径>"}]`，fetchTokenRequest 的入参同样可经 `query` 数组用 `#("字段")` 引用 authFields；失效判据业务错误码型写 `EQ(${@("Body/<错误码字段>")},"<失效码>")`。

- `authFields`：声明开发者要填的密钥字段，如 `[{"dataId":"appKey","type":"string","required":true},{"dataId":"appSecret","type":"password","required":true}]`；
- `fetchTokenRequest`：**用 v1.0 接口** `POST https://api.dingtalk.com/v1.0/oauth2/accessToken`（返回驼峰 `accessToken`），**不要用老 gettoken**；请求体里引用鉴权字段用 `#("appKey")` / `#("appSecret")` 形态；
- **token 注入到 header 不是 query**：`authHeaders` 加一项 `{key:"x-acs-dingtalk-access-token", type:"text", value:"$.Body.accessToken"}`（value 引用换 token 响应体字段）；
- `tokenExpireRules`（失效判定）**只认 func 表达式**：`${@("$/statusCode")}` 引用刷新链响应上下文（结构 `{Header(单数),Body,statusCode}`）。钉钉 v1.0 无效 token 返 **HTTP 400**，判 `EQ(${@("$/statusCode")},"400")`——不要判 401、不要判 errcode（老 oapi 接口恒返 200，失效自愈永不触发）。
- **凭证保存即预置**：TOKEN 型 `mcp_credential_save` 会现场真实换 token 验密钥并预置入凭证（密钥无效则 save 整体失败，如 invalidClientIdOrSecret）。

### SIGNATURE（静态 API key 直引 / 表达式计算签名注入）

**场景一：静态 API key 直引**（已实测真调公开 API 通过；key 放 query 用 `authQuery`，放 header 换 `authHeaders`）：

```json
{"signatureAuthConfig": {
  "authFields": [{"dataId":"apiKey","description":"API Key","type":"password","required":true}],
  "authQuery": [{"key":"api_key","type":"authField","value":"#(\"apiKey\")"}],
  "testRequest": {"method":"GET","url":"https://<业务接口>"}
}}
```

凭证 content=`{"apiKey":"<真实key>"}`；调试记得 `mcp_tool_debug` 显式带 credentialId。

**场景二：表达式计算签名**：

结构：`{authFields, authHeaders/authQuery/authBody/authPath, testRequest, forceValidate}`。注入参数项 `{key, type, value/funcValue}` 有**三种形态**（字段用法不同，错用**静默不注入**且 save 照样 success）：

| type | 值放哪 | 用途与写法 |
|------|--------|-----------|
| `text` | `value` | 固定字面量原样注入 |
| `authField` | `value` | 直引鉴权字段：`#("accessKeyId")` |
| `func` | **`funcValue:{source,display}`** | 表达式计算。source=表达式原文，display=可读说明。⚠️ 表达式放 `value`（裸的或手工拼 `{"source":…}` 壳）都**静默不注入** |

- **func 表达式内引用鉴权字段的语法**：`${@("authField/$/<dataId>")}`——如 `SHA256(${@("authField/$/accessKeySecret")})`（实测回显精确命中 sha256 结果）。函数目录见 `expression-functions.md`。
- 拿不准形态时：读回一个 UI 里配置成功的同类样本对照，别凭空写。

## 凭证账号（credential）行为细则

- `content` 的 key 必须与鉴权配置 `authFields` 的 `dataId` 一致（`mcp_auth_config_get` 可查）。**保存时即校验必填**：缺 authFields 声明的必填字段直接被拒 `credential_missing_required_field`（中文提示缺哪个字段，如「缺少必填鉴权字段：账号密码」）。
- **save 是全量重存**：`content` 服务端必填，没有"只改名"路径——改名=重交密钥（credentialId 不变）。传 credentialId=更新、不传=新建。
- **保存行为按类型分型**：TOKEN 型 save 真实换 token（见上）；BASIC/SIGNATURE 型纯落库、不调任何接口——完整质检是另一动作 `mcp_credential_debug`，save 不会自动跑。
- 密钥仅保存时传输，任何查询接口都不回显。
- `mcp_credential_list` **按当前鉴权配置版本过滤**：改过 auth_config 后，旧配置下建的账号 list 里看不见（`mcp_credential_get` 按 id 仍可查）。
- **出参 shape**：save 返回 `credentialId`/`credentialName`；get 返回 `credential`{id,name,editable,gmtCreate}；list 返回顶层 `credentials`+分页三字段；debug 返回顶层 `executeSuccess`（HTTP 2xx 判定）/`executeErrorMsg`/`detail`；bind/unbind/delete 仅三件套。所有工具另带 `success`/`errorCode`/`errorMsg` 三件套。
