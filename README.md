# mcp-builder

把你的 HTTP API 变成钉钉平台上可被 AI agent 调用的 MCP 工具——一个给 Claude Code 等 agent 用的 Skill。

给 agent 装上这个 skill 后，你只要把接口材料（OpenAPI / Postman / curl / 接口文档）丢给它，说一句「把这个接口做成 MCP」，agent 就会照着本 skill 的工作流：拆解接口 → 建 MCP 服务 → 配鉴权与凭证 → 建工具 → 真跑调试 → 发布 → 取接入地址并真实调用验证，最后交给你一个可用的 MCP 接入地址。

## 这个 skill 解决什么问题

钉钉 MCP 开发平台的工具定义是「三段式」结构（接口侧 / 工具侧 / 两侧之间的映射），手写容易踩坑：映射位置名大小写写错不报错但值传不进去、出参字段漏声明会被整段吞掉、调试不带凭证会得到误导性的假症状……这些坑分散在平台各处，没有一份文档说全。

本 skill 把这些规则、坑位与验证方法沉淀成 agent 可执行的工作流与参考手册，让 agent 一次做对，而不是靠反复试错。

## 安装

克隆到你的 agent skills 目录即可。以 Claude Code 为例：

```bash
# 用户级（所有项目可用）
git clone https://github.com/ChanningYuan/mcp-builder.git ~/.claude/skills/mcp-builder

# 或项目级（仅当前项目）
git clone https://github.com/ChanningYuan/mcp-builder.git .claude/skills/mcp-builder
```

其他支持 Skill 机制的 agent，放到它约定的 skills 目录下同理。

## 前置条件

1. 你的组织能访问[钉钉 MCP 市场](https://aihub.dingtalk.com)；
2. 你的账号在本组织有**开放平台开发者权限**（没有则所有调用统一报 `no_permission`，找组织管理员开通）；
3. 你要包装的接口本身可以调通（涉鉴权时=密钥有效且接口权限已授权）。

## 怎么用

1. 让 agent 连上「MCP 开发脚手架」这个 MCP——在市场页复制 StreamableHTTP URL 交给 agent，它会写进 MCP client 配置；
2. 把接口材料给 agent，说明这些接口要给 AI 干什么；
3. 剩下的交给它。发布前 agent 会停下来向你确认（发布 = 使用方即可调用，这是强制闸门）。

## 目录结构

| 文件 | 内容 |
|---|---|
| `SKILL.md` | 主流程：定位与边界、接入前自查、平台关键机制、Step 1-9 工作流、护栏 |
| `references/scaffold-tools.md` | 脚手架工具速查：参数、出参、工具状态机、debug 版本选择规则 |
| `references/api-to-tool.md` | 三段式工具定义结构；从 OpenAPI/Postman/curl 提取字段；description 写法规范 |
| `references/mapping-rules.md` | 入参/出参映射格式：JSONPath、位置名大小写、三种映射类型、出参精修、系统参数 |
| `references/auth-credentials.md` | 5 种鉴权类型的配置与凭证账号全流程 |
| `references/expression-functions.md` | 表达式函数全集（7 组 82 个），做复杂数据变换时查 |
| `scripts/mcp_call.py` | 直连 MCP 端点列工具/调工具的验证脚本（仅标准库） |

references 按需加载，不必一次全读——SKILL.md 里标注了每份「什么时候读」。

## 安全须知

MCP 接入地址里的 `?key=` 是**调用者个人身份凭证**，接口密钥同理：只进 MCP client 配置与平台凭证存储，不要写进文档、聊天记录或代码仓库。本 skill 的护栏里也写明了这条，agent 会遵守。

## License

MIT
