# locales/zh/messages.ftl

# 命令描述和常用短语
start-prompt = 选择您的首选语言：
start-welcome = 你好，{ $user_name }！我是一个人工智能机器人。给我发送文本或图片（带或不带说明），我会尽力回答。使用 /help 查看命令。
language-chosen = 语言已设置为简体中文。{ start-welcome }
language-select-button = 简体中文 🇨🇳

help-text =
    我可以借助 Gemini AI 回复您的文本消息并分析图像。

    <b>命令:</b>
    /start - 重新启动机器人（显示欢迎信息）
    /newchat - 开始新对话（清除历史记录）
    /model - 选择用于生成文本的人工智能模型
    /language - 更改界面语言
    /settings - (只有在你知道自己在做什么的情况下) 配置 Gemini 生成设置
    /help - 显示此消息

    <b>如何使用:</b>
    - 只需给我发送一条文本消息。
    - 发送一张图片。您可以为图片添加标题以提出具体问题（例如，<code>“这张图片有什么不寻常之处？”</code>）。如果没有标题，我会直接描述它。

# 处理消息
thinking = 🧠 正在思考您的问题...
analyzing = 🖼️ 正在分析图片...
thinking-retry = ⏳ 正在重试您的上一个请求...

# 人工智能模型
model-prompt = 选择用于生成文本的人工智能模型：
model-chosen = 人工智能模型已设置为：{ $model_name }

# 创建新聊天
newchat-started = ✨ 好的，我们开始一个新对话！我已经忘记了之前的上下文。

# 键盘
main-keyboard-placeholder = 请选择指令或输入文本…
button-retry-request = 🔁 重试请求？
settings-current-prompt = 当前 Gemini 生成设置：
settings-button-temperature = 🌡️ 温度：{ $value }
settings-button-max-tokens = 📏 最大长度：{ $value }
settings-prompt-temperature = 选择温度（影响创造力）：
settings-prompt-max-tokens = 选择最大回复长度（以令牌计）：
settings-option-default = 默认 ({ $value })
settings-option-temperature-precise = 0.3（精确）
settings-option-temperature-balanced = 0.7（平衡）
settings-option-temperature-creative = 1.4（创意）
settings-option-max-tokens-short = 512（短）
settings-option-max-tokens-medium = 1024（中等）
settings-option-max-tokens-long = 2048（长）
settings-option-max-tokens-very_long = 8192（非常长）
button-back = ⬅️ 返回

# 错误消息
error-gemini-fetch = 😔 无法从 Gemini 获取响应。请稍后再试。
error-image-download = 😔 无法加载您的图片。请重试。
error-image-analysis = 😔 无法使用 Gemini 分析图片。请稍后再试。
error-display = 😔 显示响应时出错。请稍后再试。
error-general = 😔 发生意外错误。请稍后再试。
error-blocked-content = 由于安全限制，我的回复已被阻止（原因：{ $reason }）。请尝试换种方式提问。
error-blocked-image-content = 我对图片的回复由于安全限制而被阻止（原因：{ $reason }）。
error-gemini-api-key = 错误：Gemini API 密钥未配置。
error-gemini-request = 联系 Gemini 时出错：联系管理员！
error-image-analysis-request = 分析图片时出错：联系管理员！
error-retry-not-found = 🤷 无法找到要重试的上一个请求。机器人可能已重启。
error-quota-exceeded = 哎呀！看来我现在太受欢迎了，已经达到了AI请求的限制。请稍后再试。🙏
error-settings-save = ❌ 无法保存设置。请重试。