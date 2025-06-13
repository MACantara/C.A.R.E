/**
 * UI Manager
 * Handles UI state and interactions
 */
export class UIManager {
    constructor(messageSystem) {
        this.messageSystem = messageSystem;
    }

    /**
     * Setup message input event listeners
     */
    setupMessageInput() {
        const input = document.getElementById("messageInput");
        const sendButton = document.getElementById("sendButton");

        if (!input || !sendButton) return;

        input.addEventListener("input", (e) => {
            sendButton.disabled =
                !e.target.value.trim() || !this.messageSystem.currentChatUserId;
            this.autoResizeTextarea(e.target);

            // Handle typing indicators
            if (this.messageSystem.currentChatUserId && e.target.value.trim()) {
                this.messageSystem.startTyping();
            } else {
                this.messageSystem.stopTyping();
            }
        });

        input.addEventListener("keypress", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (!sendButton.disabled) {
                    this.messageSystem.sendMessage();
                }
            }
        });

        // Initially disable input
        input.disabled = true;
        input.placeholder = "Select a conversation to start messaging...";
        sendButton.disabled = true;
    }

    /**
     * Auto-resize textarea
     */
    autoResizeTextarea(textarea) {
        textarea.style.height = "auto";
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + "px";
    }

    /**
     * Update chat selection in sidebar
     */
    updateChatSelection(userId) {
        document.querySelectorAll("#chatItems > div").forEach((item) => {
            item.classList.remove("bg-blue-50", "dark:bg-blue-900/20");
        });

        // Find and highlight the selected chat
        const chatItems = document.querySelectorAll("#chatItems > div");
        chatItems.forEach((item) => {
            if (item.querySelector("div").textContent.includes(userId)) {
                item.classList.add("bg-blue-50", "dark:bg-blue-900/20");
            }
        });
    }

    /**
     * Show chat view
     */
    showChatView() {
        const welcome = document.getElementById("chatWelcome");
        const chatView = document.getElementById("chatView");

        welcome?.classList.add("hidden");
        chatView?.classList.remove("hidden");
    }

    /**
     * Enable message input
     */
    enableMessageInput() {
        const input = document.getElementById("messageInput");
        const sendButton = document.getElementById("sendButton");

        if (input && sendButton) {
            input.disabled = false;
            input.placeholder = "Type a message...";
            sendButton.disabled = !input.value.trim();
        }
    }

    /**
     * Disable message input while sending
     */
    disableMessageInput() {
        const input = document.getElementById("messageInput");
        const sendButton = document.getElementById("sendButton");

        if (input && sendButton) {
            input.disabled = true;
            sendButton.disabled = true;
        }
    }

    /**
     * Hide loading state
     */
    hideLoadingState() {
        const loading = document.getElementById("chatListLoading");
        loading?.classList.add("hidden");
    }

    /**
     * Show empty state
     */
    showEmptyState() {
        const empty = document.getElementById("chatListEmpty");
        empty?.classList.remove("hidden");
    }

    /**
     * Show chat items
     */
    showChatItems() {
        const items = document.getElementById("chatItems");
        items?.classList.remove("hidden");
    }

    /**
     * Show new message toast notification
     */
    showNewMessageToast(data) {
        const toast = document.createElement("div");
        toast.className =
            "fixed bottom-20 right-6 bg-blue-600 text-white px-4 py-3 rounded-lg shadow-lg z-40 animate-slide-in-right cursor-pointer";
        toast.innerHTML = `
            <div class="flex items-center">
                <i class="bi bi-chat-dots mr-2"></i>
                <div>
                    <p class="font-medium">New message</p>
                    <p class="text-sm opacity-90">${data.notification.title}</p>
                </div>
            </div>
        `;

        document.body.appendChild(toast);

        // Auto remove after 5 seconds
        setTimeout(() => {
            toast.remove();
        }, 5000);

        // Click to open conversation
        toast.addEventListener("click", () => {
            this.messageSystem.openChat(data.message.sender_id);
            toast.remove();
        });
    }
}
