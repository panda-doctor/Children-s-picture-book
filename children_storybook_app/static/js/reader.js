/**
 * 在线绘本阅读器交互逻辑
 */

const readerApp = {
    bookData: null,
    currentPage: 0,
    totalPages: 0,
    utterance: null,

    init() {
        if (typeof BOOK_ID === "undefined" || !BOOK_ID) {
            this.showError("绘本 ID 无效");
            return;
        }
        // 离开页面时停止朗读，避免后台继续发声
        window.addEventListener("beforeunload", () => this.stopSpeak());
        this.loadBook(BOOK_ID);
    },

    async loadBook(bookId) {
        try {
            const response = await fetch(`/api/books/${bookId}`);
            const result = await response.json();

            if (result.success) {
                this.bookData = result.data;
                this.totalPages = this.bookData.pages.length;
                this.currentPage = 0;
                this.renderBook();
            } else {
                this.showError(result.message || "绘本加载失败");
            }
        } catch (error) {
            this.showError("网络错误：" + error.message);
        }
    },

    renderBook() {
        const container = document.getElementById("bookContainer");
        const controls = document.getElementById("pageControls");
        const title = document.getElementById("readerTitle");

        title.textContent = this.bookData.title || "未命名绘本";

        container.innerHTML = this.bookData.pages.map((page, index) => {
            const imageUrl = page.image_url || this.fixImagePath(page.image);
            const pageNum = index + 1;
            return `
                <div class="book-page ${index === 0 ? 'active' : 'next'}" data-page="${index}">
                    <img src="${imageUrl}" alt="${page.title || '第' + pageNum + '页'}" 
                         onerror="readerApp.handleImageError(this)">
                    <span class="page-corner">${pageNum}</span>
                </div>
            `;
        }).join("");

        controls.style.display = "flex";
        this.updateControls();
        this.initSpeak();
        this.bindKeyboard();
        this.bindSwipe();
    },

    fixImagePath(path) {
        if (!path) return "";
        // 将 Windows 路径转为 URL 路径，并保留 data 目录
        let urlPath = path.replace(/\\/g, "/");
        // 如果路径以 children_storybook_app/ 开头，去掉它
        urlPath = urlPath.replace(/^.*children_storybook_app\//, "");
        return "/" + urlPath;
    },

    handleImageError(img) {
        img.onerror = null;
        img.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300'%3E%3Crect width='400' height='300' fill='%23e0e0e0'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-size='20' fill='%23999'%3E插画加载失败%3C/text%3E%3C/svg%3E";
    },

    updateControls() {
        const prevBtn = document.getElementById("prevBtn");
        const nextBtn = document.getElementById("nextBtn");
        const indicator = document.getElementById("pageIndicator");

        prevBtn.disabled = this.currentPage === 0;
        nextBtn.disabled = this.currentPage === this.totalPages - 1;
        indicator.textContent = `${this.currentPage + 1} / ${this.totalPages}`;

        // 更新页面类名实现翻页动画
        document.querySelectorAll(".book-page").forEach((page, index) => {
            page.classList.remove("active", "prev", "next");
            if (index === this.currentPage) {
                page.classList.add("active");
            } else if (index < this.currentPage) {
                page.classList.add("prev");
            } else {
                page.classList.add("next");
            }
        });
    },

    nextPage() {
        if (this.currentPage < this.totalPages - 1) {
            this.stopSpeak();
            this.currentPage++;
            this.updateControls();
        }
    },

    prevPage() {
        if (this.currentPage > 0) {
            this.stopSpeak();
            this.currentPage--;
            this.updateControls();
        }
    },

    /* ===== 语音朗读 ===== */

    speechSupported() {
        return typeof window !== "undefined" && "speechSynthesis" in window;
    },

    initSpeak() {
        const btn = document.getElementById("speakBtn");
        if (!btn) return;
        if (!this.speechSupported()) {
            // 浏览器不支持时隐藏按钮
            btn.classList.add("unsupported");
        }
    },

    // 根据页面类型取出可朗读的文本
    getPageText(page) {
        if (!page) return "";
        if (page.type === "content") {
            return page.content || page.chapter || "";
        }
        if (page.type === "cover") {
            const author = page.author ? `，作者，${page.author}` : "";
            return `${page.title || ""}${author}`;
        }
        if (page.type === "back") {
            return `${page.title || ""}，故事结束`;
        }
        return page.content || page.title || "";
    },

    toggleSpeak() {
        if (!this.speechSupported()) {
            this.showToast("当前浏览器不支持语音朗读");
            return;
        }
        const synth = window.speechSynthesis;
        if (synth.speaking) {
            this.stopSpeak();
        } else {
            this.speakCurrentPage();
        }
    },

    speakCurrentPage() {
        if (!this.speechSupported() || !this.bookData) return;
        const text = this.getPageText(this.bookData.pages[this.currentPage]);
        if (!text.trim()) {
            this.showToast("本页没有可朗读的文字");
            return;
        }

        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = "zh-CN";
        utterance.rate = 0.9;   // 略放慢，适合儿童跟读
        utterance.pitch = 1.05;
        utterance.onend = () => this.setSpeakingState(false);
        utterance.onerror = () => this.setSpeakingState(false);

        this.utterance = utterance;
        window.speechSynthesis.speak(utterance);
        this.setSpeakingState(true);
    },

    stopSpeak() {
        if (!this.speechSupported()) return;
        window.speechSynthesis.cancel();
        this.setSpeakingState(false);
    },

    setSpeakingState(speaking) {
        const btn = document.getElementById("speakBtn");
        if (!btn) return;
        btn.classList.toggle("speaking", speaking);
        btn.textContent = speaking ? "⏹" : "🔊";
        btn.title = speaking ? "停止朗读" : "朗读本页";
    },

    showToast(message) {
        // 复用错误提示样式的轻量浮层
        let toast = document.getElementById("readerToast");
        if (!toast) {
            toast = document.createElement("div");
            toast.id = "readerToast";
            toast.style.cssText = "position:fixed;bottom:100px;left:50%;transform:translateX(-50%);" +
                "background:rgba(0,0,0,0.75);color:#fff;padding:10px 22px;border-radius:24px;" +
                "font-size:15px;z-index:3000;transition:opacity .3s ease;";
            document.body.appendChild(toast);
        }
        toast.textContent = message;
        toast.style.opacity = "1";
        clearTimeout(this._toastTimer);
        this._toastTimer = setTimeout(() => { toast.style.opacity = "0"; }, 2500);
    },

    bindKeyboard() {
        document.addEventListener("keydown", (e) => {
            if (e.key === "ArrowRight" || e.key === " ") {
                e.preventDefault();
                this.nextPage();
            } else if (e.key === "ArrowLeft") {
                e.preventDefault();
                this.prevPage();
            }
        });
    },

    bindSwipe() {
        let startX = 0;
        const container = document.querySelector(".reader-page");

        container.addEventListener("touchstart", (e) => {
            startX = e.touches[0].clientX;
        }, { passive: true });

        container.addEventListener("touchend", (e) => {
            const endX = e.changedTouches[0].clientX;
            const diff = startX - endX;

            if (Math.abs(diff) > 50) {
                if (diff > 0) {
                    this.nextPage();
                } else {
                    this.prevPage();
                }
            }
        }, { passive: true });
    },

    showError(message) {
        const container = document.getElementById("bookContainer");
        container.innerHTML = `
            <div class="reader-error">
                <h2>😢 出错了</h2>
                <p>${this.escapeHtml(message)}</p>
                <a href="/" class="btn btn-primary" style="margin-top: 20px;">返回首页</a>
            </div>
        `;
    },

    escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
};

document.addEventListener("DOMContentLoaded", () => {
    readerApp.init();
});
