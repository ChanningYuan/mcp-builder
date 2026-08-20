# 排障分诊手册

debug 或真实调用出问题时，**先按 §1 拿判据定性，再进对应小节**。禁止跳过分诊直接猜原因——本手册每条结论都由真实工具对照实验实证。

## 目录
- [1. 分诊表（第一步，不能跳）](#1-分诊表第一步不能跳)
- [2. 建工具就被拒：unsafe_domain_url](#2-建工具就被拒unsafe_domain_url)
- [3. executeSuccess=false：没连上或非 200](#3-executesuccessfalse没连上或非-200)
- [4. executeSuccess=true 但结果为空：出参配置问题](#4-executesuccesstrue-但结果为空出参配置问题)
- [5. 有数据但不是预期业务数据](#5-有数据但不是预期业务数据)
- [6. 鉴权类假症状](#6-鉴权类假症状)
- [7. 调试打到了旧版本](#7-调试打到了旧版本)
- [8. 真实案例：空结果被误判成「访问不到我的服务器」](#8-真实案例空结果被误判成访问不到我的服务器)

## 1. 分诊表（第一步，不能跳）

`mcp_tool_debug` 返回顶层五个字段：`executeSuccess` / `toolOutput` / `rawOutput` / `toolInput` / `time`。**`executeSuccess` 是分水岭**。

| 观察到的 | 结论 | 去 |
|---|---|---|
| 建工具阶段就报 `unsafe_domain_url` | URL 是内网地址或域名解析不了 | §2 |
| `executeSuccess=false` + `errorCode: 7000015` | 连不上 / 超时 | §3 |
| `executeSuccess=false` + `errorCode: api_business_error` | 下游 HTTP 状态码非 200（errorMessage 里带完整响应） | §3 |
| `executeSuccess=true`，`toolOutput` 为 `{}` | **出参配置问题，与网络无关** | §4 |
| `executeSuccess=true`，`toolOutput` 是 `{"Body":{…}}` 多包一层 | `outputMappings` 传了 `[]` | §4 |
| `executeSuccess=true`，有数据但不是想要的业务数据 | 入参没传对 / 下游业务报错 | §5 |
| `executeSuccess=true`，返回真实业务数据 | ✅ 通过 | — |

### ⛔ 三条禁止

1. **`executeSuccess=true` 时，禁止提出任何网络类推测**——不要说改域名、换 IP、DNS 解析、内外网分离、防火墙、SSRF 拦截。`true` 就意味着 HTTP 往返已经完成、下游已经响应了。
2. **工具能建成，URL 就已经过了平台安全校验**。内网地址和解析不了的域名在 `mcp_tool_create_http` 阶段直接被拒（§2），不会放行到 debug 再失败。
3. **同一工具同一症状连续 2 次不通就停手**。回到本表定性，向用户报告「已排除项 + 待确认项 + 需要用户提供什么」，不要继续换参数盲试。

### ⚠️ rawOutput 不是原始响应

`rawOutput` **不是映射前的下游原始响应**——它是映射结果外面包一层 `Body`。出参映射取不到值时，`toolOutput` 是 `{}`，`rawOutput` 就是 `{"Body":{}}`，两个都空。

**HTTP 200 的情况下，当前没有任何字段回传下游原始响应体**。要看下游到底返回了什么，用 §4 的透传探针。（HTTP 非 200 是唯一例外：`errorMessage` 里带完整 `Headers` + `Body` + `statusCode`。）

## 2. 建工具就被拒：unsafe_domain_url

```
{"success": false, "errorCode": "unsafe_domain_url",
 "errorMsg": "URL 未通过安全校验（疑似内网地址或不安全域名）：请改用公网可访问的地址"}
```

**含义**：`httpInfo.url` 的域名是内网地址，或者公网 DNS 解析不出来。平台在建工具时就做这道校验。

**修复**：接口必须公网可达。内网接口需要先做公网映射或反向代理，再把公网地址填进来。

**反过来的推论很有用**：工具建成了 = URL 已通过这道校验。后续再出问题，都不要回头怀疑内网/SSRF/DNS。

## 3. executeSuccess=false：没连上或非 200

两种形态，看 `errorCode`：

**`7000015`** —— `request connection server timeout`。请求发出去了但连不上：端口不通、服务没起、防火墙拦了钉钉出口、或下游响应超过 timeout（默认 10 秒，`mcp_tool_create_http` 的 `timeout` 可设 1-180 秒）。

**`api_business_error`** —— 下游返回了，但 HTTP 状态码不是 200。这种情况 `errorMessage` 里**带完整下游响应**，直接读：

```
调用远程服务业务异常, 出参校验不通过。HTTP 状态码当前值：404， 预期值：200，
所有值：{"Headers":{…},"Body":{"reason":"Not Found","error":true},"statusCode":404}
```

看到 404 查 url 路径拼错没；401/403 查鉴权（§6）；5xx 是下游自己的问题，找接口提供方。

## 4. executeSuccess=true 但结果为空：出参配置问题

这是最常见也最容易误判的一类。**下游已经正常返回了**（`time` 字段能看到真实耗时），空是平台在出参映射这一层丢的。

### 三种成因

**成因 1（最常见）：`outputMappings` 的 source 落在 `apiOutputs` 声明范围外。**
`apiOutputs` 按 schema 精确裁剪，没声明的字段先被裁掉，映射再去取就取了个空。全部映射项都取空 → `toolOutput` = `{}`。

```
apiOutputs.body 只声明了 latitude / longitude
outputMappings  却写 source: $.node_service_activator.Body.current.temperature_2m
→ toolOutput {}，rawOutput {"Body":{}}
```

修法：把 `apiOutputs` 补声明到**被映射引用的最深层级**（`current` 是 object 就要带 `children`，里面把 `temperature_2m` 写出来），再 debug。

**成因 2：`outputMappings` 传了 `[]`。** 结果不是空，而是整包响应多包一层 `Body`（`{"Body":{…}}`）。要么按 mapping-rules.md §5 写整体透传，要么写字段级精修。

**成因 3：映射位置名大小写写错。** `$.query` / `$.QUERY` 都静默失效，必须 Pascal：`$.Query` / `$.Body`（mapping-rules.md §3）。这条更多表现为入参丢失（下游报缺参数）。

### ⭐ 透传探针：把下游真实返回捞出来

不知道下游到底返回什么结构时，别猜。**临时**把工具改成下面这样，debug 一次，下游原始全貌就出来了：

```json
"apiOutputs":     { "headers": [], "body": [] },
"outputMappings": [ { "type": "reference", "source": "$.node_service_activator.Body", "target": "$" } ]
```

`apiOutputs.body` 传**空数组**时不做裁剪，整包透传——连你没声明过的字段都会原样出现在 `toolOutput` 里。拿到真实结构后，再照着它把 `apiOutputs` 和字段级映射正式写回去。

> 注意区分：`apiOutputs.body` 传 `[]`（完全不声明）= 不裁剪、全透传；声明了但不全 = 按声明裁剪、漏的被吞。**两者行为相反**，别记混。
>
> 探针是临时手段，查完必须改回正式定义——`[]` + 整体透传会把下游所有字段（含噪音和敏感字段）暴露给 LLM。

## 5. 有数据但不是预期业务数据

下游返回了，但内容是它自己的业务错误（`{"code":-1,"msg":"xxx不能为空"}` 这类）。**这不是平台问题**，是请求没组装对：

- **debug 的 `value` 传了 `{}` 走过场** —— 必须传符合 `toolInputs` 的真实测试入参；
- **入参映射没配全** —— 下游要的参数没有对应的 `inputMappings` 条目，或位置写错了组（该在 Query 的写进了 Body）；
- **鉴权参数没进去** —— 见 §6。

排查时先拿 curl 用同样的参数直接打一次下游接口，对比返回。curl 都返回同样的业务错误 → 是接口调用方式的问题（参数名、位置、鉴权方式），需要找接口提供方确认，不是平台侧能修的。

## 6. 鉴权类假症状

**debug 不吃 `mcp_credential_bind` 绑定的凭证**——调试必须显式传 `credentialId`。不传时按「无账号」降级直连，产生的报错极具误导性：TOKEN 型会把注入配置原文当成 token 发给下游（下游报「不合法的 access_token」之类），BASIC 型静默不注入（下游报未授权）。

看到 401/403/token 无效类报错，**第一件事是确认 debug 有没有传 `credentialId`**，而不是去改鉴权配置。详见 auth-credentials.md。

## 7. 调试打到了旧版本

工具**发布过之后**，`mcp_tool_debug` 不传 `versionId` 默认调**已发布的老版本**，即使存在更新的草稿也不会自动选草稿。

症状：刚改完映射，debug 结果和改之前一模一样（改动像没生效）。
修法：`mcp_tool_get` 读回拿草稿 `versionId`，debug 时显式传。工具状态是 `published_with_draft` 时尤其要注意。

## 8. 真实案例：空结果被误判成「访问不到我的服务器」

**症状**：某接入方的工具 debug 返回空，连试 4 次都空。

**被误导的推理链**：结果空 → 怀疑下游不可达 → 查 DNS 发现该域名内网解析到私网 IP、公网解析到公网 IP（split-horizon）→ 断定是平台 SSRF 防护整体拦截了该域名 → 建议改用 IP 直连绕过域名解析。

**服务端日志显示的真实情况**：三次调试全部成功，160–190 毫秒内拿到下游 HTTP 200 响应，响应体是一条业务错误（`{"code":"-1","msg":"token不能为空"}`）。网络层从头到尾没有任何问题。

**真因**：出参映射的 source 落在 `apiOutputs` 声明范围外（§4 成因 1），下游返回被吞成空；同时 debug 的 `value` 传的是 `{}`，没带 token，所以下游返回的是业务错误而不是数据（§5）。两个问题叠加。

**本该怎么做**：看一眼 `executeSuccess`。它是 `true` ——禁止令第 1 条当场就该挡住所有网络类推测，分诊表直接指向 §4，用透传探针一次就能看到「token不能为空」，五分钟结束。

**代价**：接入方 4 轮试错、改了域名、准备改 IP，最后动用服务端日志才定位。

**这个案例暴露的三件事**（已固化为本手册的设计）：`executeSuccess` 才是分水岭而不是「有没有报错」；`rawOutput` 不能当原始响应用；空结果时必须有一个能看到下游真实返回的手段（透传探针）。
