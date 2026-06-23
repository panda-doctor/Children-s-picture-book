/**
 * 故事编辑器 & 绘本馆交互逻辑
 */

const editorApp = {
    currentFile: null,

    init() {
        this.bindTabs();
        this.bindUploadArea();
        this.loadBooksList();
        this.refreshParentLock();
        this.bindParentInput();
    },

    bindTabs() {
        const buttons = document.querySelectorAll(".tab-btn");
        buttons.forEach(btn => {
            btn.addEventListener("click", () => {
                const tabName = btn.dataset.tab;
                
                // 切换按钮状态
                buttons.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                
                // 切换内容区
                document.querySelectorAll(".tab-content").forEach(content => {
                    content.classList.remove("active");
                });
                document.getElementById(tabName + "Tab").classList.add("active");
                
                if (tabName === "library") {
                    this.loadBooksList();
                }
            });
        });
    },

    bindUploadArea() {
        const uploadArea = document.getElementById("uploadArea");
        const fileInput = document.getElementById("fileInput");
        
        uploadArea.addEventListener("click", () => fileInput.click());
        
        uploadArea.addEventListener("dragover", (e) => {
            e.preventDefault();
            uploadArea.classList.add("dragover");
        });
        
        uploadArea.addEventListener("dragleave", () => {
            uploadArea.classList.remove("dragover");
        });
        
        uploadArea.addEventListener("drop", (e) => {
            e.preventDefault();
            uploadArea.classList.remove("dragover");
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileSelect(files[0]);
            }
        });
        
        fileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) {
                this.handleFileSelect(e.target.files[0]);
            }
        });
    },

    handleFileSelect(file) {
        const validTypes = [".txt", ".json"];
        const ext = file.name.toLowerCase().substring(file.name.lastIndexOf("."));
        
        if (!validTypes.includes(ext)) {
            this.showMessage("❌ 仅支持 TXT 或 JSON 文件", "error");
            return;
        }
        
        this.currentFile = file;
        document.querySelector(".upload-text").textContent = `已选择：${file.name}`;
        this.showMessage("✅ 文件已选择，点击上传按钮继续", "success");
    },

    async uploadStory() {
        if (!this.currentFile) {
            this.showMessage("请先选择故事文件", "error");
            return;
        }
        
        const formData = new FormData();
        formData.append("file", this.currentFile);
        
        try {
            this.showMessage("📤 正在上传文件...", "info");
            
            const response = await fetch("/api/story/upload", {
                method: "POST",
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showMessage("✅ 上传成功，正在跳转到创作页面...", "success");
                // 将故事数据存入 sessionStorage，跳转首页
                sessionStorage.setItem("pendingStory", JSON.stringify(result.data));
                setTimeout(() => {
                    window.location.href = "/";
                }, 1000);
            } else {
                // 未通过家长验证时，锁定上传区并弹出验证框
                if (result.data && result.data.need_parent) {
                    this.setParentUnlocked(false);
                    this.promptParent();
                }
                this.showMessage("❌ " + result.message, "error");
            }
        } catch (error) {
            this.showMessage("❌ 上传失败：" + error.message, "error");
        }
    },

    /* ===== 家长模式 ===== */

    async refreshParentLock() {
        try {
            const response = await fetch("/api/parent/status");
            const result = await response.json();
            this.setParentUnlocked(!!(result.data && result.data.verified));
        } catch (error) {
            this.setParentUnlocked(false);
        }
    },

    setParentUnlocked(unlocked) {
        const lock = document.getElementById("parentLock");
        const inner = document.getElementById("uploadInner");
        if (!lock || !inner) return;
        lock.style.display = unlocked ? "none" : "flex";
        inner.style.display = unlocked ? "block" : "none";
    },

    promptParent() {
        const modal = document.getElementById("parentModal");
        const input = document.getElementById("parentPassword");
        modal.style.display = "flex";
        input.value = "";
        input.focus();
    },

    closeParentModal() {
        document.getElementById("parentModal").style.display = "none";
    },

    bindParentInput() {
        const input = document.getElementById("parentPassword");
        if (input) {
            input.addEventListener("keydown", (e) => {
                if (e.key === "Enter") this.verifyParent();
            });
        }
    },

    async verifyParent() {
        const password = document.getElementById("parentPassword").value;
        if (!password) {
            this.showMessage("请输入家长密码", "error");
            return;
        }
        try {
            const response = await fetch("/api/parent/verify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ password })
            });
            const result = await response.json();
            if (result.success) {
                this.closeParentModal();
                this.setParentUnlocked(true);
                this.showMessage("✅ 家长验证成功，已解锁编辑功能", "success");
            } else {
                this.showMessage("❌ " + result.message, "error");
            }
        } catch (error) {
            this.showMessage("❌ 验证失败：" + error.message, "error");
        }
    },

    async parentLogout() {
        try {
            await fetch("/api/parent/logout", { method: "POST" });
        } catch (error) {
            // 忽略网络错误，前端仍然回到锁定状态
        }
        this.setParentUnlocked(false);
        this.showMessage("已退出家长模式", "info");
    },

    async loadBooksList() {
        const container = document.getElementById("booksList");
        
        try {
            const response = await fetch("/api/books/list");
            const result = await response.json();
            
            if (result.success && result.data.books && result.data.books.length > 0) {
                this.renderBooksList(result.data.books);
            } else {
                container.innerHTML = `
                    <div class="empty-state" style="grid-column: 1/-1;">
                        <span class="empty-icon">📖</span>
                        <p>还没有绘本，快去创作一本吧！</p>
                    </div>
                `;
            }
        } catch (error) {
            container.innerHTML = `
                <div class="empty-state" style="grid-column: 1/-1;">
                    <span class="empty-icon">😢</span>
                    <p>加载绘本列表失败：${this.escapeHtml(error.message)}</p>
                </div>
            `;
        }
    },

    renderBooksList(books) {
        const container = document.getElementById("booksList");
        
        container.innerHTML = books.map(book => {
            const createdDate = new Date(book.created_at).toLocaleString("zh-CN");
            const coverUrl = book.cover_url || this.fixImagePath(book.cover);
            const coverHtml = coverUrl
                ? `<img src="${coverUrl}" alt="封面" onerror="this.style.display='none'">`
                : `<span class="book-cover-icon">📚</span>`;
            
            return `
                <div class="book-card">
                    <div class="book-cover">
                        ${coverHtml}
                    </div>
                    <div class="book-info">
                        <div class="book-title">${this.escapeHtml(book.title)}</div>
                        <div class="book-meta">作者：${this.escapeHtml(book.author || "佚名")}</div>
                        <div class="book-time">${createdDate}</div>
                        <div class="book-time">${book.page_count} 页</div>
                        <div class="book-actions">
                            <a href="/reader/${book.id}" class="btn btn-primary btn-sm">📖 阅读</a>
                            <a href="/api/books/${book.id}/download" class="btn btn-secondary btn-sm">⬇️ PDF</a>
                        </div>
                    </div>
                </div>
            `;
        }).join("");
    },

    fixImagePath(path) {
        if (!path) return "";
        let urlPath = path.replace(/\\/g, "/");
        urlPath = urlPath.replace(/^.*children_storybook_app\//, "");
        return "/" + urlPath;
    },

    goToLibrary() {
        window.location.href = "/editor";
    },

    showMessage(message, type = "info") {
        let messageBox = document.getElementById("editorMessageBox");
        if (!messageBox) {
            messageBox = document.createElement("div");
            messageBox.id = "editorMessageBox";
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
    editorApp.init();
});
