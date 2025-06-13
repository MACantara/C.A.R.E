import { SocketManager } from "./SocketManager.js";
import { ConversationManager } from "./ConversationManager.js";
import { MessageRenderer } from "../ui/MessageRenderer.js";
import { UIManager } from "../ui/UIManager.js";
import { ComposeModal } from "../ui/ComposeModal.js";
import { SearchManager } from "../utils/SearchManager.js";
import { TimeFormatter } from "../utils/TimeFormatter.js";

/**
 * Main Message System Class
 * Orchestrates all messaging functionality
 */
export class MessageSystem {
    constructor() {
        this.currentUserId = null;
        this.currentChatUserId = null;

        // Initialize managers
        this.socketManager = new SocketManager(this);
        this.conversationManager = new ConversationManager(this);
        this.messageRenderer = new MessageRenderer(this);
        this.uiManager = new UIManager(this);
        this.composeModal = new ComposeModal(this);
        this.searchManager = new SearchManager(this);
        this.timeFormatter = new TimeFormatter();

        this.init();
    }

    /**
     * Initialize the message system
     */
    init() {
        this.getCurrentUserId();
        this.socketManager.initialize();
        this.conversationManager.loadConversations();
        this.conversationManager.loadUsers();
        this.uiManager.setupMessageInput();
        this.searchManager.setupSearch();
        this.setupEventListeners();
    }

    /**
     * Get current user ID from page data
     */
    getCurrentUserId() {
        const userIdElement = document.querySelector("[data-current-user-id]");
        if (userIdElement) {
            this.currentUserId = parseInt(userIdElement.dataset.currentUserId);
        }
    }

    /**
     * Setup global event listeners
     */
    setupEventListeners() {
        // Make functions globally available for HTML onclick handlers
        window.openComposeModal = () => this.composeModal.open();
        window.closeComposeModal = () => this.composeModal.close();
        window.sendNewMessage = () => this.composeModal.sendNewMessage();
        window.sendMessage = () => this.sendMessage();
    }

    /**
     * Open a chat conversation
     */
    openChat(userId) {
        this.currentChatUserId = userId;
        this.uiManager.updateChatSelection(userId);
        this.conversationManager.loadChatMessages(userId);
        this.uiManager.showChatView();
        this.uiManager.enableMessageInput();
    }

    /**
     * Send a message
     */
    async sendMessage() {
        const input = document.getElementById("messageInput");
        const content = input.value.trim();

        if (!content || !this.currentChatUserId) return;

        this.uiManager.disableMessageInput();

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
                this.uiManager.autoResizeTextarea(input);

                // Add message immediately for better UX
                this.messageRenderer.addMessageToUI({
                    sender_id: this.currentUserId,
                    content: content,
                    created_at: new Date().toISOString(),
                    sender_name: "You",
                });

                // Refresh conversation list
                this.conversationManager.loadConversations();
            } else {
                console.error("Failed to send message:", data.error);
            }
        } catch (error) {
            console.error("Error sending message:", error);
        } finally {
            this.uiManager.enableMessageInput();
            input.focus();
        }
    }

    /**
     * Handle new incoming messages
     */
    handleNewMessage(data) {
        this.conversationManager.loadConversations();

        if (this.currentChatUserId === data.message.sender_id) {
            this.messageRenderer.addMessageToUI({
                ...data.message,
                sender_name: data.notification.title.replace(
                    "New message from ",
                    ""
                ),
            });
            this.conversationManager.markConversationAsRead(
                this.currentChatUserId
            );
        }

        // Update chat bubble
        if (typeof updateChatBubble === "function") {
            updateChatBubble();
        }

        // Show notification for new message if not currently viewing that conversation
        if (this.currentChatUserId !== data.message.sender_id) {
            this.uiManager.showNewMessageToast(data);
        }
    }

    /**
     * Handle typing indicators
     */
    handleTypingIndicator(data) {
        console.log(
            `${data.user_name} is ${data.typing ? "typing" : "not typing"}`
        );
    }

    /**
     * Start typing indicator
     */
    startTyping() {
        if (this.currentChatUserId) {
            this.socketManager.startTyping(this.currentChatUserId);
        }
    }

    /**
     * Stop typing indicator
     */
    stopTyping() {
        if (this.currentChatUserId) {
            this.socketManager.stopTyping(this.currentChatUserId);
        }
    }

    /**
     * Show chat options (placeholder)
     */
    showChatOptions() {
        console.log("Chat options clicked");
    }
}
