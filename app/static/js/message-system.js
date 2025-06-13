/**
 * Message System Module
 * Handles chat interface functionality including real-time messaging,
 * conversation management, and WebSocket connections.
 */
class MessageSystem {
    constructor() {
        this.socket = null;
        this.currentChatUserId = null;
        this.conversations = [];
        this.allUsers = [];
        this.currentUserId = null;
        this.typingTimeout = null;
        this.isTyping = false;

        this.init();
    }

    /**
     * Initialize the message system
     */
    init() {
        // Get current user ID from the page
        const userIdElement = document.querySelector("[data-current-user-id]");
        if (userIdElement) {
            this.currentUserId = parseInt(userIdElement.dataset.currentUserId);
        }

        this.initializeSocket();
        this.loadConversations();
        this.loadUsers();
        this.setupMessageInput();
        this.setupSearch();
        this.setupEventListeners();
    }

    /**
     * Initialize Socket.IO connection
     */
    initializeSocket() {
        this.socket = io();

        this.socket.on("connect", () => {
            console.log("Connected to messaging system");
            this.socket.emit("join_user_room");
        });

        this.socket.on("new_message", (data) => {
            this.handleNewMessage(data);
        });

        this.socket.on("user_typing", (data) => {
            this.handleTypingIndicator(data);
        });

        this.socket.on("disconnect", () => {
            console.log("Disconnected from messaging system");
        });
    }

    /**
     * Load conversations from API
     */
    async loadConversations() {
        try {
            const response = await fetch("/messages/api/conversations");
            const data = await response.json();

            this.conversations = data.conversations;
            this.renderChatList();
            this.hideLoadingState();

            if (this.conversations.length === 0) {
                this.showEmptyState();
            } else {
                this.showChatItems();
            }
        } catch (error) {
            console.error("Error loading conversations:", error);
            this.hideLoadingState();
            this.showEmptyState();
        }
    }

    /**
     * Load users from API
     */
    async loadUsers() {
        try {
            const response = await fetch("/messages/api/users");
            const data = await response.json();

            this.allUsers = data.users;
            this.populateRecipientSelect();
        } catch (error) {
            console.error("Error loading users:", error);
        }
    }

    /**
     * Render chat list in sidebar
     */
    renderChatList() {
        const container = document.getElementById("chatItems");
        if (!container) return;

        container.innerHTML = "";

        this.conversations.forEach((conversation) => {
            const chatItem = this.createChatItem(conversation);
            container.appendChild(chatItem);
        });
    }

    /**
     * Create a chat item element
     */
    createChatItem(conversation) {
        const div = document.createElement("div");
        div.className = `flex items-center p-4 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer border-b border-gray-100 dark:border-gray-700 ${
            this.currentChatUserId === conversation.other_user.id
                ? "bg-blue-50 dark:bg-blue-900/20"
                : ""
        }`;

        div.addEventListener("click", () =>
            this.openChat(conversation.other_user.id)
        );

        const lastMessage = conversation.last_message;
        const timeStr = lastMessage
            ? this.formatTime(lastMessage.created_at)
            : "";

        div.innerHTML = `
            <div class="flex-shrink-0 mr-3">
                <div class="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold">
                    ${conversation.other_user.first_name[0]}${
            conversation.other_user.last_name[0]
        }
                </div>
                ${
                    conversation.unread_count > 0
                        ? '<div class="w-3 h-3 bg-blue-500 rounded-full -mt-2 -ml-2"></div>'
                        : ""
                }
            </div>
            <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between">
                    <h3 class="text-sm font-medium text-gray-900 dark:text-white truncate">
                        ${conversation.other_user.first_name} ${
            conversation.other_user.last_name
        }
                    </h3>
                    <span class="text-xs text-gray-500 dark:text-gray-400">${timeStr}</span>
                </div>
                <div class="flex items-center justify-between">
                    <p class="text-sm text-gray-500 dark:text-gray-400 truncate">
                        ${
                            lastMessage
                                ? lastMessage.content.length > 40
                                    ? lastMessage.content.substring(0, 40) +
                                      "..."
                                    : lastMessage.content
                                : "No messages yet"
                        }
                    </p>
                    ${
                        conversation.unread_count > 0
                            ? `<span class="ml-2 bg-blue-500 text-white text-xs rounded-full px-2 py-1">${conversation.unread_count}</span>`
                            : ""
                    }
                </div>
            </div>
        `;

        return div;
    }

    /**
     * Open a chat conversation
     */
    openChat(userId) {
        this.currentChatUserId = userId;

        // Update chat list selection
        document.querySelectorAll("#chatItems > div").forEach((item) => {
            item.classList.remove("bg-blue-50", "dark:bg-blue-900/20");
        });

        // Highlight current chat
        event.currentTarget?.classList.add("bg-blue-50", "dark:bg-blue-900/20");

        // Load chat messages
        this.loadChatMessages(userId);

        // Show chat view
        this.showChatView();

        // Enable message input
        this.enableMessageInput();
    }

