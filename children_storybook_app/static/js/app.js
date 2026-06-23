/**
 * 儿童故事绘本生成器 - 主页交互逻辑
 */

const app = {
    currentStory: null,
    selectedStyle: "cartoon",

    init() {
        this.bindStyleSelection();
        this.bindForm();
    },

    bindStyleSelection() {
        const cards = document.querySelectorAll(".style-card");
        cards.forEach(card => {
            card.addEventListener("click", () => {
                cards.forEach(c => c.classList.remove("selected"));
                card.classList.add("selected");
                this.selectedStyle = card.dataset.style;
            });
        });
    },

    bindForm() {
        const form = document.getElementById("storyForm");
        form.addEventListener("submit", (e) => {
            e.preventDefault();
            this.validateAndParse();
        });
        
        // 检查是否有从上传页面带来的故事数据
        const pendingStory = sessionStorage.getItem("pendingStory");
        if (pendingStory) {
            try {
                const story = JSON.parse(pendingStory);
                document.getElementById("storyTitle").value = story.title || "";
                document.getElementById("storyAuthor").value = story.author || "";
                document.getElementById("storyContent").value = story.chapters
                    ? story.chapters.map(c => c.content).join("\n\n")
                    : "";
                sessionStorage.removeItem("pendingStory");
                this.showMessage("📤 上传的故事已载入，点击安全检测即可预览", "info");
            } catch (e) {
                console.error("解析 pendingStory 失败:", e);
            }
        }
    },

    async loadDemoStory() {
        try {
            const response = await fetch("/api/demo-story");
            const result = await response.json();
            
            if (result.success) {
                const story = result.data;
                document.getElementById("storyTitle").value = story.title;
                document.getElementById("storyAuthor").value = story.author;
                document.getElementById("storyContent").value = story.chapters
                    .map(c => c.content)
                    .join("\n\n");
                this.showMessage("🎲 示例故事已载入，点击安全检测即可预览");
            }
        } catch (error) {
            this.showMessage("❌ 载入示例失败：" + error.message, "error");
        }
    },

    async validateAndParse() {
        const title = document.getElementById("storyTitle").value.trim();
        const content = document.getElementById("storyContent").value.trim();
        const author = document.getElementById("storyAuthor").value.trim();

        if (!title || !content) {
            this.showMessage("请填写故事标题和正文", "error");
            return;
        }

        try {
            this.showMessage("🔍 正在检测内容安全...", "info");
            
            const response = await fetch("/api/story/parse", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title, content, author })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.currentStory = result.data;
                this.renderChapterPreview(this.currentStory.chapters);
                this.renderSafetyResult(this.currentStory.safety);
                document.getElementById("generateActions").style.display = "block";
                this.showMessage("✅ 故事解析完成，共 " + this.currentStory.chapter_count + " 页");
            } else {
                this.renderSafetyResult(result.data?.safety || { risk_level: "high" });
                this.showMessage("❌ " + result.message, "error");
            }
        } catch (error) {
            this.showMessage("❌ 请求失败：" + error.message, "error");
        }
    },

    renderChapterPreview(chapters) {
        const container = document.getElementById("chapterPreview");
        
        if (!chapters || chapters.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">📝</span>
                    <p>未解析到章节</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = chapters.map((chapter, index) => `
            <div class="chapter-item" title="点击查看完整内容">
                <div class="chapter-item-title">${index + 1}. ${this.escapeHtml(chapter.title)}</div>
                <div class="chapter-item-content">${this.escapeHtml(chapter.content)}</div>
            </div>
        `).join("");
    },

    renderSafetyResult(safety) {
        const container = document.getElementById("safetyResult");
        if (!safety) {
            container.style.display = "none";
            return;
        }
        
        let className = "safety-safe";
        let icon = "✅";
        let text = "内容安全，可以放心创作绘本";
        
        if (safety.risk_level === "medium") {
            className = "safety-warning";
            icon = "⚠️";
            text = `检测到敏感词：${safety.matched_words.join(", ") || "无"}，请注意内容把关`;
        } else if (safety.risk_level === "high") {
            className = "safety-danger";
            icon = "🚫";
            text = `内容风险较高，包含：${safety.matched_words.join(", ") || "未知敏感词"}，请修改后重试`;
        }
        
        container.className = `safety-result ${className}`;
        container.innerHTML = `<strong>${icon} ${text}</strong>`;
        container.style.display = "block";
    },

    async generateBook() {
        if (!this.currentStory) {
            this.showMessage("请先完成故事解析", "error");
            return;
        }

        this.currentStory.style = this.selectedStyle;
        this.showProgressModal();
        this.updateProgress(10, "正在准备故事数据...");

        try {
            this.updateProgress(30, "正在调用 AI 绘制插画...");

            const response = await fetch("/api/book/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    story: this.currentStory,
                    style: this.selectedStyle
                })
            });

            this.updateProgress(80, "正在排版生成绘本...");

            const result = await response.json();

            if (result.success) {
                this.updateProgress(100, "绘本生成完成！");
                setTimeout(() => {
                    this.hideProgressModal();
                    this.showResultModal(result.data);
                }, 500);
            } else {
                this.hideProgressModal();
                this.showMessage("❌ " + result.message, "error");
            }
        } catch (error) {
            this.hideProgressModal();
            this.showMessage("❌ 生成失败：" + error.message, "error");
        }
    },

    showProgressModal() {
        document.getElementById("progressModal").style.display = "flex";
        this.updateProgress(0, "准备开始...");
    },

    hideProgressModal() {
        document.getElementById("progressModal").style.display = "none";
    },

    updateProgress(percent, text) {
        document.getElementById("progressFill").style.width = percent + "%";
        if (text) {
            document.getElementById("progressText").textContent = text;
        }
    },

    showResultModal(bookData) {
        const modal = document.getElementById("resultModal");
        const readLink = document.getElementById("readBookLink");
        const downloadLink = document.getElementById("downloadBookLink");
        const resultText = document.getElementById("resultText");
        
        readLink.href = `/reader/${bookData.id}`;
        downloadLink.href = `/api/books/${bookData.id}/download`;
        resultText.textContent = `《${bookData.title}》共 ${bookData.page_count} 页，准备就绪！`;
        
        modal.style.display = "flex";
    },

    closeResultModal() {
        document.getElementById("resultModal").style.display = "none";
    },

    goToLibrary() {
        // 跳转编辑器页面，因为编辑器页面同时展示绘本馆
        window.location.href = "/editor";
    },

    showMessage(message, type = "info") {
        // 简单的消息提示实现
        let messageBox = document.getElementById("messageBox");
        if (!messageBox) {
            messageBox = document.createElement("div");
            messageBox.id = "messageBox";
            messageBox.style.cssText = `
                position: fixed;
                top: 80px;
                left: 50%;
                transform: translateX(-50%);
                padding: 12px 24px;
                border-radius: 30px;
                font-weight: 600;
                z-index: 3000;
                transition: all 0.3s ease;
                max-width: 80%;
                text-align: center;
            `;
            document.body.appendChild(messageBox);
        }
        
        const colors = {
            info: "#54A0FF",
            success: "#1DD1A1",
            error: "#FF6B6B",
            warning: "#FFC312"
        };
        
        messageBox.style.background = colors[type] || colors.info;
        messageBox.style.color = "white";
        messageBox.style.boxShadow = "0 4px 15px rgba(0,0,0,0.2)";
        messageBox.textContent = message;
        messageBox.style.opacity = "1";
        messageBox.style.top = "80px";
        
        setTimeout(() => {
            messageBox.style.opacity = "0";
            messageBox.style.top = "60px";
        }, 3000);
    },

    escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
};

// 初始化
document.addEventListener("DOMContentLoaded", () => {
    app.init();
});
