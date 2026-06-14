# 国家电网 Home Assistant 集成

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Version](https://img.shields.io/badge/version-0.3.9-blue.svg)]()
[![GitHub release](https://img.shields.io/github/v/release/tiejiang29/state_grid.svg)](https://github.com/tiejiang29/state_grid/releases)

国家电网（95598.cn）Home Assistant 自定义集成，支持**点选验证码**和**滑块验证码**自动识别，**手机号登录遇流控自动降级邮箱登录**。

## 功能特性

- 电费余额 — 账户余额、预付费余额
- 日用电量 — 日总/峰/谷/平/尖用电量
- 月用电量 — 当月累计分时用电量
- 年度数据 — 年度累计用电量、电费
- 历史图表 — 最近30天每日用电、最近12个月每月用电
- LLM验证码 — 使用视觉大模型自动识别点选/滑块验证码
- 流控降级 — 手机号登录遇流控时，自动切换邮箱登录

## v0.3.9 更新

- 修复流控降级逻辑无法触发的严重 Bug（`_is_flow_control_error` 检测不到内部方法返回的流控码）
- 修复 `__get_request_key` / `__get_pass_verify_code` / `__verify_password` 丢失原始错误码的问题（保留 `raw_code` 字段）
- 修复 `__fetch_safe` 遇流控时无邮箱降级路径的问题
- 修复 `__try_password_login` 只用手机号重试、不会降级邮箱的问题
- 修复 `__need_login` 将 11401 流控码当作需重新登录导致反复重试的问题
- 流控关键词检测增加 `RK001` 匹配
- `FLOW_CONTROL_CODES` 精简为 `{11401}`（10015/30010/10002 是 token 失效码，不是流控码）

## v0.3.8 更新

- 支持手机号优先登录，遇流控自动降级邮箱登录
- 单步配置表单（手机号 + 备用邮箱 + 密码 + LLM 配置）
- 处理 HTTP 405 非 JSON 返回（IP 级 WAF 限流）

## v0.2.0 更新

- 支持点选验证码（LLM视觉大模型识别）
- 支持滑块验证码（LLM + 像素算法双模式）
- 自动检测验证码类型
- 新增预付费余额传感器
- 移除 onnxruntime 依赖，改用 openai SDK
- 代码可读性优化

## 安装

### 方式一：HACS 安装（推荐）

1. 在 HACS 中点击 **集成**
2. 点击右下角 **探索与下载仓库**
3. 点击右下角 **自定义仓库**
4. 仓库地址填入：`https://github.com/tiejiang29/state_grid`
5. 类别选择：**集成**
6. 点击 **添加** → **下载**
7. 重启 Home Assistant

### 方式二：手动安装

1. 下载此仓库
2. 将 `state_grid` 文件夹复制到 Home Assistant 的 `custom_components/state_grid/` 目录
3. 重启 Home Assistant

## 配置

1. 进入 **设置** → **设备与服务** → **添加集成**
2. 搜索 **"国家电网"**
3. 填写配置信息：
   - **手机号**：国家电网手机号（必填，优先使用）
   - **备用邮箱**：流控降级用（选填，手机号遇流控时自动切换）
   - **密码**：国家电网密码
   - **LLM API Key**：大模型 API 密钥（必填，用于验证码识别）
   - **LLM Base URL**（可选）：默认为火山引擎豆包 API
   - **LLM Model**（可选）：默认为 `doubao-seed-2-0-pro-260215`

### 流控降级说明

95598 API 对手机号登录有频率限制（错误码 11401 / RK001），触发流控后手机号登录会反复失败。配置备用邮箱后，集成会：

1. 优先使用手机号登录
2. 检测到流控错误时，自动切换到邮箱登录（同一密码）
3. 邮箱登录成功后继续正常获取数据

### 获取 LLM API Key

推荐使用**火山引擎豆包**大模型（注册送免费额度）：

1. 访问 [火山引擎](https://www.volcengine.com/)
2. 注册并开通豆包大模型
3. 创建 API Key
4. 填入配置即可

也支持任何 OpenAI 兼容的 API（如 OpenAI、Azure、Gemini 等）。

## 传感器列表

| 传感器 | 说明 | 单位 |
|--------|------|------|
| 账户余额 | 电费账户余额 | 元 |
| 预付费余额 | 预付费账户余额 | 元 |
| 年度累计用电 | 年度总用电量 | kWh |
| 年度累计峰用电 | 年度峰时段用电 | kWh |
| 年度累计谷用电 | 年度谷时段用电 | kWh |
| 年度累计平用电 | 年度平时段用电 | kWh |
| 年度累计尖用电 | 年度尖时段用电 | kWh |
| 年度累计电费 | 年度总电费 | 元 |
| 上个月用电 | 上月总用电量 | kWh |
| 上个月电费 | 上月总电费 | 元 |
| 上个月抄表 | 上月抄表数 | - |
| 当月累计用电 | 当月总用电量 | kWh |
| 当月累计峰/谷/平/尖用电 | 当月分时用电 | kWh |
| 日总/峰/谷/平/尖用电 | 日分时用电 | kWh |
| 最近30天每日用电 | 图表数据 | - |
| 最近12个月每月用电 | 图表数据 | - |

## 技术架构

- **验证码识别**：LLM 视觉大模型（点选/滑块）+ 像素算法（滑块后备）
- **流控降级**：手机号优先 → 流控检测 → 邮箱降级登录
- **数据获取**：纯 API 直连（SM4/SM2/SM3 国密加密）
- **运行方式**：HA 原生集成（无 Selenium/浏览器依赖）

## 致谢

- [bilezhou/state_grid](https://github.com/bilezhou/state_grid) — 原 HA 集成
- [ARC-MX/sgcc_electricity_new](https://github.com/ARC-MX/sgcc_electricity_new) — LLM 验证码解算参考

## 免责声明

本项目仅供学习交流使用，请勿用于商业用途。使用本集成即表示您同意自行承担相关风险。