    /**
     * Load messages for a specific conversation
     */
    async loadChatMessages(userId) {
        try {
            const response = await fetch(
                `/messages/api/conversation/${userId}`
            );
            const data = await response.json();

            this.renderChatHeader(data.other_user);
            this.renderMessages(data.messages);
            this.markConversationAsRead(userId);

            // Focus on message input after loading
            setTimeout(() => {
                const input = document.getElementById("messageInput");
                input?.focus();
            }, 100);
        } catch (error) {
            console.error("Error loading chat messages:", error);
        }
    }

    /**
     * Render chat header
     */
    renderChatHeader(user) {
        const header = document.getElementById("chatHeader");
        if (!header) return;

        header.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center">
                    <div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold mr-3">
                        ${user.first_name[0]}${user.last_name[0]}
                    </div>
                    <div>
                        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
                            ${user.first_name} ${user.last_name}
                        </h2>
                        <p class="text-sm text-gray-500 dark:text-gray-400">${
                            user.role.charAt(0).toUpperCase() +
                            user.role.slice(1)
                        }</p>
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    <button onclick="messageSystem.showChatOptions()" class="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                        <i class="bi bi-three-dots-vertical"></i>
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Render messages in the chat area
     */
    renderMessages(messages) {
        const container = document.getElementById("messagesArea");
        if (!container) return;

        container.innerHTML = "";

        messages.forEach((message) => {
            const messageElement = this.createMessageElement(message);
            container.appendChild(messageElement);
        });

        // Scroll to bottom smoothly
        requestAnimationFrame(() => {
            container.scrollTop = container.scrollHeight;
        });
    }

    /**
     * Create a message element
     */
    createMessageElement(message) {
        const isOwn = message.sender_id === this.currentUserId;
        const div = document.createElement("div");
        div.className = `flex ${isOwn ? "justify-end" : "justify-start"} mb-3`;

        const messageTime = this.formatTime(message.created_at);

        div.innerHTML = `
            <div class="max-w-xs lg:max-w-md ${
                isOwn
                    ? "bg-blue-600 text-white"
                    : "bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            } rounded-lg px-4 py-2 shadow-sm">
                ${
                    !isOwn
                        ? `<p class="text-xs font-medium mb-1 opacity-75">${message.sender_name}</p>`
                        : ""
                }
                <p class="text-sm whitespace-pre-wrap break-words">${
                    message.content
                }</p>
                <p class="text-xs mt-1 ${
                    isOwn ? "text-blue-100" : "text-gray-500 dark:text-gray-400"
                } opacity-75">
                    ${messageTime}
                </p>
            </div>
        `;

        return div;
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
                !e.target.value.trim() || !this.currentChatUserId;
            this.autoResize(e.target);

            // Handle typing indicators
            if (this.currentChatUserId && e.target.value.trim()) {
                this.startTyping();
            } else {
                this.stopTyping();
            }
        });

