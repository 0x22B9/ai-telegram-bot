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
    /generate_image - 根据文本生成图像
    /model - 选择用于生成文本的人工智能模型
    /language - 更改界面语言
    /settings - (只有在你知道自己在做什么的情况下) 配置 Gemini 生成设置
    /help - 显示此消息
    /delete_my_data - 从机器人中删除您的所有数据

    <b>如何使用:</b>
    - 只需给我发送一条文本消息。
    - 发送一张图片。您可以为图片添加标题以提出具体问题（例如，<code>“这张图片有什么不寻常之处？”</code>）。如果没有标题，我会直接描述它。
    - 给我发送一个 .docx、.pdf 或 .txt 文件，我会对其进行分析。
    - 不想打字？只需发送语音消息，我会回复！

# 处理消息
thinking = 🧠 正在思考您的问题...
analyzing = 🖼️ 正在分析图片...
thinking-retry = ⏳ 正在重试您的上一个请求...

# 图像生成
generate-image-prompt = 🎨 输入用于生成图像的文本描述（提示）：
generating-image = ✨ 魔法进行中... 正在生成您的图像！这可能需要一些时间。
error-invalid-prompt-type = 请为图像输入文本描述。

# 音频处理
processing-voice = 🎤 正在处理您的语音消息...
processing-transcribed-text = 🧠 正在思考您从音频中提出的请求...
error-transcription-failed = ⚠️ 无法转录音频：{ $error }
error-transcription-failed-unknown = ⚠️ 由于未知错误，无法转录音频。
error-processing-voice = ⚠️ 处理您的语音消息时发生错误。

# 文档处理
error-doc-unsupported-type = ⚠️ 文件类型 ({ $mime_type }) 不支持。请上传 PDF、DOCX 或 TXT。
error-doc-too-large = ⚠️ 文件过大。最大大小：{ $limit_mb } MB。
processing-document = 📄 正在处理文档 '{ $filename }'... 这可能需要一些时间。
processing-extracted-text = 🧠 正在分析文档 '{ $filename }' 中的文本...

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

# 数据删除
confirm-delete-prompt = ⚠️ <b>警告！</b> 您确定要从此机器人中删除您的所有数据（聊天记录、设置）吗？此操作不可逆。
button-confirm-delete = 是的，删除我的数据
button-cancel-delete = 不，取消
delete-success = ✅ 您的信息已成功删除。
delete-error = ❌ 无法删除您的数据。请重试或如果问题持续存在，请联系管理员。
delete-cancelled = 👌 数据删除已取消。

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
error-image-api_error = ❌ 图像生成API错误。请稍后再试。
error-image-timeout_error = ⏳ 图像生成服务器无响应或模型正在加载。请稍后再试。
error-image-rate_limit_error = 🚦 请求过多！已超出图像生成限制。请稍后再试。
error-image-content_filter_error = 🙅 请求被安全过滤器拒绝。请尝试修改提示。
error-image-unknown = ❓ 生成图像时发生未知错误。
error-telegram-send = 😔 无法发送生成的图像。
error-doc-parsing-pdf = ❌ 读取 PDF 文件时出错。文件可能已损坏或加密。
error-doc-parsing-docx = ❌ 读取 DOCX 文件时出错。文件可能已损坏。
error-doc-parsing-txt = ❌ 读取文本文件时出错（编码问题）。
error-doc-parsing-lib_missing = ❌ 服务器上未安装处理此文件类型所需的库 ({ $library })。
error-doc-parsing-emptydoc = ⚠️ 文档不含文本或无法提取文本。
error-doc-parsing-unknown = ❓ 从文档中提取文本时发生未知错误。
error-doc-processing-general = ⚠️ 处理您的文档时发生错误。
response-truncated = [由于消息长度限制，响应已被截断]
error-download-image = 😔 无法上传您的图片。请重试。
error-image-analysis-failed = ❌ 人工智能分析图片失败。请稍后重试。
error-image-analysis-unknown = ❓ 图片分析时发生未知错误。