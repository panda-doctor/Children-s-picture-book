/**
 * 在线绘本阅读器交互逻辑
 */

const readerApp = {
    bookData: null,
    currentPage: 0,
    totalPages: 0,

    init() {
        if (typeof BOOK_ID === "undefined" || !BOOK_ID) {
            this.showError("绘本 ID 无效");
            return;
        }
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
            this.currentPage++;
            this.updateControls();
        }
    },

    prevPage() {
        if (this.currentPage > 0) {
            this.currentPage--;
            this.updateControls();
        }
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