        input.addEventListener("keypress", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (!sendButton.disabled) {
                    this.sendMessage();
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
    autoResize(textarea) {
        textarea.style.height = "auto";
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + "px";
    }

    /**
     * Send a message
     */
    async sendMessage() {
        const input = document.getElementById("messageInput");
        const sendButton = document.getElementById("sendButton");
        const content = input.value.trim();

        if (!content || !this.currentChatUserId) return;

        // Disable input while sending
        input.disabled = true;
        sendButton.disabled = true;

        const messageData = {
            recipient_id: this.currentChatUserId,
            content: content,
            subject: "Chat Message",
            priority: "normal",
            message_type: "general",
        };

        try {
            const response = await fetch("/messages/api/send", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(messageData),
            });

            const data = await response.json();

            if (data.success) {
                input.value = "";
                this.autoResize(input);

                // Add message immediately for better UX
                this.addMessageToUI({
                    sender_id: this.currentUserId,
                    content: content,
                    created_at: new Date().toISOString(),
                    sender_name: "You",
                });

                // Refresh conversation list
                this.loadConversations();
            } else {
                console.error("Failed to send message:", data.error);
            }
        } catch (error) {
            console.error("Error sending message:", error);
        } finally {
            // Re-enable input
            input.disabled = false;
            input.focus();
            sendButton.disabled = !input.value.trim();
        }
    }

    /**
     * Add message to UI immediately
     */
    addMessageToUI(message) {
        const container = document.getElementById("messagesArea");
        if (!container) return;

        const messageElement = this.createMessageElement(message);
        container.appendChild(messageElement);

        // Scroll to bottom smoothly
        requestAnimationFrame(() => {
            container.scrollTop = container.scrollHeight;
        });
    }

    /**
     * Setup search functionality
     */
    setupSearch() {
        const searchInput = document.getElementById("chatSearch");
        if (!searchInput) return;

        searchInput.addEventListener("input", (e) => {
            const searchTerm = e.target.value.toLowerCase();
            const chatItems = document.querySelectorAll("#chatItems > div");

            chatItems.forEach((item) => {
                const text = item.textContent.toLowerCase();
                item.style.display = text.includes(searchTerm)
                    ? "flex"
                    : "none";
            });
        });
    }

    /**
     * Setup global event listeners
     */
    setupEventListeners() {
        // Compose modal functions
        window.openComposeModal = () => this.openComposeModal();
        window.closeComposeModal = () => this.closeComposeModal();
        window.sendNewMessage = () => this.sendNewMessage();
        window.sendMessage = () => this.sendMessage();
    }

    /**
     * Handle new incoming messages
     */
    handleNewMessage(data) {
        // Refresh conversation list
        this.loadConversations();

        // If chat is open with sender, add message to UI immediately
        if (this.currentChatUserId === data.message.sender_id) {
            this.addMessageToUI({
                ...data.message,
                sender_name: data.notification.title.replace(
                    "New message from ",
                    ""
                ),
            });
            this.markConversationAsRead(this.currentChatUserId);
        }

        // Update chat bubble
        if (typeof updateChatBubble === "function") {
            updateChatBubble();
        }

        // Show notification for new message if not currently viewing that conversation
        if (this.currentChatUserId !== data.message.sender_id) {
            this.showNewMessageToast(data);
        }
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
            this.openChat(data.message.sender_id);
            toast.remove();
        });
    }

    /**
     * Modal functions
     */
    openComposeModal() {
        const modal = document.getElementById("composeModal");
        modal?.classList.remove("hidden");
    }

    closeComposeModal() {
        const modal = document.getElementById("composeModal");
        const form = document.getElementById("composeForm");

        modal?.classList.add("hidden");
        form?.reset();
    }

    /**
     * Populate recipient select in compose modal
     */
    populateRecipientSelect() {
        const select = document.getElementById("composeRecipient");
        if (!select) return;

        select.innerHTML = '<option value="">Select recipient...</option>';

        this.allUsers.forEach((user) => {
            const option = document.createElement("option");
            option.value = user.id;
            option.textContent = `${user.first_name} ${user.last_name} - ${
                user.role.charAt(0).toUpperCase() + user.role.slice(1)
            }`;
            select.appendChild(option);
        });
    }

    /**
     * Send new message from compose modal
     */
    async sendNewMessage() {
        const form = document.getElementById("composeForm");
        if (!form) return;

        const formData = new FormData(form);

        const messageData = {
            recipient_id: formData.get("recipient_id"),
            subject: formData.get("subject"),
            content: formData.get("content"),
            priority: formData.get("priority"),
            message_type: "general",
        };

        try {
            const response = await fetch("/messages/api/send", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(messageData),
            });

            const data = await response.json();

            if (data.success) {
                this.closeComposeModal();
                this.loadConversations();
                // Open the new conversation
                this.openChat(parseInt(messageData.recipient_id));
            }
        } catch (error) {
            console.error("Error sending message:", error);
        }
    }

    /**
     * Utility functions
     */
    showChatView() {
        const welcome = document.getElementById("chatWelcome");
        const chatView = document.getElementById("chatView");

        welcome?.classList.add("hidden");
        chatView?.classList.remove("hidden");
    }

    enableMessageInput() {
        const input = document.getElementById("messageInput");
        const sendButton = document.getElementById("sendButton");

        if (input && sendButton) {
            input.disabled = false;
            input.placeholder = "Type a message...";
            sendButton.disabled = !input.value.trim();
        }
    }

    hideLoadingState() {
        const loading = document.getElementById("chatListLoading");
        loading?.classList.add("hidden");
    }

    showEmptyState() {
        const empty = document.getElementById("chatListEmpty");
        empty?.classList.remove("hidden");
    }

    showChatItems() {
        const items = document.getElementById("chatItems");
        items?.classList.remove("hidden");
    }

    async markConversationAsRead(userId) {
        try {
            await fetch(`/messages/api/mark_conversation_read/${userId}`, {
                method: "POST",
            });
        } catch (error) {
            console.error("Error marking conversation as read:", error);
        }
    }

    startTyping() {
        if (this.currentChatUserId && !this.isTyping) {
            this.isTyping = true;
            this.socket?.emit("typing_start", {
                recipient_id: this.currentChatUserId,
            });
        }
    }

    stopTyping() {
        if (this.currentChatUserId && this.isTyping) {
            this.isTyping = false;
            this.socket?.emit("typing_stop", {
                recipient_id: this.currentChatUserId,
            });
        }
    }

    handleTypingIndicator(data) {
        // Handle typing indicators
        console.log(
            `${data.user_name} is ${data.typing ? "typing" : "not typing"}`
        );
    }

    showChatOptions() {
        console.log("Chat options clicked");
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diffInHours = (now - date) / (1000 * 60 * 60);

        if (diffInHours < 24) {
            return date.toLocaleTimeString("en-US", {
                hour: "numeric",
                minute: "2-digit",
                hour12: true,
            });
        } else if (diffInHours < 168) {
            // 7 days
            return date.toLocaleDateString("en-US", { weekday: "short" });
        } else {
            return date.toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
            });
        }
    }
}

// Initialize message system when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
    window.messageSystem = new MessageSystem();
});

export { MessageSystem };
