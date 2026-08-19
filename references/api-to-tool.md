# API 材料 → 三段式工具定义

`mcp_tool_create_http` / `mcp_tool_update_http` 的入参是「三段式」结构。这份文档讲怎么把用户给的 API 材料（OpenAPI / Postman / curl / 文档）拆成这个结构。映射规则（inputMappings/outputMappings）的格式见 `mapping-rules.md`。

## 目录
- [1. 三段式总览](#1-三段式总览)
- [2. 字段结构（MCPToolField）](#2-字段结构mcptoolfield)
- [3. 从不同材料提取](#3-从不同材料提取)
- [4. 工具侧加工（裁剪 / 改名 / 防呆）](#4-工具侧加工)
- [5. description 写法规范](#5-description-写法规范)
- [6. 拆分粒度](#6-拆分粒度)

## 1. 三段式总览

一个工具 = 基本信息 + 接口侧 + 工具侧：

| 段 | 字段 | 说明 |
|----|------|------|
| **基本信息** | `mcpId`* / `name`* / `title`* / `description`* | name=snake_case 动词开头；title=中文≤30字；description 见 §5 |
| **接口侧** | `httpInfo`*（method/url/auth）+ `apiInputs`*（headers/body/query/path 四组）+ `apiOutputs`*（headers/body） | 照接口原貌，是真实要发出去的 HTTP 请求。⚠️ apiOutputs 按 schema **精确裁剪**：漏声明的字段会被**整段吞掉**（调用"成功"但业务数据残缺且不报错，实测曾出现整个数组字段无声消失）+ UI 标「变量已失效」——必须如实声明到被出参映射引用的最深层级（mapping-rules.md §5） |
| **工具侧** | `toolInputs`*（暴露给 LLM 的入参）+ `toolOutputs`* + `inputMappings`* + `outputMappings`* | LLM 看到的样子 + 与接口侧的映射（见 mapping-rules.md）。toolOutputs=对外出参字段树（不做精修时显式传 `[]`），配合字段级 outputMappings 做裁剪/改名/补语义 |

> **契约要点**：带 `*` 的 **11 项必填**（create_http；update_http 另加 `toolId` 共 12 项）；另有 2 个可选参数 **`timeout`**（1-180 秒整数，缺省系统默认 10 秒；⚠️一旦设置无法清回默认）与 **`onlyOriginalKeys`**（开启后出参只映射 API 实际返回的 key，不产生 null 占位）——这两个是 update_http 全量提交语义的**仅有例外**：漏传=保留原值。没有 toolType 参数。⚠️ 必填是 **schema 语义约束**（给遵守 schema 的 AI/MCP 客户端防呆用），平台运行时不强拦缺失——别依赖平台报错兜底。

`httpInfo.auth`（工具级内联鉴权，简单场景用）：无鉴权传 `{"type":"NO_AUTH"}`；Basic 传 `{"type":"BASIC","username":"..","password":".."}`；API Secret 传 `{"type":"API_SECRET","apiSecret":".."}`；Bearer 传 `{"type":"BEARER",...}`。下游是 TOKEN/SIGNATURE 类鉴权、或密钥不想写进工具定义时，走**服务级鉴权配置 + 凭证账号**（见 `auth-credentials.md`，推荐路径）。

`outputMappings` 若传 `[]`（或被平台容忍地省略）会导致运行时返回多包一层 Body 的整包响应（不推荐）——至少写整体透传，交付级工具建议字段级精修（mapping-rules.md §5）。

## 2. 字段结构（MCPToolField）

`apiInputs` 是**按位置分组的对象**：每组（`query`/`body`/`path`/`headers`）的值 = `[{key,type,description,...}]` **数组**，用不到的组给空数组 `[]`：

```json
{
  "query": [
    { "key": "name", "type": "string", "title": "城市名", "required": true, "description": "城市名称" }
  ],
  "body": [],
  "path": [],
  "headers": []
}
```

⚠️ 组的值写成对象（如 `{"query":{"name":{...}}}`）会被服务端拒。`apiOutputs` 同构，但只有 `headers`/`body` 两组。

`apiInputs.<组>[]` 和 `toolInputs[]` 的每个字段：

```json
{ "key": "name", "type": "string", "title": "城市名", "required": true, "description": "城市名称", "children": [] }
```
- `type`：`string` / `number` / `integer` / `boolean` / `object` / `array`；
- `object` 型：子字段列表放 `children`（递归同结构）；`array` 型：`children` 固定**恰一项** `key="items"`（元素结构，可任意深嵌套），items 不能空（见 mapping-rules.md §7）；
- `toolInputs` 的 `key` 与 `inputMappings.source`（`$.node_start.<key>`）对应；`apiInputs` 的字段位置与 `inputMappings.target`（`$.<位置>.<key>`）对应。

## 3. 从不同材料提取

| 材料 | 提取规则 |
|------|----------|
| **OpenAPI/Swagger** | `paths.{path}.{method}` → 候选工具；`operationId` → name（不合规则则重命名）；`summary/description` → title/description 素材；`parameters`（按 in=query/path/header 分组进 apiInputs 对应组）+ `requestBody` → apiInputs.body；`responses.200.schema` → apiOutputs.body；`servers[0].url` + path → httpInfo.url |
| **Postman Collection** | `item[].request` → method/url/headers/body；`item[].name` → title 素材；`response`/example → 测试入参 + apiOutputs 素材 |
| **curl 样例** | `-X` → method；URL（query 串拆进 apiInputs.query）；`-H` → headers；`-d/--data/--form` → body；**只读接口可真跑一次**拿响应反推 apiOutputs（推荐，比猜准） |
| **文档文本** | 逐接口提取；字段含义不确定处**问用户，禁止编** |

**建议真跑取样**：对只读接口，先用 curl/直连真实请求一次，拿到真实响应，反推 apiOutputs 结构 + 生成 Step「调试」用的测试入参。比只看文档猜可靠得多。

### 3.1 curl → 三段式提取要点（最常见材料，逐项过）

1. `-X`（缺省=GET）→ `httpInfo.method`；URL 主体 → `httpInfo.url`——**query 串不留在 url 里**，逐参数拆进 `apiInputs.query`；
2. `-H` 逐个处理：鉴权类 header（Authorization/token 等）**不进工具定义**——走服务级鉴权配置+凭证（auth-credentials.md）；`Content-Type` 这类固定头用 `fixed` 映射写死，不暴露给 LLM；
3. `-d/--data/--form` → `apiInputs.body`——JSON 体**逐字段展开成字段树**（object 用 children 递归），别整包声明成一个 string；
4. URL path 里的变量段（如 `/users/123` 的 `123`）→ `apiInputs.path`；
5. 只读接口先把这条 curl 真跑一次 → 真实响应反推 `apiOutputs` + 留作调试入参。

**提取后的增值 checklist（拆完 curl 只是及格线，以下才是决定工具质量的活）**：
- [ ] toolInputs 字段名对 LLM 语义化（接口缩写名 → 语义名，靠 inputMappings 连回）；
- [ ] 每个 toolInput 的 description 按 §5 模板写全（必填性/格式/取值来源/GoodCase/BadCase）；
- [ ] 分页游标/固定控制位裁掉，用 `fixed` 写死（§4）；
- [ ] 身份字段走系统注入，不做成 toolInput（mapping-rules.md §6）；
- [ ] 出参裁噪音字段、改中文语义名、逐字段写 description（§4 出参侧）；
- [ ] name/title/description 按 §5 §6 校一遍（一个语义动作一个工具）。

## 4. 工具侧加工

toolInputs 不是 apiInputs 的照搬，而是**面向 LLM 的投影**：
- **裁剪**：分页游标、固定控制位、冗余参数不暴露给 LLM，改用 `fixed` 映射写死（见 mapping-rules.md §4）；
- **改名**：接口字段名对 LLM 不友好时改成语义名（如接口 `name` → 工具 `city_name`），靠 inputMappings 连回去；
- **补默认/约束**：平台的 MCPToolField 不支持 enum/default/example 标准属性 → 这些约束写进 `description` 文本（见 §5）；
- **身份字段**：接口要 userId/corpId 的，用系统注入（mapping-rules.md §6），不做成 toolInput。

**出参侧同理**（`toolOutputs` = 面向 LLM 的出参投影，支持字段级精修）：裁掉审计/回显噪音字段（不声明也不映射即裁除）、把接口字段改成语义名（如 `data.staff_id` → `user.userId`）、每个字段写中文 description（直接喂给 LLM）。快速起步可先整体透传，交付前建议精修——写法见 mapping-rules.md §5。

## 5. description 写法规范

description 是喂给 agent 的，质量直接决定 agent 会不会/会不会用对。

**工具 description**（`description` 字段）：动词开头，50-200 字，独立可理解，包含四要素——功能 / 参数 / 输出 / 适用场景。写清「什么时候用本工具」「前置工具依赖」（如「latitude 可由 search_city 工具获得」）。

**参数 description**（每个 toolInput 的 `description`）按模板填空：

```
{必填/可选}。{这是什么+起什么作用}。{格式/枚举/默认值说明——平台字段不支持 enum/default/example 属性，约束全写在这}。{取值来源：固定格式 or 由哪个工具的哪个出参获得}。✅GoodCase：{合法示例}；❌BadCase：{典型错误}（{为什么错}）。示例：{可直接照抄的值}
```

**示例**（参数 desc）：
```
必填。要查询的城市中文名称。✅GoodCase：北京 / 上海；❌BadCase：beijing（不要传拼音或英文）。示例：北京
```

自检法：把这条 desc 单独拿给一个没见过接口文档的人（或 agent），能否不猜就填对参数。

破坏性/写操作类工具，description 里显式注明影响面。

## 6. 拆分粒度

**一个语义动作一个工具**，不是「一个 endpoint 机械翻译成一个工具」：
- 同一 endpoint 的两种典型用法可拆两个工具（各自 description 更聚焦）；
- 纯运维 / 冗余 / 内部接口可以不建；
- 有依赖关系的工具（先 A 拿 ID 再 B 用）在各自 description 里写清依赖，让 agent 会编排。
