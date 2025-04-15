# locales/zh/messages.ftl

# 命令描述和常用短语
start-prompt = 选择您的首选语言：
start-welcome = 你好，{ $user_name }！我是一个由 Gemini 驱动的人工智能机器人。给我发送文本或图片（带或不带标题），我会尝试回复。使用 /help 查看命令。
language-chosen = 语言已设置为简体中文。{ start-welcome }
language-select-button = 简体中文 🇨🇳

help-text =
    我可以借助 Gemini AI 回复您的文本消息并分析图像。

    命令:
    /start - 重新启动机器人（显示欢迎信息）
    /language - 更改界面语言
    /help - 显示此消息

    如何使用:
    - 只需给我发送一条文本消息。
    - 发送一张图片。您可以为图片添加标题以提出具体问题（例如，“这张图片有什么不寻常之处？”）。如果没有标题，我会直接描述它。

# 处理消息
thinking = 🧠 正在思考您的问题...
analyzing = 🖼️ 正在分析图片...

# 错误消息
error-gemini-fetch = 😔 无法从 Gemini 获取响应。请稍后再试。
error-image-download = 😔 无法加载您的图片。请重试。
error-image-analysis = 😔 无法使用 Gemini 分析图片。请稍后再试。
error-display = 😔 显示响应时出错。请稍后再试。
error-general = 😔 发生意外错误。请稍后再试。
error-blocked-content = 由于安全限制，我的回复已被阻止（原因：{ $reason }）。请尝试换种方式提问。
error-blocked-image-content = 我对图片的回复由于安全限制而被阻止（原因：{ $reason }）。
error-gemini-api-key = 错误：Gemini API 密钥未配置。
error-gemini-request = 联系 Gemini 时出错：{ $error }
error-image-analysis-request = 分析图片时出错：{ $error }