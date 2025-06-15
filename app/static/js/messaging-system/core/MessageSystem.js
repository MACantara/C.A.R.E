import { SocketManager } from "./SocketManager.js";
import { ConversationManager } from "./ConversationManager.js";
import { MessageRenderer } from "../ui/MessageRenderer.js";
import { UIManager } from "../ui/UIManager.js";
import { ComposeModal } from "../ui/ComposeModal.js";
import { SearchManager } from "../utils/SearchManager.js";
import { TimeFormatter } from "../utils/TimeFormatter.js";
import { MessageStatusManager } from "../utils/MessageStatusManager.js";

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
        this.messageStatusManager = new MessageStatusManager(this);

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
        // Clear typing indicator for previous conversation
        if (this.currentChatUserId !== userId) {
            this.uiManager.clearTypingForConversationSwitch();
        }

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

        // Clear typing indicator and disable input
        this.uiManager.disableMessageInput();

        // Generate temporary message ID for tracking
        const tempMessageId = "temp_" + Date.now();

        const messageData = {
            recipient_id: this.currentChatUserId,
            content: content,
            subject: "Chat Message",
            priority: "normal",
            message_type: "general",
            temp_id: tempMessageId,
        };

        // Add message immediately with "sending" status
        const tempMessage = {
            id: tempMessageId,
            sender_id: this.currentUserId,
            content: content,
            created_at: new Date().toISOString(),
            sender_name: "You",
            status: "sending",
        };

        this.messageRenderer.addMessageToUI(tempMessage);
        input.value = "";
        this.uiManager.autoResizeTextarea(input);

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
                // Update message status to sent
                this.messageStatusManager.updateMessageStatus(
                    tempMessageId,
                    "sent",
                    data.message.id
                );
                this.conversationManager.loadConversations();
            } else {
                // Update message status to failed
                this.messageStatusManager.updateMessageStatus(
                    tempMessageId,
                    "failed"
                );
                console.error("Failed to send message:", data.error);
            }
        } catch (error) {
            this.messageStatusManager.updateMessageStatus(
                tempMessageId,
                "failed"
            );
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
                status: "delivered",
            });
            this.conversationManager.markConversationAsRead(
                this.currentChatUserId
            );
        } else {
            // Play notification sound for messages not from current chat
            this.playNotificationSound();
        }

        // Update unread count badges in sidebar and navbar
        this.updateUnreadCountBadges();

        // Show notification for new message if not currently viewing that conversation
        if (this.currentChatUserId !== data.message.sender_id) {
            this.uiManager.showNewMessageToast(data);
        }
    }

    /**
     * Play notification sound for new messages
     */
    playNotificationSound() {
        try {
            // Use the MP3 notification sound file
            const audio = new Audio('/static/audio/chat-message-notification.mp3');
            audio.volume = 0.4;
            audio.preload = 'auto';
            
            const playPromise = audio.play();
            if (playPromise !== undefined) {
                playPromise.catch(() => {
                    // Silently fail if audio can't play
                    console.log('Audio notification failed to play');
                });
            }
        } catch (error) {
            // Silently fail if audio is not supported
            console.log('Audio notification not supported');
        }
    }

    /**
     * Update unread count badges across the interface
     */
    updateUnreadCountBadges() {
        // Request updated count from server via Socket.IO
        if (this.socketManager.socket) {
            this.socketManager.socket.emit('request_unread_count');
        } else {
            // Fallback to REST API if Socket.IO not available
            this.fetchUnreadCountFallback();
        }
    }

    /**
     * Fallback method to get unread count via REST API
     */
    async fetchUnreadCountFallback() {
        try {
            const response = await fetch('/messages/api/unread_count');
            const data = await response.json();
            this.displayUnreadCount(data.count || 0);
        } catch (error) {
            console.error('Error fetching unread count:', error);
        }
    }

    /**
     * Display unread count in all badge locations
     */
    displayUnreadCount(count) {
        const badges = [
            'message-badge',           // navbar
            'unread-messages-count',   // sidebar full
            'collapsed-unread-count',  // sidebar collapsed
            'mobile-message-badge'     // mobile navbar
        ];
        
        badges.forEach(badgeId => {
            const badge = document.getElementById(badgeId);
            if (badge) {
                if (count > 0) {
                    // Different count limits for different badge sizes
                    let displayCount;
                    if (badgeId === 'collapsed-unread-count') {
                        displayCount = count > 9 ? '9+' : count;
                    } else {
                        displayCount = count > 99 ? '99+' : count;
                    }
                    
                    badge.textContent = displayCount;
                    badge.classList.remove('hidden');
                } else {
                    badge.classList.add('hidden');
                }
            }
        });
    }

    /**
     * Handle typing indicators
     */
    handleTypingIndicator(data) {
        if (this.currentChatUserId === data.user_id) {
            this.uiManager.showTypingIndicator(data.user_name, data.typing);
        }
    }

    /**
     * Handle message delivery confirmation
     */
    handleMessageDelivered(data) {
        this.messageStatusManager.updateMessageStatus(
            data.message_id,
            "delivered"
        );
    }

    /**
     * Handle message read confirmation
     */
    handleMessageRead(data) {
        this.messageStatusManager.updateMessageStatus(data.message_id, "read");
        // Update unread count when messages are marked as read
        this.updateUnreadCountBadges();
    }

    /**
     * Show chat options (placeholder)
     */
    showChatOptions() {
        console.log("Chat options clicked");
    }
}
