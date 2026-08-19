# 映射规则（inputMappings / outputMappings）

工具的「入参映射」和「出参映射」把 LLM 可见的工具参数（toolInputs）与接口真实参数（apiInputs）连起来，是工具能不能跑通的核心。这份文档是格式权威，`mcp_tool_create_http` / `mcp_tool_update_http` 的 `inputMappings` / `outputMappings` 字段严格按此写。

> 以下规则均经真实工具端到端逐条实证。

## 目录
- [1. 一条映射规则的结构](#1-一条映射规则的结构)
- [2. source / target 的 JSONPath 写法](#2-source--target-的-jsonpath-写法)
- [3. 位置名必须 Pascal 大小写（最大的坑）](#3-位置名必须-pascal-大小写最大的坑)
- [4. 三种映射类型：reference / fixed / express](#4-三种映射类型reference--fixed--express)
- [5. 出参映射：整体透传 或 字段级精修](#5-出参映射整体透传-或-字段级精修)
- [6. 系统身份注入](#6-系统身份注入)
- [7. 入参数组字段的双规则](#7-入参数组字段的双规则)
- [8. 完整示例](#8-完整示例)

## 1. 一条映射规则的结构

每条 rule 是一个对象：

```json
{ "type": "reference", "source": "$.node_start.city_name", "target": "$.Query.name" }
```

| 字段 | 含义 |
|------|------|
| `type` | 映射类型：`reference`（引用变量）/ `fixed`（固定常量）/ `express`（表达式） |
| `source` | 值从哪来（见 §2）。⚠️ express 型不用 source——表达式放 `expression` 字段、说明放 `displayText`（见 §4） |
| `target` | 值放到哪个接口参数（见 §2） |

`inputMappings` 是「工具入参 → 接口入参」的规则数组（type 三型都可用）；`outputMappings` 是「接口出参 → 工具出参」的规则数组（**只支持 reference / express，无 fixed**，type 缺省 reference）。

## 2. source / target 的 JSONPath 写法

**入参映射（inputMappings）**：
- `source`：`$.node_start.<toolInput 的 key>` —— 引用用户传给工具的参数。
- `target`：`$.<位置>.<接口字段>` —— 写到接口的哪个参数位置。位置 = `Body` / `Query` / `Head` / `Path`（见 §3）。

**出参映射（outputMappings）**：
- `source`：`$.node_service_activator.Body`（接口响应体）/ `$.node_service_activator.Headers`（响应头）。
- `target`：`$` 表示工具出参根，或 `$.<字段>` 指定子字段。

系统身份变量：`source` 用 `$.system_node.operateUserId` / `$.system_node.ddDataCorpId`（见 §6）。

## 3. 位置名必须 Pascal 大小写（最大的坑）

`target` 里的位置名 **必须首字母大写**：`Body` / `Query` / `Head` / `Path`。

- ✅ 正确：`$.Query.name`、`$.Body.userId`
- ❌ 错误：`$.QUERY.name`（全大写）、`$.query.name`（全小写）——**静默失效**：不报错、但值不会流转，接口收到空参数。

这一条最坑，因为写错了平台不报错，只有真跑（`mcp_tool_debug`）才会暴露（接口报缺参数）。建完工具**必须 debug 验证**，就是为了抓这个。

> 注：`apiInputs` 分组的 key 是全大写（`QUERY`/`BODY`/`HEAD`/`PATH`），但映射 `target` 路径里用 Pascal（`Query`/`Body`）。两处大小写不同，别混。

## 4. 三种映射类型：reference / fixed / express

### reference（引用变量，最常用）
把工具入参透传到接口字段。`source` 指向 toolInput 的 key。
```json
{ "type": "reference", "source": "$.node_start.city_name", "target": "$.Query.name" }
```

### fixed（固定常量）
接口字段填一个写死的值，**不暴露给 LLM**。`source` 直接写常量值（不加 `$.`）。用来把接口的固定控制参数从 LLM 视野里裁掉（简化工具入参）。
```json
{ "type": "fixed", "source": "zh", "target": "$.Query.language" }
{ "type": "fixed", "source": "temperature_2m,relative_humidity_2m", "target": "$.Query.current" }
```

### express（表达式）
用表达式函数把值做变换/换算再送给接口（如从系统参数按 key 取值、拼接、取默认值）。

> ⚠️ **字段用法与 reference/fixed 不同（最容易踩的坑）**：express 的表达式**必须放 `expression` 字段**（可读说明放 `displayText`），**不是 `source`**。放 `source` 会被服务端静默丢弃（存成 `{}`），且不报错——DTO 定义：`source`=reference 用 / `expression`=express 用（`MCPToolSchemaTranslator` 只从 expression 取值组装）。

```json
{ "type": "express",
  "expression": "GET(\"operateUserId\",${@(\"system_node/$\")})",
  "displayText": "GET(operateUserId,系统参数)",
  "target": "$.Query.p_expr" }
```

已实证跑通（httpbin 回显收到表达式算出的真实 userId）。表达式语法要点：
- `${@("node_start/$/<字段>")}` 引用工具入参；`${@("system_node/$")}` 引用整个系统参数对象（配 `GET("key", …)` 按 key 取值）；
- 函数可嵌套（如 `CONCATENATE(${@("node_start/$/a")},"_sfx")`）。

**「API → MCP」绝大多数场景用不到 express**：入参走 reference（用户传）+ fixed（常量）+ 系统参数注入（§6）就够了。只有接口要的值需要**运算/换算**才用它，常见两类：
- **身份换算**：接口要 uid/unionId 而系统参数只有 userId → 用换算函数。⚠️ `USERID2UIDBYCORPID` / `CORPID2ORGID`（存量工具 rules 里偶见）是平台「推荐映射」自动注入的**内部函数，不在公开目录**；公开的系统函数只有 `USERID2UNIONID` / `UNIONID2USERID` / `BATCHUSERID2UNIONID` / `BATCHUNIONID2USERID`。
- **取值/兜底/拼接**：`GET(key, obj)`（从对象按 key 取值，key 含特殊字符时用）、`COALESCE`（取第一个非空）、`CONCATENATE`（拼接）、`IF`。

**完整函数目录**（7 组 82 个：集合/日期/逻辑/数学/字符串/JSON/系统）见同目录 **`expression-functions.md`**——做高级数据变换（日期计算/集合运算/字符串处理等）才需要翻，日常建工具用不到。

> 注意区分：**鉴权配置**（`mcp_auth_config_save` 的 authHeaders 等）里的 func 型参数是**另一套字段**（表达式放 `funcValue:{source,display}`，引用鉴权字段用 `${@("authField/$/<dataId>")}`）——见 `auth-credentials.md`，别与这里工具映射的 `expression` 字段混用。

## 5. 出参映射：整体透传 或 字段级精修

`outputMappings` **建议显式配置**，两种模式二选一：

**模式 A · 整体透传**（最简，快速起步）：

```json
[ { "type": "reference", "source": "$.node_service_activator.Body", "target": "$" } ]
```

工具出参 = 按 apiOutputs 裁剪后的完整响应体。

**模式 B · 字段级精修**（推荐交付形态）：配套 `toolOutputs` 声明对外字段树，逐条写映射。词汇表：

| 意图 | 写法 |
|------|------|
| 平移 | `source: $.node_service_activator.Body.a` → `target: $.a` |
| 改名/补语义 | `source: …Body.data.staff_id` → `target: $.user.userId`（toolOutputs 里声明 user.userId 并写中文 description） |
| **裁字段** | 不声明也不写 rule——未映射的 API 字段自动裁除 |
| 数组逐元素 | 两侧带 `[*]`：`…Body.list[*].name` → `$.items[*].name`。⚠️ **数组出参一律元素级 `[*]` 逐字段、不要写"整体一条"**——整体条运行时有效但 UI 数组子字段行全空 |
| 嵌套数组 | **「外层字段条 + 二级 `[*]` 条」两条一组**：`…list[*].tags → $.items[*].tags` 加 `…list[*].tags[*] → $.items[*].tags[*]`（缺二级条 UI 内层空） |
| 对象数组→标量数组 | `…Body.result[*].userId` → `$.members[*]`（取数组元素的单字段拍成字符串数组） |
| 系统变量注入 | `source: $.system_node.ddDataCorpId / $.system_node.operateUserId` → 出参附带调用者上下文 |
| 深层嵌套 target | 4 层嵌套实测存活，`target: $.a.b.c.d` 照写 |

**⚠️ 两条口径**：

1. **省略或传 `[]` 不报错**：工具能建成、运行时返回整包响应体且**多包一层 Body**（`{"Body":{…}}`，无裁剪）——不推荐，请显式选 A 或 B。
2. **source 必须落在 apiOutputs 声明范围内**：apiOutputs 按 schema 精确裁剪——**漏声明的字段被整段吞掉**（调用"成功"但业务数据残缺且不报错，实测曾出现整个数组字段无声消失），同时 UI 标「变量已失效」。`apiOutputs` 必须如实声明到被映射的**最深层级**。

**debug 判读位**：`mcp_tool_debug` 的映射后结果在返回顶层的 **`toolOutput`** 字段，映射前原始响应在 `rawOutput`——对比两者可直接验证出参映射是否生效。⚠️ debug 全绿不代表 UI 无标红（UI 校验与运行时引擎不同源）——映射类改动最后让服务 owner 在管理台 UI 目视一眼出/入参映射页。

## 6. 系统参数注入（身份等）

接口需要调用者身份（userId / corpId）等**运行时上下文**时，**不要**做成 toolInput 让 LLM 传（LLM 不知道、也不该伪造），而是用 `reference` 引用系统参数：

```json
{ "type": "reference", "source": "$.system_node.operateUserId", "target": "$.Body.userId" }
{ "type": "reference", "source": "$.system_node.ddDataCorpId",  "target": "$.Body.corpId" }
```

平台在运行时按「当前调用者」自动填充，权限跟人走。工具入参里不出现身份字段。

### 系统参数全集（`$.system_node.*`）

**用 `key` 列写映射，不要用显示名。** 多数 key 带 `deap` 前缀、且与显示名不同——写错静默失效：

| key（写映射用） | source 路径 | 含义 |
|-----------------|-------------|------|
| `operateUserId` | `$.system_node.operateUserId` | 调用工具的用户 userId（最常用） |
| `ddDataCorpId` | `$.system_node.ddDataCorpId` | 调用工具的组织 corpId（最常用） |
| `deapAgentCode` | `$.system_node.deapAgentCode` | agentCode |
| `deapAgentName` | `$.system_node.deapAgentName` | agentName |
| `deapRunId` | `$.system_node.deapRunId` | 本次运行 runId |
| `deapClientSessionId` | `$.system_node.deapClientSessionId` | sessionId |
| `deapScenarioCode` | `$.system_node.deapScenarioCode` | scenarioCode |
| `deapParentAbilityCallSessionId` | `$.system_node.deapParentAbilityCallSessionId` | 父能力调用 sessionId |

服务配了鉴权时另有 `$.system_node.AppKey` / `$.system_node.AppSecret`（鉴权参数）。

> 若接口要的不是 userId 而是 uid/unionId 等派生身份，需要 `express`（§4）做换算——但换算函数名以平台「推荐映射」为准（如内部的 `USERID2UIDBYCORPID`），不在公开函数目录里，建工具时用 `mcp_tool_get` 读一个已有工具的 rules 参照，别凭空写。

## 7. 入参数组字段的双规则

当某个**入参**是数组时，inputMappings 需要**两条一组**：整体一条 + 元素级一条（`[*]`）（缺 `[*]` 条 UI 显示未映射）。且 `apiInputs`/`toolInputs` 里该 array 字段必须带**非空 `items`**（`items` 用 object 型，避免误导 LLM 以为是标量数组）。

多数「API → MCP」场景入参是标量，用不到这条；遇到数组入参再查此节 + 读一个真实带数组的工具样本对齐。**出参数组**不适用本节——按 §5 词汇表写单条 `[*]` 规则即可。

## 8. 完整示例

open-meteo 城市搜索工具 `search_city` 的完整映射（已实证跑通）：

```json
{
  "inputMappings": [
    { "type": "reference", "source": "$.node_start.city_name", "target": "$.Query.name" },
    { "type": "fixed",     "source": "zh",                       "target": "$.Query.language" },
    { "type": "fixed",     "source": "10",                       "target": "$.Query.count" }
  ],
  "outputMappings": [
    { "type": "reference", "source": "$.node_service_activator.Body", "target": "$" }
  ]
}
```
- 用户只传 `city_name`（reference）；`language=zh`、`count=10` 用 fixed 固定不暴露；
- 出参整体透传，工具返回 open-meteo 的完整 `{results:[...]}`。
